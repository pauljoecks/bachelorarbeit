"""Generate analyzed scan JSON and weld H5 files from saved measurement data."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import h5py
import numpy as np

from run_scan import (
    AUTO_BASELINE_MIN_PROFILES,
    _compute_baseline_profile,
    _profile_has_measurement,
    _profile_measurement_mask,
    assign_profile_y_mm,
    extract_scan_duration_s,
)
from run_weld import WeldConfig, _save_weld_h5

PROBE_THRESHOLD_MM = 2.0
WELD_CHUNK_FRACTION_S = 0.1
WELD_BASELINE_MIN_CHUNKS = 10


def _select_baseline_profiles(profiles: list[dict]) -> list[dict]:
    baseline_profiles = []
    for profile in profiles:
        if not _profile_has_measurement(profile):
            continue
        baseline_profiles.append(profile)
        if len(baseline_profiles) >= AUTO_BASELINE_MIN_PROFILES:
            break

    if len(baseline_profiles) < AUTO_BASELINE_MIN_PROFILES:
        raise ValueError(
            f"Nicht genug Baseline-Profile für den Tisch "
            f"(mindestens {AUTO_BASELINE_MIN_PROFILES} erforderlich)."
        )

    return baseline_profiles


def _filter_profile_to_probe_only(
    profile: dict,
    baseline: dict,
    *,
    threshold_mm: float = PROBE_THRESHOLD_MM,
) -> dict:
    z_mm = np.asarray(profile["z_mm"], dtype=float)
    baseline_z = np.asarray(baseline["z_mm"], dtype=float)
    intensities = np.asarray(profile["intensities"], dtype=float)
    profile_mask = _profile_measurement_mask(profile)
    baseline_mask = _profile_measurement_mask(baseline)

    new_z = np.zeros_like(z_mm)
    new_intensities = np.zeros_like(intensities, dtype=int)

    valid_mask = profile_mask & baseline_mask
    height_delta = z_mm - baseline_z
    probe_mask = valid_mask & (height_delta >= threshold_mm)

    new_z[probe_mask] = z_mm[probe_mask]
    new_intensities[probe_mask] = intensities[probe_mask].astype(int)

    filtered_profile = dict(profile)
    filtered_profile["z_mm"] = new_z.astype(float).tolist()
    filtered_profile["intensities"] = new_intensities.astype(int).tolist()
    return filtered_profile


def generate_analyzing_document(
    scan_document: dict,
    *,
    experiment_id: str,
    source_json_file: str,
    threshold_mm: float = PROBE_THRESHOLD_MM,
    scan_speed_mm_s: float | None = None,
    scan_duration_s: float | None = None,
) -> dict:
    profiles = scan_document.get("profiles") or []
    if not profiles:
        raise ValueError("Keine Profile in Scan-Datei gefunden.")

    scan_settings = scan_document.get("scan_settings") or {}
    if scan_duration_s is None:
        scan_duration_s = extract_scan_duration_s(scan_settings)
    if scan_speed_mm_s is None:
        stored_speed = scan_settings.get("scan_speed_mm_s")
        if stored_speed is None or str(stored_speed).strip() == "":
            raise ValueError(f"{source_json_file}: SCANSPEED fehlt.")
        scan_speed_mm_s = float(stored_speed)

    baseline_profiles = _select_baseline_profiles(profiles)
    baseline = _compute_baseline_profile(baseline_profiles)
    if baseline is None:
        raise ValueError("Baseline für den Tisch konnte nicht berechnet werden.")

    filtered_profiles = [
        {
            **filtered,
            "profile_index": index,
        }
        for index, filtered in enumerate(
            _filter_profile_to_probe_only(profile, baseline, threshold_mm=threshold_mm)
            for profile in profiles
        )
    ]
    assign_profile_y_mm(
        filtered_profiles,
        scan_speed_mm_s=float(scan_speed_mm_s),
        scan_duration_s=float(scan_duration_s),
    )

    return {
        "experiment_id": experiment_id,
        "source_json_file": source_json_file,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "resolution": int(scan_document.get("resolution") or len(profiles[0].get("x_mm", []))),
        "profile_count": len(filtered_profiles),
        "baseline_profile_count": len(baseline_profiles),
        "probe_threshold_mm": threshold_mm,
        "scan_speed_mm_s": float(scan_speed_mm_s),
        "scan_duration_s": float(scan_duration_s),
        "profiles": filtered_profiles,
    }


def _load_weld_h5_channels(h5_path: Path) -> tuple[np.ndarray, list[tuple[str, np.ndarray, str, str]]]:
    with h5py.File(h5_path, "r") as h5_file:
        if "time_s" not in h5_file:
            raise ValueError('Datensatz "time_s" nicht gefunden.')

        time_s = np.array(h5_file["time_s"], dtype=float)
        channels: list[tuple[str, np.ndarray, str, str]] = []
        for key in sorted(name for name in h5_file.keys() if name.startswith("channel_")):
            dataset = h5_file[key]
            channels.append(
                (
                    key,
                    np.array(dataset, dtype=float),
                    str(dataset.attrs.get("label", key)),
                    str(dataset.attrs.get("units", "")),
                )
            )

    if not channels:
        raise ValueError("Keine Messkanäle in H5-Datei gefunden.")

    return time_s, channels


def _find_current_channel(
    channels: list[tuple[str, np.ndarray, str, str]],
) -> tuple[str, np.ndarray, str, str]:
    for channel in channels:
        key, _values, label, units = channel
        if label.strip().lower() == "strom" or key == "channel_0":
            return channel

    raise ValueError("Stromkanal in H5-Datei nicht gefunden.")


def _estimate_sample_rate(time_s: np.ndarray, config: WeldConfig) -> float:
    if time_s.size > 1:
        dt = float(np.median(np.diff(time_s)))
        if dt > 0:
            return 1.0 / dt

    if config.rate > 0:
        return float(config.rate)

    return float(config.demo_rate_hz)


def _compute_weld_chunk_means(
    current_a: np.ndarray,
    time_s: np.ndarray,
    *,
    config: WeldConfig,
) -> tuple[int, list[float]]:
    if current_a.size == 0:
        raise ValueError("Keine Stromdaten in H5-Datei.")

    rate = _estimate_sample_rate(time_s, config)
    chunk_samples = max(1, int(rate * WELD_CHUNK_FRACTION_S))
    chunk_means = []

    for start in range(0, current_a.size, chunk_samples):
        end = min(start + chunk_samples, current_a.size)
        chunk_means.append(float(np.mean(current_a[start:end])))

    if not chunk_means:
        raise ValueError("Keine Strom-Chunks für die Analyse verfügbar.")

    return chunk_samples, chunk_means


def _find_weld_active_range(
    current_a: np.ndarray,
    time_s: np.ndarray,
    *,
    config: WeldConfig,
) -> tuple[int, int, float, float]:
    chunk_samples, chunk_means = _compute_weld_chunk_means(current_a, time_s, config=config)

    if len(chunk_means) < WELD_BASELINE_MIN_CHUNKS:
        raise ValueError(
            f"Nicht genug Idle-Messwerte für die Baseline "
            f"(mindestens {WELD_BASELINE_MIN_CHUNKS} Chunks erforderlich)."
        )

    idle_baseline_a = float(np.mean(chunk_means[:WELD_BASELINE_MIN_CHUNKS]))
    margin_a = config.threshold_v * config.current_scale
    threshold_a = idle_baseline_a + margin_a

    active_chunk_indices = [
        index for index, chunk_mean in enumerate(chunk_means) if chunk_mean > threshold_a
    ]
    if not active_chunk_indices:
        raise ValueError("Schweißphase konnte nicht erkannt werden.")

    start_chunk = active_chunk_indices[0]
    end_chunk = active_chunk_indices[-1]
    start_index = start_chunk * chunk_samples
    end_index = min((end_chunk + 1) * chunk_samples, current_a.size)

    if end_index <= start_index:
        raise ValueError("Keine Messdaten in der erkannten Schweißphase vorhanden.")

    return start_index, end_index, idle_baseline_a, threshold_a


def generate_analyzing_weld_h5(
    h5_path: Path,
    *,
    experiment_id: str,
    source_h5_file: str,
    config: WeldConfig | None = None,
) -> dict:
    weld_config = config or WeldConfig()
    time_s, channels = _load_weld_h5_channels(h5_path)
    _key, current_a, _label, _units = _find_current_channel(channels)

    start_index, end_index, idle_baseline_a, threshold_a = _find_weld_active_range(
        current_a,
        time_s,
        config=weld_config,
    )
    weld_start_time_s = float(time_s[start_index])
    weld_end_time_s = float(time_s[end_index - 1])
    trimmed_time_s = time_s[start_index:end_index]
    trimmed_channels = [
        (key, values[start_index:end_index], label, units)
        for key, values, label, units in channels
    ]

    if trimmed_time_s.size <= 0:
        raise ValueError("Keine Messdaten in der Schweißphase vorhanden.")

    return {
        "experiment_id": experiment_id,
        "source_h5_file": source_h5_file,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "baseline_chunk_count": WELD_BASELINE_MIN_CHUNKS,
        "idle_baseline_a": round(idle_baseline_a, 6),
        "weld_start_time_s": round(weld_start_time_s, 6),
        "weld_end_time_s": round(weld_end_time_s, 6),
        "threshold_a": round(threshold_a, 6),
        "sample_count": int(trimmed_time_s.size),
        "duration_s": float(trimmed_time_s[-1] - trimmed_time_s[0]) if trimmed_time_s.size else 0.0,
        "time_s": trimmed_time_s,
        "channels": trimmed_channels,
    }


def run_analyze_scan(
    experiment_id: str,
    scan_path: Path,
    output_dir: Path,
    *,
    threshold_mm: float = PROBE_THRESHOLD_MM,
    scan_speed_mm_s: float | None = None,
    scan_duration_s: float | None = None,
) -> dict:
    experiment_id = experiment_id.strip().upper()
    scan_path = Path(scan_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with scan_path.open("r", encoding="utf-8") as handle:
        scan_document = json.load(handle)

    document = generate_analyzing_document(
        scan_document,
        experiment_id=experiment_id,
        source_json_file=scan_path.name,
        threshold_mm=threshold_mm,
        scan_speed_mm_s=scan_speed_mm_s,
        scan_duration_s=scan_duration_s,
    )

    output_path = output_dir / f"{experiment_id}.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2)

    return {
        "json_file": output_path.name,
        "profile_count": document["profile_count"],
        "baseline_profile_count": document["baseline_profile_count"],
        "probe_threshold_mm": document["probe_threshold_mm"],
        "source_json_file": scan_path.name,
    }


def run_analyze_weld(
    experiment_id: str,
    weld_path: Path,
    output_dir: Path,
    *,
    config: WeldConfig | None = None,
) -> dict:
    experiment_id = experiment_id.strip().upper()
    weld_path = Path(weld_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    document = generate_analyzing_weld_h5(
        weld_path,
        experiment_id=experiment_id,
        source_h5_file=weld_path.name,
        config=config,
    )

    output_path = output_dir / f"{experiment_id}.h5"
    _save_weld_h5(output_path, document["time_s"], document["channels"])

    return {
        "h5_file": output_path.name,
        "weld_sample_count": document["sample_count"],
        "weld_duration_s": document["duration_s"],
        "weld_start_time_s": document["weld_start_time_s"],
        "weld_end_time_s": document["weld_end_time_s"],
        "weld_idle_baseline_a": document["idle_baseline_a"],
        "weld_threshold_a": document["threshold_a"],
        "source_h5_file": weld_path.name,
    }


def run_analyze(
    experiment_id: str,
    output_dir: Path,
    *,
    scan_path: Path | None = None,
    weld_path: Path | None = None,
    threshold_mm: float = PROBE_THRESHOLD_MM,
    weld_config: WeldConfig | None = None,
    scan_speed_mm_s: float | None = None,
    scan_duration_s: float | None = None,
) -> dict:
    if scan_path is None and weld_path is None:
        raise ValueError("Weder Scan- noch Weld-Datei vorhanden.")

    result: dict = {
        "success": True,
        "experiment_id": experiment_id.strip().upper(),
    }

    if scan_path is not None:
        result.update(
            run_analyze_scan(
                experiment_id,
                scan_path,
                output_dir,
                threshold_mm=threshold_mm,
                scan_speed_mm_s=scan_speed_mm_s,
                scan_duration_s=scan_duration_s,
            )
        )

    if weld_path is not None:
        result.update(
            run_analyze_weld(
                experiment_id,
                weld_path,
                output_dir,
                config=weld_config,
            )
        )

    return result


# Backward-compatible alias for scan-only callers.
run_analyze_scan_only = run_analyze_scan
