"""Generate analyzed scan JSON and weld H5 files from saved measurement data."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import h5py
import numpy as np

from run_scan import (
    AUTO_BASELINE_MIN_PROFILES,
    _classify_probe_vs_baseline,
    _compute_baseline_profile,
    _profile_has_measurement,
    _profile_measurement_mask,
    assign_profile_y_mm,
    extract_scan_duration_s,
)
from run_weld import WeldConfig, _save_weld_h5

PROBE_THRESHOLD_MM = 2.0
MIRROR_ORIGIN_EDGE_EXCLUSION_MM = 1.0
PROBE_CROP_MARGIN_POINTS = 15
WELD_CHUNK_FRACTION_S = 0.1
WELD_BASELINE_MIN_CHUNKS = 10
CROPPED_SCAN_FILENAME = "cropped_scan.json"
CROPPED_WELD_FILENAME = "cropped_weld.h5"
X_PROFILE_FILENAME = "X_profile.json"
Y_PROFILE_FILENAME = "Y_profile.json"


def build_analyze_folder_name(experiment_id: str, timestamp: datetime | None = None) -> str:
    normalized_id = experiment_id.strip().upper()
    current_time = timestamp or datetime.now()
    return f"{normalized_id}_{current_time.strftime('%Y%m%d_%H%M%S')}"


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


def _compute_probe_point_mask(
    profile: dict,
    baseline: dict,
    *,
    threshold_mm: float = PROBE_THRESHOLD_MM,
) -> np.ndarray:
    z_mm = np.asarray(profile["z_mm"], dtype=float)
    baseline_z = np.asarray(baseline["z_mm"], dtype=float)
    profile_mask = _profile_measurement_mask(profile)
    baseline_mask = _profile_measurement_mask(baseline)

    valid_mask = profile_mask & baseline_mask
    height_delta = z_mm - baseline_z
    return valid_mask & (height_delta >= threshold_mm)


def _shrink_true_run(mask: np.ndarray, margin: int) -> np.ndarray:
    if margin <= 0:
        return mask

    indices = np.flatnonzero(mask)
    if indices.size == 0:
        return mask

    start = int(indices[0]) + margin
    end = int(indices[-1]) - margin
    if start > end:
        return np.zeros_like(mask, dtype=bool)

    shrunk = np.zeros_like(mask, dtype=bool)
    shrunk[start : end + 1] = mask[start : end + 1]
    return shrunk


def _zero_profile_measurements(profile: dict) -> dict:
    filtered_profile = dict(profile)
    point_count = len(profile.get("z_mm") or [])
    filtered_profile["z_mm"] = [0.0] * point_count
    filtered_profile["intensities"] = [0] * point_count
    return filtered_profile


def _apply_probe_mask_to_profile(profile: dict, probe_mask: np.ndarray) -> dict:
    z_mm = np.asarray(profile["z_mm"], dtype=float)
    intensities = np.asarray(profile["intensities"], dtype=float)

    new_z = np.zeros_like(z_mm)
    new_intensities = np.zeros_like(intensities, dtype=int)
    new_z[probe_mask] = z_mm[probe_mask]
    new_intensities[probe_mask] = intensities[probe_mask].astype(int)

    filtered_profile = dict(profile)
    filtered_profile["z_mm"] = new_z.astype(float).tolist()
    filtered_profile["intensities"] = new_intensities.astype(int).tolist()
    return filtered_profile


def _shrink_profile_index_range(
    first_index: int,
    last_index: int,
    margin: int,
) -> tuple[int, int] | None:
    if margin <= 0:
        return first_index, last_index

    start = first_index + margin
    end = last_index - margin
    if start > end:
        return None
    return start, end


def _filter_profiles_to_probe_only(
    profiles: list[dict],
    baseline: dict,
    *,
    threshold_mm: float = PROBE_THRESHOLD_MM,
    crop_margin_points: int = PROBE_CROP_MARGIN_POINTS,
) -> list[dict]:
    probe_masks = [
        _compute_probe_point_mask(profile, baseline, threshold_mm=threshold_mm)
        for profile in profiles
    ]

    profile_indices_with_probe = [
        index for index, probe_mask in enumerate(probe_masks) if np.any(probe_mask)
    ]
    y_keep_range = None
    if profile_indices_with_probe:
        y_keep_range = _shrink_profile_index_range(
            profile_indices_with_probe[0],
            profile_indices_with_probe[-1],
            crop_margin_points,
        )

    filtered_profiles: list[dict] = []
    for index, (profile, probe_mask) in enumerate(zip(profiles, probe_masks)):
        if y_keep_range is None or index < y_keep_range[0] or index > y_keep_range[1]:
            filtered = _zero_profile_measurements(profile)
        else:
            cropped_mask = _shrink_true_run(probe_mask, crop_margin_points)
            filtered = _apply_probe_mask_to_profile(profile, cropped_mask)

        filtered_profiles.append(
            {
                **filtered,
                "profile_index": index,
            }
        )

    return filtered_profiles


def _filter_profile_to_probe_only(
    profile: dict,
    baseline: dict,
    *,
    threshold_mm: float = PROBE_THRESHOLD_MM,
    crop_margin_points: int = PROBE_CROP_MARGIN_POINTS,
) -> dict:
    probe_mask = _compute_probe_point_mask(profile, baseline, threshold_mm=threshold_mm)
    cropped_mask = _shrink_true_run(probe_mask, crop_margin_points)
    return _apply_probe_mask_to_profile(profile, cropped_mask)


def _profile_belongs_to_probe(
    profile: dict,
    baseline: dict,
) -> bool:
    return _classify_probe_vs_baseline(profile, baseline) == "present"


def compute_probe_origin_mm(
    profiles: list[dict],
    baseline: dict,
    *,
    threshold_mm: float = PROBE_THRESHOLD_MM,
    exclude_probe_x_below_mm: float | None = None,
) -> tuple[float, float] | None:
    origin_x = None
    first_probe_profile_y = None

    baseline_z = np.asarray(baseline["z_mm"], dtype=float)
    baseline_mask = _profile_measurement_mask(baseline)

    for profile in profiles:
        y_value = profile.get("y_mm")
        if y_value is None:
            continue

        x_mm = np.asarray(profile["x_mm"], dtype=float)
        z_mm = np.asarray(profile["z_mm"], dtype=float)
        profile_mask = _profile_measurement_mask(profile)
        valid_mask = profile_mask & baseline_mask
        probe_mask = valid_mask & ((z_mm - baseline_z) >= threshold_mm)

        if not np.any(probe_mask):
            continue

        probe_x = x_mm[probe_mask]
        if exclude_probe_x_below_mm is not None:
            candidate_x = probe_x[probe_x > exclude_probe_x_below_mm]
            if candidate_x.size == 0:
                candidate_x = probe_x
        else:
            candidate_x = probe_x

        profile_min_x = float(np.min(candidate_x))
        origin_x = profile_min_x if origin_x is None else min(origin_x, profile_min_x)

        if first_probe_profile_y is None and _profile_belongs_to_probe(profile, baseline):
            first_probe_profile_y = float(y_value)

    if origin_x is None:
        return None

    if first_probe_profile_y is None:
        for profile in profiles:
            y_value = profile.get("y_mm")
            if y_value is None:
                continue

            baseline_z = np.asarray(baseline["z_mm"], dtype=float)
            z_mm = np.asarray(profile["z_mm"], dtype=float)
            profile_mask = _profile_measurement_mask(profile)
            baseline_mask = _profile_measurement_mask(baseline)
            valid_mask = profile_mask & baseline_mask
            probe_mask = valid_mask & ((z_mm - baseline_z) >= threshold_mm)
            if np.any(probe_mask):
                first_probe_profile_y = float(y_value)
                break

    if first_probe_profile_y is None:
        return None

    return origin_x, first_probe_profile_y


def apply_probe_origin_to_profiles(
    profiles: list[dict],
    origin_x: float,
    origin_y: float,
) -> None:
    for profile in profiles:
        x_mm = profile.get("x_mm")
        if x_mm:
            profile["x_mm"] = [round(float(value) - origin_x, 6) for value in x_mm]
        if profile.get("y_mm") is not None:
            profile["y_mm"] = round(float(profile["y_mm"]) - origin_y, 6)


def align_profiles_to_probe_origin(
    profiles: list[dict],
    *,
    threshold_mm: float = PROBE_THRESHOLD_MM,
    exclude_probe_x_below_mm: float | None = None,
) -> dict | None:
    if not profiles:
        return None

    baseline_profiles = _select_baseline_profiles(profiles)
    baseline = _compute_baseline_profile(baseline_profiles)
    if baseline is None:
        return None

    origin = compute_probe_origin_mm(
        profiles,
        baseline,
        threshold_mm=threshold_mm,
        exclude_probe_x_below_mm=exclude_probe_x_below_mm,
    )
    if origin is None:
        return None

    origin_x, origin_y = origin
    apply_probe_origin_to_profiles(profiles, origin_x, origin_y)
    return {
        "origin_x_mm": round(origin_x, 6),
        "origin_y_mm": round(origin_y, 6),
        "probe_threshold_mm": threshold_mm,
    }


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

    probe_origin = scan_document.get("probe_origin")
    if probe_origin is None:
        probe_origin = align_profiles_to_probe_origin(profiles, threshold_mm=threshold_mm)

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

    filtered_profiles = _filter_profiles_to_probe_only(
        profiles,
        baseline,
        threshold_mm=threshold_mm,
    )
    if not all(profile.get("y_mm") is not None for profile in profiles):
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
        "probe_crop_margin_points": PROBE_CROP_MARGIN_POINTS,
        "scan_speed_mm_s": float(scan_speed_mm_s),
        "scan_duration_s": float(scan_duration_s),
        "profiles": filtered_profiles,
        **({"probe_origin": probe_origin} if probe_origin else {}),
    }


def _is_valid_median_point(profile: dict, index: int, z_value: float) -> bool:
    if z_value <= 0:
        return False

    mask = _profile_measurement_mask(profile)
    return bool(mask[index])


def generate_x_profile_document(cropped_scan_document: dict) -> dict:
    profiles = cropped_scan_document.get("profiles") or []
    if not profiles:
        raise ValueError("Keine Profile für X_profile gefunden.")

    resolution = len(profiles[0].get("x_mm") or [])
    if resolution == 0:
        raise ValueError("Keine x-Werte für X_profile gefunden.")

    x_mm = profiles[0]["x_mm"]
    x_values: list[float] = []
    z_values: list[float] = []

    for index in range(resolution):
        sample_z = [
            float(profile["z_mm"][index])
            for profile in profiles
            if _is_valid_median_point(profile, index, float(profile["z_mm"][index]))
        ]
        if not sample_z:
            continue

        x_values.append(round(float(x_mm[index]), 6))
        z_values.append(round(float(np.median(sample_z)), 6))

    if not x_values:
        raise ValueError("Keine gültigen Punkte für X_profile gefunden.")

    return {
        "experiment_id": cropped_scan_document.get("experiment_id"),
        "source_json_file": CROPPED_SCAN_FILENAME,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "point_count": len(x_values),
        "x_mm": x_values,
        "z_mm": z_values,
    }


def generate_y_profile_document(cropped_scan_document: dict) -> dict:
    profiles = cropped_scan_document.get("profiles") or []
    if not profiles:
        raise ValueError("Keine Profile für Y_profile gefunden.")

    y_values: list[float] = []
    z_values: list[float] = []

    for profile in profiles:
        y_mm = profile.get("y_mm")
        if y_mm is None:
            continue

        sample_z = [
            float(z_value)
            for index, z_value in enumerate(profile.get("z_mm") or [])
            if _is_valid_median_point(profile, index, float(z_value))
        ]
        if not sample_z:
            continue

        y_values.append(round(float(y_mm), 6))
        z_values.append(round(float(np.median(sample_z)), 6))

    if not y_values:
        raise ValueError("Keine gültigen Punkte für Y_profile gefunden.")

    return {
        "experiment_id": cropped_scan_document.get("experiment_id"),
        "source_json_file": CROPPED_SCAN_FILENAME,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "point_count": len(y_values),
        "y_mm": y_values,
        "z_mm": z_values,
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
    output_folder: Path,
    *,
    threshold_mm: float = PROBE_THRESHOLD_MM,
    scan_speed_mm_s: float | None = None,
    scan_duration_s: float | None = None,
) -> dict:
    experiment_id = experiment_id.strip().upper()
    scan_path = Path(scan_path)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

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

    output_path = output_folder / CROPPED_SCAN_FILENAME
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2)

    x_profile = generate_x_profile_document(document)
    y_profile = generate_y_profile_document(document)

    with (output_folder / X_PROFILE_FILENAME).open("w", encoding="utf-8") as handle:
        json.dump(x_profile, handle, indent=2)

    with (output_folder / Y_PROFILE_FILENAME).open("w", encoding="utf-8") as handle:
        json.dump(y_profile, handle, indent=2)

    return {
        "scan_file": CROPPED_SCAN_FILENAME,
        "x_profile_file": X_PROFILE_FILENAME,
        "y_profile_file": Y_PROFILE_FILENAME,
        "x_profile_point_count": x_profile["point_count"],
        "y_profile_point_count": y_profile["point_count"],
        "profile_count": document["profile_count"],
        "baseline_profile_count": document["baseline_profile_count"],
        "probe_threshold_mm": document["probe_threshold_mm"],
        "source_json_file": scan_path.name,
    }


def run_analyze_weld(
    experiment_id: str,
    weld_path: Path,
    output_folder: Path,
    *,
    config: WeldConfig | None = None,
) -> dict:
    experiment_id = experiment_id.strip().upper()
    weld_path = Path(weld_path)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    document = generate_analyzing_weld_h5(
        weld_path,
        experiment_id=experiment_id,
        source_h5_file=weld_path.name,
        config=config,
    )

    output_path = output_folder / CROPPED_WELD_FILENAME
    _save_weld_h5(output_path, document["time_s"], document["channels"])

    return {
        "weld_file": CROPPED_WELD_FILENAME,
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

    experiment_id = experiment_id.strip().upper()
    output_dir = Path(output_dir)
    timestamp = datetime.now()
    analyze_folder = build_analyze_folder_name(experiment_id, timestamp)
    output_folder = output_dir / analyze_folder
    output_folder.mkdir(parents=True, exist_ok=True)

    result: dict = {
        "success": True,
        "experiment_id": experiment_id,
        "analyze_folder": analyze_folder,
    }

    if scan_path is not None:
        result.update(
            run_analyze_scan(
                experiment_id,
                scan_path,
                output_folder,
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
                output_folder,
                config=weld_config,
            )
        )

    return result
