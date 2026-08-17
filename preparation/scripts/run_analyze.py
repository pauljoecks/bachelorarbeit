"""Generate analyzed scan JSON and weld H5 files from saved measurement data."""

from __future__ import annotations

import json
import sys
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import h5py
import numpy as np

_ACQUESITION_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "acquesition" / "scripts"
if str(_ACQUESITION_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_ACQUESITION_SCRIPTS_DIR))

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

PROBE_THRESHOLD_MM = 2.5
MIRROR_ORIGIN_EDGE_EXCLUSION_MM = 1.0
PROBE_CROP_MARGIN_POINTS = 0
WELD_CHUNK_FRACTION_S = 0.1
WELD_BASELINE_MIN_CHUNKS = 10
# Minimum fraction of (peak - idle) current change in one chunk to count as rise/fall.
WELD_EDGE_AMPLITUDE_FRACTION = 0.2
# Skip the arc-strike transient (sharp V drop + I rise) before cropping.
WELD_START_DELAY_S = 0.020
# Keep only this many seconds from the center of the detected weld phase.
WELD_CROPPED_CENTER_DURATION_S = 10.0
CROPPED_SCAN_FILENAME = "cropped_scan.json"
SCAN_64_64_FILENAME = "64_64_scan.json"
SCAN_64_64_GRID_SIZE = 64
CROPPED_WELD_FILENAME = "cropped_weld.h5"
POWER_H5_FILENAME = "power.h5"
CHARACTERISTICS_FILENAME = "characteristics.json"
GRENZEN_FILENAME = "grenzen.json"
CHAR_GRAPHEN_FILENAME = "char_graphen.json"
FILTERED_SCAN_FILENAME = "filtered.json"
SCAN_SUBDIR = "scan"
WELD_SUBDIR = "weld"
WELD_GRAPH_SOURCE = "current"
WELD_VOLTAGE_GRAPH_SOURCE = "voltage"
WELD_POWER_GRAPH_SOURCE = "power"
CURRENT_A_FIELD = "current_a"
CURRENT_STD_A_FIELD = "current_std_a"
CURRENT_MAX_A_FIELD = "current_max_a"
CURRENT_MIN_A_FIELD = "current_min_a"
CURRENT_RANGE_A_FIELD = "current_range_a"
CURRENT_SKEWNESS_A_FIELD = "current_skewness_a"
CURRENT_KURTOSIS_A_FIELD = "current_kurtosis_a"
CURRENT_SLOPE_A_PER_S_FIELD = "current_slope_a_per_s"
CURRENT_PULSE_INTEGRAL_FIELD = "current_pulse_integral_as"
VOLTAGE_V_FIELD = "voltage_v"
VOLTAGE_STD_V_FIELD = "voltage_std_v"
VOLTAGE_MAX_V_FIELD = "voltage_max_v"
VOLTAGE_MIN_V_FIELD = "voltage_min_v"
VOLTAGE_RANGE_V_FIELD = "voltage_range_v"
VOLTAGE_SKEWNESS_V_FIELD = "voltage_skewness_v"
VOLTAGE_KURTOSIS_V_FIELD = "voltage_kurtosis_v"
VOLTAGE_SLOPE_V_PER_S_FIELD = "voltage_slope_v_per_s"
VOLTAGE_PULSE_INTEGRAL_FIELD = "voltage_pulse_integral_vs"
POWER_W_FIELD = "power_w"
POWER_STD_W_FIELD = "power_std_w"
POWER_MAX_W_FIELD = "power_max_w"
POWER_MIN_W_FIELD = "power_min_w"
POWER_RANGE_W_FIELD = "power_range_w"
POWER_SKEWNESS_W_FIELD = "power_skewness_w"
POWER_KURTOSIS_W_FIELD = "power_kurtosis_w"
POWER_SLOPE_W_PER_S_FIELD = "power_slope_w_per_s"
POWER_PULSE_INTEGRAL_FIELD = "power_pulse_integral_j"
PULSE_DURATION_GRAPH_KEY = "pulse_duration"
ON_DURATION_GRAPH_KEY = "on_duration"
OFF_DURATION_GRAPH_KEY = "off_duration"
ON_DURATION_RATIO_GRAPH_KEY = "on_duration_ratio"
CURRENT_PULSE_INTEGRAL_GRAPH_KEY = "current_pulse_integral"
VOLTAGE_PULSE_INTEGRAL_GRAPH_KEY = "voltage_pulse_integral"
POWER_PULSE_INTEGRAL_GRAPH_KEY = "power_pulse_integral"
ON_DURATION_FIELD = "on_duration_s"
OFF_DURATION_FIELD = "off_duration_s"
ON_DURATION_RATIO_FIELD = "on_duration_ratio"

CHAR_GRAPHEN_GRAPH_SPECS = (
    ("current", "low", "mean", CURRENT_A_FIELD),
    ("current", "high", "mean", CURRENT_A_FIELD),
    ("current", "low", "standarddeviation", CURRENT_STD_A_FIELD),
    ("current", "high", "standarddeviation", CURRENT_STD_A_FIELD),
    ("current", "low", "max", CURRENT_MAX_A_FIELD),
    ("current", "high", "max", CURRENT_MAX_A_FIELD),
    ("current", "low", "min", CURRENT_MIN_A_FIELD),
    ("current", "high", "min", CURRENT_MIN_A_FIELD),
    ("current", "low", "range", CURRENT_RANGE_A_FIELD),
    ("current", "high", "range", CURRENT_RANGE_A_FIELD),
    ("current", "low", "skewness", CURRENT_SKEWNESS_A_FIELD),
    ("current", "high", "skewness", CURRENT_SKEWNESS_A_FIELD),
    ("current", "low", "kurtosis", CURRENT_KURTOSIS_A_FIELD),
    ("current", "high", "kurtosis", CURRENT_KURTOSIS_A_FIELD),
    ("current", "rise", "slope", CURRENT_SLOPE_A_PER_S_FIELD),
    ("current", "fall", "slope", CURRENT_SLOPE_A_PER_S_FIELD),
    ("voltage", "low", "mean", VOLTAGE_V_FIELD),
    ("voltage", "high", "mean", VOLTAGE_V_FIELD),
    ("voltage", "low", "standarddeviation", VOLTAGE_STD_V_FIELD),
    ("voltage", "high", "standarddeviation", VOLTAGE_STD_V_FIELD),
    ("voltage", "low", "max", VOLTAGE_MAX_V_FIELD),
    ("voltage", "high", "max", VOLTAGE_MAX_V_FIELD),
    ("voltage", "low", "min", VOLTAGE_MIN_V_FIELD),
    ("voltage", "high", "min", VOLTAGE_MIN_V_FIELD),
    ("voltage", "low", "range", VOLTAGE_RANGE_V_FIELD),
    ("voltage", "high", "range", VOLTAGE_RANGE_V_FIELD),
    ("voltage", "low", "skewness", VOLTAGE_SKEWNESS_V_FIELD),
    ("voltage", "high", "skewness", VOLTAGE_SKEWNESS_V_FIELD),
    ("voltage", "low", "kurtosis", VOLTAGE_KURTOSIS_V_FIELD),
    ("voltage", "high", "kurtosis", VOLTAGE_KURTOSIS_V_FIELD),
    ("voltage", "rise", "slope", VOLTAGE_SLOPE_V_PER_S_FIELD),
    ("voltage", "fall", "slope", VOLTAGE_SLOPE_V_PER_S_FIELD),
    ("power", "low", "mean", POWER_W_FIELD),
    ("power", "high", "mean", POWER_W_FIELD),
    ("power", "low", "standarddeviation", POWER_STD_W_FIELD),
    ("power", "high", "standarddeviation", POWER_STD_W_FIELD),
    ("power", "low", "max", POWER_MAX_W_FIELD),
    ("power", "high", "max", POWER_MAX_W_FIELD),
    ("power", "low", "min", POWER_MIN_W_FIELD),
    ("power", "high", "min", POWER_MIN_W_FIELD),
    ("power", "low", "range", POWER_RANGE_W_FIELD),
    ("power", "high", "range", POWER_RANGE_W_FIELD),
    ("power", "low", "skewness", POWER_SKEWNESS_W_FIELD),
    ("power", "high", "skewness", POWER_SKEWNESS_W_FIELD),
    ("power", "low", "kurtosis", POWER_KURTOSIS_W_FIELD),
    ("power", "high", "kurtosis", POWER_KURTOSIS_W_FIELD),
    ("power", "rise", "slope", POWER_SLOPE_W_PER_S_FIELD),
    ("power", "fall", "slope", POWER_SLOPE_W_PER_S_FIELD),
    ("", "low", "duration", "duration_s"),
    ("", "rise", "duration", "duration_s"),
    ("", "high", "duration", "duration_s"),
    ("", "fall", "duration", "duration_s"),
)
PULSE_INTEGRAL_GRAPH_SPECS = (
    ("current", "", "integral", CURRENT_PULSE_INTEGRAL_FIELD),
    ("voltage", "", "integral", VOLTAGE_PULSE_INTEGRAL_FIELD),
    ("power", "", "integral", POWER_PULSE_INTEGRAL_FIELD),
)
PULSE_DURATION_GRAPH_SPEC = ("pulse", "", "duration", "duration_s")
ON_DURATION_GRAPH_SPEC = ("on", "", "duration", ON_DURATION_FIELD)
OFF_DURATION_GRAPH_SPEC = ("off", "", "duration", OFF_DURATION_FIELD)
ON_DURATION_RATIO_GRAPH_SPEC = ("on", "", "ratio", ON_DURATION_RATIO_FIELD)
PULSE_LEVEL_GRAPH_SPECS = (
    PULSE_DURATION_GRAPH_SPEC,
    ON_DURATION_GRAPH_SPEC,
    OFF_DURATION_GRAPH_SPEC,
    ON_DURATION_RATIO_GRAPH_SPEC,
)


def char_graphen_graph_key(graph_source: str, region: str, analysis: str) -> str:
    if graph_source == "pulse" and analysis == "duration":
        return PULSE_DURATION_GRAPH_KEY
    if graph_source == "on" and analysis == "duration":
        return ON_DURATION_GRAPH_KEY
    if graph_source == "off" and analysis == "duration":
        return OFF_DURATION_GRAPH_KEY
    if graph_source == "on" and analysis == "ratio":
        return ON_DURATION_RATIO_GRAPH_KEY
    if analysis == "integral":
        return f"{graph_source}_pulse_integral"
    if analysis == "duration":
        return f"{region}_duration"
    return f"{graph_source}_{region}_{analysis}"



CHAR_GRAPHEN_GRAPH_KEYS = tuple(
    char_graphen_graph_key(graph_source, region, analysis)
    for graph_source, region, analysis, _field in (
        *CHAR_GRAPHEN_GRAPH_SPECS,
        *PULSE_LEVEL_GRAPH_SPECS,
        *PULSE_INTEGRAL_GRAPH_SPECS,
    )
)
WELD_REGION_GRAPH_KEYS = CHAR_GRAPHEN_GRAPH_KEYS

CURRENT_CHAR_GRAPHEN_GRAPH_KEYS = (
    *tuple(
        char_graphen_graph_key(graph_source, region, analysis)
        for graph_source, region, analysis, _field in CHAR_GRAPHEN_GRAPH_SPECS
        if graph_source == WELD_GRAPH_SOURCE
    ),
    CURRENT_PULSE_INTEGRAL_GRAPH_KEY,
)
VOLTAGE_CHAR_GRAPHEN_GRAPH_KEYS = (
    *tuple(
        char_graphen_graph_key(graph_source, region, analysis)
        for graph_source, region, analysis, _field in CHAR_GRAPHEN_GRAPH_SPECS
        if graph_source == WELD_VOLTAGE_GRAPH_SOURCE
    ),
    VOLTAGE_PULSE_INTEGRAL_GRAPH_KEY,
)
POWER_CHAR_GRAPHEN_GRAPH_KEYS = (
    *tuple(
        char_graphen_graph_key(graph_source, region, analysis)
        for graph_source, region, analysis, _field in CHAR_GRAPHEN_GRAPH_SPECS
        if graph_source == WELD_POWER_GRAPH_SOURCE
    ),
    POWER_PULSE_INTEGRAL_GRAPH_KEY,
)
REGION_DURATION_CHAR_GRAPHEN_GRAPH_KEYS = tuple(
    char_graphen_graph_key(graph_source, region, analysis)
    for graph_source, region, analysis, _field in CHAR_GRAPHEN_GRAPH_SPECS
    if analysis == "duration"
)
PULSE_LEVEL_CHAR_GRAPHEN_GRAPH_KEYS = (
    PULSE_DURATION_GRAPH_KEY,
    ON_DURATION_GRAPH_KEY,
    OFF_DURATION_GRAPH_KEY,
    ON_DURATION_RATIO_GRAPH_KEY,
)
DURATION_CHAR_GRAPHEN_GRAPH_KEYS = (
    *REGION_DURATION_CHAR_GRAPHEN_GRAPH_KEYS,
    *PULSE_LEVEL_CHAR_GRAPHEN_GRAPH_KEYS,
)


def _char_graphen_characteristic_keys_for_graphs(graph_keys: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        f"{graph_key}_{stat}"
        for graph_key in graph_keys
        for stat in ("mean", "standarddeviation")
    )


CHAR_GRAPHEN_CURRENT_CHARACTERISTIC_KEYS = _char_graphen_characteristic_keys_for_graphs(
    CURRENT_CHAR_GRAPHEN_GRAPH_KEYS,
)
CHAR_GRAPHEN_VOLTAGE_CHARACTERISTIC_KEYS = _char_graphen_characteristic_keys_for_graphs(
    VOLTAGE_CHAR_GRAPHEN_GRAPH_KEYS,
)
CHAR_GRAPHEN_POWER_CHARACTERISTIC_KEYS = _char_graphen_characteristic_keys_for_graphs(
    POWER_CHAR_GRAPHEN_GRAPH_KEYS,
)
CHAR_GRAPHEN_DURATION_CHARACTERISTIC_KEYS = _char_graphen_characteristic_keys_for_graphs(
    DURATION_CHAR_GRAPHEN_GRAPH_KEYS,
)
CHAR_GRAPHEN_CHARACTERISTIC_KEYS = (
    *CHAR_GRAPHEN_CURRENT_CHARACTERISTIC_KEYS,
    *CHAR_GRAPHEN_VOLTAGE_CHARACTERISTIC_KEYS,
    *CHAR_GRAPHEN_POWER_CHARACTERISTIC_KEYS,
    *CHAR_GRAPHEN_DURATION_CHARACTERISTIC_KEYS,
)
WELD_CYCLE_CATEGORIES = ("low", "rise", "high", "fall")
FILTER_KERNEL_SIZE = 9
X_PROFILE_FILENAME = "X_profile.json"
Y_PROFILE_FILENAME = "Y_profile.json"
# Keep generate_*_profile_document helpers; profiles are built from filtered.json.
GENERATE_AXIS_PROFILES = True

SCAN_GENERATE_KEYS = (
    "cropped_scan",
    "filtered",
    "x_profile",
    "y_profile",
    "characteristics",
    "64_64_scan",
)
WELD_GENERATE_KEYS = (
    "cropped",
    "power",
    "grenzen",
    "char_graphen",
    "characteristics",
)


def default_scan_generate_options() -> dict[str, bool]:
    return {key: True for key in SCAN_GENERATE_KEYS}


def default_weld_generate_options() -> dict[str, bool]:
    return {key: True for key in WELD_GENERATE_KEYS}


def normalize_generate_options(raw, valid_keys: tuple[str, ...]) -> dict[str, bool]:
    defaults = {key: True for key in valid_keys}
    if not isinstance(raw, dict):
        return defaults
    return {key: bool(raw.get(key, defaults[key])) for key in valid_keys}


def resolve_scan_generate_options(options: dict[str, bool]) -> dict[str, bool]:
    resolved = dict(options)
    if resolved.get("64_64_scan"):
        resolved["cropped_scan"] = True
    if resolved.get("filtered") or resolved.get("x_profile") or resolved.get("y_profile"):
        resolved["cropped_scan"] = True
    if resolved.get("x_profile") or resolved.get("y_profile"):
        resolved["filtered"] = True
    if resolved.get("characteristics"):
        resolved["filtered"] = True
        resolved["x_profile"] = True
        resolved["y_profile"] = True
    return resolved


def resolve_weld_generate_options(options: dict[str, bool]) -> dict[str, bool]:
    resolved = dict(options)
    if resolved.get("char_graphen"):
        resolved["grenzen"] = True
    return resolved


def forward_dependent_generate_keys(key: str, keys: tuple[str, ...]) -> tuple[str, ...]:
    try:
        index = keys.index(key)
    except ValueError:
        return ()
    return keys[index + 1:]


def collect_regenerate_deletion_keys(
    options: dict[str, bool],
    keys: tuple[str, ...],
) -> frozenset[str]:
    deletion_keys: set[str] = set()
    for index, key in enumerate(keys):
        if options.get(key):
            deletion_keys.update(keys[index:])
    # 64×64 depends only on cropped_scan — later scan steps do not invalidate it.
    if (
        "64_64_scan" in deletion_keys
        and not options.get("cropped_scan")
        and not options.get("64_64_scan")
    ):
        deletion_keys.discard("64_64_scan")
    return frozenset(deletion_keys)


def _artifact_relative_paths_for_generate_key(key: str) -> tuple[str, ...]:
    if key == "cropped_scan":
        return (f"{SCAN_SUBDIR}/{CROPPED_SCAN_FILENAME}",)
    if key == "64_64_scan":
        return (f"{SCAN_SUBDIR}/{SCAN_64_64_FILENAME}",)
    if key == "filtered":
        return (f"{SCAN_SUBDIR}/{FILTERED_SCAN_FILENAME}",)
    if key == "x_profile":
        return (f"{SCAN_SUBDIR}/{X_PROFILE_FILENAME}",)
    if key == "y_profile":
        return (f"{SCAN_SUBDIR}/{Y_PROFILE_FILENAME}",)
    if key == "cropped":
        return (f"{WELD_SUBDIR}/{CROPPED_WELD_FILENAME}",)
    if key == "power":
        return (f"{WELD_SUBDIR}/{POWER_H5_FILENAME}",)
    if key == "grenzen":
        return (f"{WELD_SUBDIR}/{GRENZEN_FILENAME}",)
    if key == "char_graphen":
        return (f"{WELD_SUBDIR}/{CHAR_GRAPHEN_FILENAME}",)
    if key == "characteristics":
        return ()
    return ()


def clear_characteristics_sections(
    output_folder: Path,
    *,
    clear_scan: bool = False,
    clear_weld: bool = False,
) -> list[str]:
    if not clear_scan and not clear_weld:
        return []

    char_path = Path(output_folder) / CHARACTERISTICS_FILENAME
    if not char_path.is_file():
        return []

    existing_doc = None
    try:
        existing_doc = load_characteristics(char_path)
    except ValueError:
        existing_doc = {"scan": {}, "weld": []}

    scan_fields = {} if clear_scan else dict(existing_doc.get("scan") or {})
    weld_rows = [] if clear_weld else list(existing_doc.get("weld") or [])

    cleared: list[str] = []
    if clear_scan:
        cleared.append(f"{CHARACTERISTICS_FILENAME}#scan")
    if clear_weld:
        cleared.append(f"{CHARACTERISTICS_FILENAME}#weld")

    if not scan_fields and not weld_rows:
        char_path.unlink()
        return cleared

    write_characteristics_file(
        char_path,
        scan_fields=scan_fields,
        weld_rows=weld_rows,
    )
    return cleared


def _has_scan_characteristics(output_folder: Path) -> bool:
    char_path = Path(output_folder) / CHARACTERISTICS_FILENAME
    if not char_path.is_file():
        return False
    try:
        document = load_characteristics(char_path)
    except ValueError:
        return False
    return bool(document.get("scan"))


def _has_weld_characteristics(output_folder: Path) -> bool:
    char_path = Path(output_folder) / CHARACTERISTICS_FILENAME
    if not char_path.is_file():
        return False
    try:
        document = load_characteristics(char_path)
    except ValueError:
        return False
    return bool(document.get("weld"))


def experiment_has_generate_artifact(output_folder: Path, *, section: str, key: str) -> bool:
    output_folder = Path(output_folder)
    if section == "scan":
        if key not in SCAN_GENERATE_KEYS:
            return False
        if key == "characteristics":
            return _has_scan_characteristics(output_folder)
    elif section == "weld":
        if key not in WELD_GENERATE_KEYS:
            return False
        if key == "characteristics":
            return _has_weld_characteristics(output_folder)
    else:
        return False

    for relative_path in _artifact_relative_paths_for_generate_key(key):
        if (output_folder / relative_path).is_file():
            return True
    return False


def delete_regenerate_artifacts(
    output_folder: Path,
    scan_options: dict[str, bool],
    weld_options: dict[str, bool],
) -> list[str]:
    output_folder = Path(output_folder)
    scan_deletion = collect_regenerate_deletion_keys(scan_options, SCAN_GENERATE_KEYS)
    weld_deletion = collect_regenerate_deletion_keys(weld_options, WELD_GENERATE_KEYS)
    deletion_keys = set(scan_deletion) | set(weld_deletion)

    deleted: list[str] = []
    seen_paths: set[Path] = set()
    for key in deletion_keys:
        if key == "characteristics":
            continue
        for relative_path in _artifact_relative_paths_for_generate_key(key):
            artifact_path = (output_folder / relative_path).resolve()
            if artifact_path in seen_paths or not artifact_path.is_file():
                continue
            seen_paths.add(artifact_path)
            artifact_path.unlink()
            deleted.append(relative_path.replace("\\", "/"))

    deleted.extend(
        clear_characteristics_sections(
            output_folder,
            clear_scan="characteristics" in scan_deletion,
            clear_weld="characteristics" in weld_deletion,
        ),
    )
    return deleted


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


def _average_filter_2d(
    values: np.ndarray,
    valid_mask: np.ndarray,
    *,
    kernel_size: int = FILTER_KERNEL_SIZE,
) -> np.ndarray:
    """Mean-filter valid points with a square neighborhood; invalid stays 0."""
    if kernel_size < 1 or kernel_size % 2 == 0:
        raise ValueError("kernel_size muss ungerade und >= 1 sein.")

    radius = kernel_size // 2
    padded_values = np.pad(values.astype(float, copy=False), radius, mode="constant", constant_values=0.0)
    padded_valid = np.pad(
        valid_mask.astype(float, copy=False),
        radius,
        mode="constant",
        constant_values=0.0,
    )

    value_windows = np.lib.stride_tricks.sliding_window_view(
        padded_values,
        (kernel_size, kernel_size),
    )
    valid_windows = np.lib.stride_tricks.sliding_window_view(
        padded_valid,
        (kernel_size, kernel_size),
    )

    neighbor_sum = (value_windows * valid_windows).sum(axis=(-1, -2))
    neighbor_count = valid_windows.sum(axis=(-1, -2))
    filtered = np.zeros_like(values, dtype=float)
    np.divide(neighbor_sum, neighbor_count, out=filtered, where=neighbor_count > 0)
    filtered[~valid_mask] = 0.0
    return filtered


def generate_filtered_scan_document(
    cropped_scan_document: dict,
    *,
    kernel_size: int = FILTER_KERNEL_SIZE,
) -> dict:
    profiles = cropped_scan_document.get("profiles") or []
    if not profiles:
        raise ValueError("Keine Profile in cropped_scan für den Noise-Filter gefunden.")

    resolution = len(profiles[0].get("x_mm") or [])
    if resolution <= 0:
        raise ValueError("Keine x-Werte für den Noise-Filter gefunden.")

    z_stack = np.stack([np.asarray(profile["z_mm"], dtype=float) for profile in profiles])
    intensity_stack = np.stack(
        [np.asarray(profile["intensities"], dtype=float) for profile in profiles]
    )
    valid_mask = z_stack > 0

    filtered_z = _average_filter_2d(z_stack, valid_mask, kernel_size=kernel_size)
    filtered_intensities = _average_filter_2d(
        intensity_stack,
        valid_mask,
        kernel_size=kernel_size,
    )

    filtered_profiles = []
    for index, profile in enumerate(profiles):
        filtered_profiles.append(
            {
                **profile,
                "profile_index": index,
                "z_mm": np.round(filtered_z[index], 6).astype(float).tolist(),
                "intensities": np.round(filtered_intensities[index]).astype(int).tolist(),
            }
        )

    return {
        **cropped_scan_document,
        "source_json_file": CROPPED_SCAN_FILENAME,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "filter": {
            "type": "average_2d",
            "kernel_size": int(kernel_size),
        },
        "profile_count": len(filtered_profiles),
        "profiles": filtered_profiles,
    }


def _tight_valid_bbox(valid_mask: np.ndarray) -> tuple[int, int, int, int]:
    rows = np.any(valid_mask, axis=1)
    cols = np.any(valid_mask, axis=0)
    if not rows.any() or not cols.any():
        raise ValueError("Keine gültigen Messpunkte für 64×64-Scan gefunden.")
    row_indices = np.flatnonzero(rows)
    col_indices = np.flatnonzero(cols)
    return (
        int(row_indices[0]),
        int(row_indices[-1]),
        int(col_indices[0]),
        int(col_indices[-1]),
    )


def _profile_y_mm_values(profiles: list[dict]) -> np.ndarray:
    y_values = []
    for profile in profiles:
        y_mm = profile.get("y_mm")
        if y_mm is None:
            raise ValueError("y_mm fehlt in cropped_scan-Profil.")
        y_values.append(float(y_mm))
    return np.asarray(y_values, dtype=float)


def _mean_pool_valid_2d(
    values: np.ndarray,
    valid_mask: np.ndarray,
    out_rows: int,
    out_cols: int,
) -> np.ndarray:
    """Downsample by mean of all valid source pixels in each output cell."""
    in_rows, in_cols = values.shape
    if in_rows < 1 or in_cols < 1:
        raise ValueError("Leeres Eingaberaster für 64×64-Resampling.")

    out = np.zeros((out_rows, out_cols), dtype=float)
    for oi in range(out_rows):
        r0 = (oi * in_rows) // out_rows
        r1 = ((oi + 1) * in_rows) // out_rows
        if r1 <= r0:
            r1 = min(r0 + 1, in_rows)

        for oj in range(out_cols):
            c0 = (oj * in_cols) // out_cols
            c1 = ((oj + 1) * in_cols) // out_cols
            if c1 <= c0:
                c1 = min(c0 + 1, in_cols)

            block_values = values[r0:r1, c0:c1]
            block_mask = valid_mask[r0:r1, c0:c1]
            keep = block_mask & np.isfinite(block_values) & (block_values > 0)
            if np.any(keep):
                out[oi, oj] = float(np.mean(block_values[keep]))

    return out


def generate_64_64_scan_document(
    cropped_scan_document: dict,
    *,
    grid_size: int = SCAN_64_64_GRID_SIZE,
) -> dict:
    profiles = cropped_scan_document.get("profiles") or []
    if not profiles:
        raise ValueError("Keine Profile in cropped_scan für 64×64-Scan gefunden.")

    z_stack, valid_mask = _stack_profile_z_and_valid_mask(profiles)
    row_start, row_end, col_start, col_end = _tight_valid_bbox(valid_mask)

    z_crop = z_stack[row_start : row_end + 1, col_start : col_end + 1]
    valid_crop = valid_mask[row_start : row_end + 1, col_start : col_end + 1]
    z_grid = _mean_pool_valid_2d(z_crop, valid_crop, grid_size, grid_size)

    y_mm_src = _profile_y_mm_values(profiles)
    x_mm_src = np.asarray(profiles[0]["x_mm"], dtype=float)
    if x_mm_src.size <= col_end:
        raise ValueError("x_mm-Auflösung passt nicht zum gültigen Probenbereich.")

    y_low = float(y_mm_src[row_start])
    y_high = float(y_mm_src[row_end])
    y_min = min(y_low, y_high)
    y_max = max(y_low, y_high)
    y_mm = np.linspace(y_min, y_max, grid_size)

    x_at_start = float(x_mm_src[col_start])
    x_at_end = float(x_mm_src[col_end])
    x_min = min(x_at_start, x_at_end)
    x_max = max(x_at_start, x_at_end)
    x_reversed = x_at_start > x_at_end
    if x_reversed:
        x_mm = np.linspace(x_max, x_min, grid_size)
    else:
        x_mm = np.linspace(x_min, x_max, grid_size)

    values = np.round(z_grid, 6).reshape(-1).astype(float).tolist()

    return {
        "experiment_id": cropped_scan_document.get("experiment_id"),
        "source_json_file": CROPPED_SCAN_FILENAME,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "grid_size": int(grid_size),
        "profile_count": int(grid_size),
        "resolution": int(grid_size),
        "x_min": round(x_min, 6),
        "x_max": round(x_max, 6),
        "x_reversed": bool(x_reversed),
        "y_min": round(y_min, 6),
        "y_max": round(y_max, 6),
        "y_mm": np.round(y_mm, 6).astype(float).tolist(),
        "x_mm": np.round(x_mm, 6).astype(float).tolist(),
        "values": values,
        "crop": {
            "profile_start": row_start,
            "profile_end": row_end,
            "column_start": col_start,
            "column_end": col_end,
        },
    }


def _nanmedian_axis(values: np.ndarray, axis: int) -> np.ndarray:
    with np.errstate(all="ignore"), warnings.catch_warnings():
        # Columns/rows that are entirely invalid yield NaN; filtered out by callers.
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.nanmedian(values, axis=axis)


def _stack_profile_z_and_valid_mask(
    profiles: list[dict],
) -> tuple[np.ndarray, np.ndarray]:
    """Return z stack (profiles × resolution) and valid measurement mask."""
    z_stack = np.stack([np.asarray(profile["z_mm"], dtype=float) for profile in profiles])
    valid_mask = np.stack(
        [
            _profile_measurement_mask(profile) & (np.asarray(profile["z_mm"], dtype=float) > 0)
            for profile in profiles
        ]
    )
    return z_stack, valid_mask


def fit_profile_hyperbola(
    t_mm: np.ndarray,
    z_mm: np.ndarray,
    *,
    sample_count: int = 200,
) -> dict | None:
    """
    Fit a rectangular hyperbola with linear trend:
        z(t) = a + b * t + c / (t - d)

    The pole ``d`` is searched outside the measured interval so the curve stays
    smooth over the profile. Returns None if the fit is not possible.
    """
    t = np.asarray(t_mm, dtype=float)
    z = np.asarray(z_mm, dtype=float)
    keep = np.isfinite(t) & np.isfinite(z)
    t = t[keep]
    z = z[keep]
    if t.size < 4:
        return None

    order = np.argsort(t)
    t = t[order]
    z = z[order]
    # Collapse duplicate t values by averaging z (stable design matrix).
    unique_t, inverse = np.unique(t, return_inverse=True)
    if unique_t.size < 4:
        return None
    if unique_t.size != t.size:
        sums = np.bincount(inverse, weights=z)
        counts = np.bincount(inverse)
        t = unique_t
        z = sums / np.maximum(counts, 1)

    t_min = float(t[0])
    t_max = float(t[-1])
    span = t_max - t_min
    if span <= 0:
        return None

    # Candidate poles outside [t_min, t_max], both sides, several distances.
    offsets = span * np.asarray(
        [0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0],
        dtype=float,
    )
    candidate_d = np.concatenate([t_min - offsets, t_max + offsets])

    best: dict | None = None
    z_mean = float(np.mean(z))
    ss_tot = float(np.sum((z - z_mean) ** 2))
    if ss_tot <= 0:
        return None

    ones = np.ones(t.size, dtype=float)
    for pole in candidate_d:
        denom = t - pole
        if np.any(np.abs(denom) < 1e-9):
            continue
        design = np.column_stack((ones, t, 1.0 / denom))
        try:
            coeffs, _, rank, _ = np.linalg.lstsq(design, z, rcond=None)
        except np.linalg.LinAlgError:
            continue
        if rank < 3:
            continue

        a, b, c = (float(coeffs[0]), float(coeffs[1]), float(coeffs[2]))
        z_hat = a + b * t + c / denom
        resid = z - z_hat
        ss_res = float(np.sum(resid ** 2))
        rmse = float(np.sqrt(ss_res / t.size))
        r2 = float(1.0 - (ss_res / ss_tot))
        if not np.isfinite(r2) or not np.isfinite(rmse):
            continue
        if best is None or ss_res < best["ss_res"]:
            best = {
                "a": a,
                "b": b,
                "c": c,
                "d": float(pole),
                "rmse": rmse,
                "r2": r2,
                "ss_res": ss_res,
                "formula": "z = a + b*t + c/(t - d)",
            }

    if best is None:
        return None

    eval_count = max(int(sample_count), 2)
    t_fit = np.linspace(t_min, t_max, eval_count)
    denom_fit = t_fit - best["d"]
    z_fit = best["a"] + best["b"] * t_fit + best["c"] / denom_fit
    best.pop("ss_res", None)
    curvature = compute_hyperbola_curvature(
        best["a"],
        best["b"],
        best["c"],
        best["d"],
        t_min,
        t_max,
    )
    best["t_mm"] = np.round(t_fit, 6).astype(float).tolist()
    best["z_mm"] = np.round(z_fit, 6).astype(float).tolist()
    best["point_count"] = int(eval_count)
    best["r2"] = round(best["r2"], 6)
    best["rmse"] = round(best["rmse"], 6)
    best["a"] = round(best["a"], 9)
    best["b"] = round(best["b"], 9)
    best["c"] = round(best["c"], 9)
    best["d"] = round(best["d"], 9)
    if curvature is not None:
        best.update(curvature)
    return best


def compute_hyperbola_curvature(
    a: float,
    b: float,
    c: float,
    d: float,
    t_min: float,
    t_max: float,
) -> dict | None:
    """
    Signed curvature κ = z'' / (1 + (z')^2)^(3/2) for z = a + b*t + c/(t - d).

    Coordinates are in mm; returned curvature is converted to 1/m (κ_m = κ_mm * 1000).

    Prefer κ at a z-extremum inside [t_min, t_max] (where z'=0).
    Otherwise use the location of maximum |κ| in the interval.
    """
    if not np.isfinite([a, b, c, d, t_min, t_max]).all() or t_max <= t_min:
        return None

    def derivatives(t: float) -> tuple[float, float]:
        u = t - d
        if abs(u) < 1e-12:
            return float("nan"), float("nan")
        zp = b - c / (u * u)
        zpp = 2.0 * c / (u * u * u)
        return float(zp), float(zpp)

    def signed_kappa(t: float) -> float:
        zp, zpp = derivatives(t)
        if not np.isfinite(zp) or not np.isfinite(zpp):
            return float("nan")
        return float(zpp / ((1.0 + zp * zp) ** 1.5))

    candidate_t: list[float] = []
    if abs(b) > 1e-15:
        ratio = c / b
        if ratio > 0:
            root = float(np.sqrt(ratio))
            for t_star in (d + root, d - root):
                if t_min <= t_star <= t_max:
                    zp, _zpp = derivatives(t_star)
                    if np.isfinite(zp) and abs(zp) < 1e-6 * max(1.0, abs(b)):
                        candidate_t.append(t_star)

    if candidate_t:
        scored = [(abs(signed_kappa(t)), t) for t in candidate_t]
        scored = [(mag, t) for mag, t in scored if np.isfinite(mag)]
        if scored:
            _mag, t_sel = max(scored, key=lambda item: item[0])
            kappa = signed_kappa(t_sel)
            if np.isfinite(kappa):
                return {
                    "curvature_1_per_m": round(float(kappa) * 1000.0, 9),
                    "curvature_t_mm": round(float(t_sel), 6),
                    "curvature_source": "extremum",
                }

    sample_t = np.linspace(t_min, t_max, 401)
    kappas = np.asarray([signed_kappa(float(t)) for t in sample_t], dtype=float)
    finite = np.isfinite(kappas)
    if not np.any(finite):
        return None

    idx = int(np.nanargmax(np.abs(kappas)))
    return {
        "curvature_1_per_m": round(float(kappas[idx]) * 1000.0, 9),
        "curvature_t_mm": round(float(sample_t[idx]), 6),
        "curvature_source": "max_abs",
    }


def generate_x_profile_document(cropped_scan_document: dict) -> dict:
    profiles = cropped_scan_document.get("profiles") or []
    if not profiles:
        raise ValueError("Keine Profile für X_profile gefunden.")

    resolution = len(profiles[0].get("x_mm") or [])
    if resolution == 0:
        raise ValueError("Keine x-Werte für X_profile gefunden.")

    x_mm = np.asarray(profiles[0]["x_mm"], dtype=float)
    z_stack, valid_mask = _stack_profile_z_and_valid_mask(profiles)

    # Median along profile axis for each x column, ignoring invalid points.
    masked_z = np.where(valid_mask, z_stack, np.nan)
    column_medians = _nanmedian_axis(masked_z, axis=0)

    keep = np.isfinite(column_medians)
    if not np.any(keep):
        raise ValueError("Keine gültigen Punkte für X_profile gefunden.")

    x_values = np.round(x_mm[keep], 6).astype(float)
    z_values = np.round(column_medians[keep], 6).astype(float)
    hyperbola = fit_profile_hyperbola(x_values, z_values)

    document = {
        "experiment_id": cropped_scan_document.get("experiment_id"),
        "source_json_file": FILTERED_SCAN_FILENAME,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "point_count": int(x_values.size),
        "x_mm": x_values.tolist(),
        "z_mm": z_values.tolist(),
    }
    if hyperbola is not None:
        document["hyperbola"] = hyperbola
    return document


def generate_y_profile_document(cropped_scan_document: dict) -> dict:
    profiles = cropped_scan_document.get("profiles") or []
    if not profiles:
        raise ValueError("Keine Profile für Y_profile gefunden.")

    y_mm = np.asarray(
        [profile.get("y_mm") for profile in profiles],
        dtype=float,
    )
    has_y = np.isfinite(y_mm)
    if not np.any(has_y):
        raise ValueError("Keine gültigen Punkte für Y_profile gefunden.")

    selected_profiles = [profile for profile, keep in zip(profiles, has_y) if keep]
    selected_y = y_mm[has_y]
    z_stack, valid_mask = _stack_profile_z_and_valid_mask(selected_profiles)

    masked_z = np.where(valid_mask, z_stack, np.nan)
    row_medians = _nanmedian_axis(masked_z, axis=1)

    keep = np.isfinite(row_medians)
    if not np.any(keep):
        raise ValueError("Keine gültigen Punkte für Y_profile gefunden.")

    y_values = np.round(selected_y[keep], 6).astype(float)
    z_values = np.round(row_medians[keep], 6).astype(float)
    hyperbola = fit_profile_hyperbola(y_values, z_values)

    document = {
        "experiment_id": cropped_scan_document.get("experiment_id"),
        "source_json_file": FILTERED_SCAN_FILENAME,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "point_count": int(y_values.size),
        "y_mm": y_values.tolist(),
        "z_mm": z_values.tolist(),
    }
    if hyperbola is not None:
        document["hyperbola"] = hyperbola
    return document


def compute_filtered_surface_curvature(filtered_scan_document: dict) -> dict | None:
    """
    Fit a quadratic surface on filtered z(x, y) and return mean curvature H.

        z(x, y) = a + b x + c y + d x² + e x y + f y²

    Coordinates are in mm; returned curvature is converted to 1/m (κ_m = κ_mm * 1000).
    Prefer H at a gradient-zero vertex inside the measured domain.
    Otherwise evaluate H at the centroid of the valid points.
    """
    profiles = filtered_scan_document.get("profiles") or []
    if not profiles:
        return None

    x_mm = np.asarray(profiles[0].get("x_mm") or [], dtype=float)
    if x_mm.size == 0 or not np.any(np.isfinite(x_mm)):
        return None

    try:
        y_mm = _profile_y_mm_values(profiles)
    except ValueError:
        return None

    z_stack, valid_mask = _stack_profile_z_and_valid_mask(profiles)
    row_ok = np.isfinite(y_mm)
    if not np.any(row_ok):
        return None
    z_stack = z_stack[row_ok]
    valid_mask = valid_mask[row_ok]
    y_mm = y_mm[row_ok]

    xx, yy = np.meshgrid(x_mm, y_mm)
    keep = (
        valid_mask
        & np.isfinite(z_stack)
        & np.isfinite(xx)
        & np.isfinite(yy)
        & (z_stack > 0)
    )
    if int(np.count_nonzero(keep)) < 6:
        return None

    x = xx[keep]
    y = yy[keep]
    z = z_stack[keep]

    x_mean = float(np.mean(x))
    y_mean = float(np.mean(y))
    z_mean = float(np.mean(z))
    sx = float(np.std(x))
    sy = float(np.std(y))
    if sx <= 1e-12 or sy <= 1e-12:
        return None

    xn = (x - x_mean) / sx
    yn = (y - y_mean) / sy
    zn = z - z_mean
    design = np.column_stack((np.ones(xn.size), xn, yn, xn * xn, xn * yn, yn * yn))
    try:
        coeffs, _residuals, rank, _sv = np.linalg.lstsq(design, zn, rcond=None)
    except np.linalg.LinAlgError:
        return None
    if rank < 6:
        return None

    _a, b, c, d, e, f = (float(value) for value in coeffs)

    z_hat = design @ coeffs
    resid = zn - z_hat
    ss_res = float(np.sum(resid ** 2))
    ss_tot = float(np.sum((zn - float(np.mean(zn))) ** 2))
    r2 = float(1.0 - (ss_res / ss_tot)) if ss_tot > 0 else float("nan")
    rmse = float(np.sqrt(ss_res / zn.size))

    zxx = 2.0 * d / (sx * sx)
    zyy = 2.0 * f / (sy * sy)
    zxy = e / (sx * sy)

    def signed_h(xn_val: np.ndarray, yn_val: np.ndarray) -> np.ndarray:
        zx = (b + 2.0 * d * xn_val + e * yn_val) / sx
        zy = (c + e * xn_val + 2.0 * f * yn_val) / sy
        numer = (1.0 + zy * zy) * zxx - 2.0 * zx * zy * zxy + (1.0 + zx * zx) * zyy
        denom = 2.0 * np.power(1.0 + zx * zx + zy * zy, 1.5)
        with np.errstate(divide="ignore", invalid="ignore"):
            return numer / denom

    x_min = float(np.min(x))
    x_max = float(np.max(x))
    y_min = float(np.min(y))
    y_max = float(np.max(y))

    def in_domain(x_val: float, y_val: float) -> bool:
        return x_min <= x_val <= x_max and y_min <= y_val <= y_max

    source = "centroid"
    x_sel = x_mean
    y_sel = y_mean
    kappa = float(signed_h(np.asarray(0.0), np.asarray(0.0)))
    hess = np.array([[2.0 * d, e], [e, 2.0 * f]], dtype=float)
    try:
        xn_star, yn_star = np.linalg.solve(hess, np.array([-b, -c], dtype=float))
        x_star = float(xn_star * sx + x_mean)
        y_star = float(yn_star * sy + y_mean)
        if np.isfinite([x_star, y_star]).all() and in_domain(x_star, y_star):
            h_star = float(signed_h(np.asarray(xn_star), np.asarray(yn_star)))
            if np.isfinite(h_star):
                source = "extremum"
                x_sel = x_star
                y_sel = y_star
                kappa = h_star
    except np.linalg.LinAlgError:
        pass

    if not np.isfinite(kappa):
        return None

    result = {
        "curvature_1_per_m": round(float(kappa) * 1000.0, 9),
        "curvature_x_mm": round(float(x_sel), 6),
        "curvature_y_mm": round(float(y_sel), 6),
        "curvature_source": source,
        "point_count": int(z.size),
        "formula": "z = a + b*x + c*y + d*x^2 + e*x*y + f*y^2",
    }
    if np.isfinite(r2):
        result["r2"] = round(r2, 6)
    if np.isfinite(rmse):
        result["rmse"] = round(rmse, 6)
    return result


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


def _channel_kind(label: str, units: str) -> str:
    label_l = (label or "").strip().lower()
    units_l = (units or "").strip().lower()
    if label_l in {"strom", "current"} or units_l in {"a", "amp", "ampere"}:
        return "current"
    if label_l in {"spannung", "voltage"} or units_l in {"v", "volt", "volts"}:
        return "voltage"
    return "unknown"


def _find_current_channel(
    channels: list[tuple[str, np.ndarray, str, str]],
) -> tuple[str, np.ndarray, str, str]:
    # Prefer explicit current label/units (supports legacy "current"/"A" and new "Strom"/"A").
    for channel in channels:
        _key, _values, label, units = channel
        if _channel_kind(label, units) == "current":
            return channel

    by_key = {key: channel for key, channel in ((channel[0], channel) for channel in channels)}
    channel_0 = by_key.get("channel_0")
    channel_1 = by_key.get("channel_1")

    # Legacy H5 layout: channel_0=voltage, channel_1=current.
    if channel_0 is not None and channel_1 is not None:
        if _channel_kind(channel_0[2], channel_0[3]) == "voltage":
            return channel_1
        # Newer layout from run_weld: channel_0=Strom, channel_1=Spannung.
        if _channel_kind(channel_0[2], channel_0[3]) != "voltage":
            return channel_0

    if channel_1 is not None:
        return channel_1
    if channel_0 is not None:
        return channel_0

    raise ValueError("Stromkanal in H5-Datei nicht gefunden.")


def _find_voltage_channel(
    channels: list[tuple[str, np.ndarray, str, str]],
) -> tuple[str, np.ndarray, str, str]:
    for channel in channels:
        _key, _values, label, units = channel
        if _channel_kind(label, units) == "voltage":
            return channel

    by_key = {key: channel for key, channel in ((channel[0], channel) for channel in channels)}
    channel_0 = by_key.get("channel_0")
    channel_1 = by_key.get("channel_1")

    # Legacy H5 layout: channel_0=voltage, channel_1=current.
    if channel_0 is not None and channel_1 is not None:
        if _channel_kind(channel_0[2], channel_0[3]) == "voltage":
            return channel_0
        if _channel_kind(channel_1[2], channel_1[3]) == "voltage":
            return channel_1
        # Newer layout from run_weld: channel_0=Strom, channel_1=Spannung.
        if _channel_kind(channel_0[2], channel_0[3]) == "current":
            return channel_1

    if channel_0 is not None and _channel_kind(channel_0[2], channel_0[3]) != "current":
        return channel_0
    if channel_1 is not None:
        return channel_1

    raise ValueError("Spannungskanal in H5-Datei nicht gefunden.")


def _dump_json(path: Path, document: dict, *, compact: bool = False) -> None:
    with path.open("w", encoding="utf-8") as handle:
        if compact:
            json.dump(document, handle, separators=(",", ":"))
        else:
            json.dump(document, handle, indent=2)


def _as_float32_weld_payload(
    time_s: np.ndarray,
    channels: list[tuple[str, np.ndarray, str, str]],
) -> tuple[np.ndarray, list[tuple[str, np.ndarray, str, str]]]:
    """Halve analyze H5 size/I/O; float32 is enough for plots."""
    return (
        np.asarray(time_s, dtype=np.float32),
        [
            (key, np.asarray(values, dtype=np.float32), label, units)
            for key, values, label, units in channels
        ],
    )


def _compute_power_channels(
    time_s: np.ndarray,
    channels: list[tuple[str, np.ndarray, str, str]],
) -> tuple[np.ndarray, list[tuple[str, np.ndarray, str, str]]]:
    _current_key, current_a, _current_label, _current_units = _find_current_channel(channels)
    _voltage_key, voltage_v, _voltage_label, _voltage_units = _find_voltage_channel(channels)

    sample_count = min(time_s.size, current_a.size, voltage_v.size)
    if sample_count <= 0:
        raise ValueError("Keine Messdaten für Power.")

    time_s = np.asarray(time_s[:sample_count], dtype=np.float32)
    current_a = np.asarray(current_a[:sample_count], dtype=np.float32)
    voltage_v = np.asarray(voltage_v[:sample_count], dtype=np.float32)

    power_w = voltage_v * current_a
    power_channels = [("channel_0", power_w, "Power", "W")]
    return time_s, power_channels


def _mean_median(values: np.ndarray) -> tuple[float, float]:
    arr = np.asarray(values, dtype=np.float64)
    if arr.size == 0 or not np.isfinite(arr).any():
        return float("nan"), float("nan")
    return float(np.nanmean(arr)), float(np.nanmedian(arr))


SCAN_CHARACTERISTIC_FIELDS = (
    "X_curvature",
    "Y_curvature",
    "Total_curvature_mean",
    "Total_curvature_rms",
    "Surface_curvature",
)

WELD_CURRENT_QUANTITY = "current"
WELD_VOLTAGE_QUANTITY = "voltage"
WELD_POWER_QUANTITY = "power"

WELD_CURRENT_STAT_FIELDS = (
    "current_mean",
    "current_std",
    "current_skewness",
    "current_kurtosis",
    "current_p02",
    "current_p98",
    "current_p02_p98_mid",
    "current_p02_p98_1_5",
    "current_p02_p98_4_5",
)

WELD_VOLTAGE_STAT_FIELDS = (
    "voltage_mean",
    "voltage_std",
    "voltage_skewness",
    "voltage_kurtosis",
    "voltage_p02",
    "voltage_p98",
    "voltage_p02_p98_mid",
    "voltage_p02_p98_1_5",
    "voltage_p02_p98_4_5",
)

WELD_POWER_STAT_FIELDS = (
    "power_mean",
    "power_std",
    "power_skewness",
    "power_kurtosis",
    "power_p02",
    "power_p98",
    "power_p02_p98_mid",
    "power_p02_p98_1_5",
    "power_p02_p98_4_5",
)

WELD_CURRENT_CHARACTERISTIC_FIELDS = (
    *WELD_CURRENT_STAT_FIELDS,
    *CHAR_GRAPHEN_CURRENT_CHARACTERISTIC_KEYS,
)
WELD_VOLTAGE_CHARACTERISTIC_FIELDS = (
    *WELD_VOLTAGE_STAT_FIELDS,
    *CHAR_GRAPHEN_VOLTAGE_CHARACTERISTIC_KEYS,
)
WELD_POWER_CHARACTERISTIC_FIELDS = (
    *WELD_POWER_STAT_FIELDS,
    *CHAR_GRAPHEN_POWER_CHARACTERISTIC_KEYS,
)
WELD_DURATION_CHARACTERISTIC_FIELDS = CHAR_GRAPHEN_DURATION_CHARACTERISTIC_KEYS


def list_weld_characteristic_keys() -> tuple[str, ...]:
    """Stable-order metric keys from characteristics.json weld subsection."""
    return (
        *WELD_CURRENT_CHARACTERISTIC_FIELDS,
        *WELD_VOLTAGE_CHARACTERISTIC_FIELDS,
        *WELD_POWER_CHARACTERISTIC_FIELDS,
        *WELD_DURATION_CHARACTERISTIC_FIELDS,
    )


def list_all_characteristic_keys() -> tuple[str, ...]:
    """Flat, stable-order list of every characteristics.json metric key."""
    return (
        *SCAN_CHARACTERISTIC_FIELDS,
        *WELD_CURRENT_CHARACTERISTIC_FIELDS,
        *WELD_VOLTAGE_CHARACTERISTIC_FIELDS,
        *WELD_POWER_CHARACTERISTIC_FIELDS,
        *WELD_DURATION_CHARACTERISTIC_FIELDS,
    )


def _json_safe_characteristic_value(value):
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(number):
        return None
    return number


def _normalize_scan_characteristics(raw) -> dict[str, float]:
    if not isinstance(raw, dict):
        return {}
    fields: dict[str, float] = {}
    for key in SCAN_CHARACTERISTIC_FIELDS:
        value = _json_safe_characteristic_value(raw.get(key))
        if value is not None:
            fields[key] = value
    return fields


def _serialize_scan_characteristics(fields: dict) -> dict[str, float]:
    payload: dict[str, float] = {}
    for key in SCAN_CHARACTERISTIC_FIELDS:
        value = _json_safe_characteristic_value(fields.get(key))
        if value is not None:
            payload[key] = value
    return payload


def _normalize_weld_quantity(quantity) -> str:
    normalized = str(quantity or "").strip()
    if normalized.lower() == WELD_CURRENT_QUANTITY:
        return WELD_CURRENT_QUANTITY
    if normalized.lower() == WELD_VOLTAGE_QUANTITY:
        return WELD_VOLTAGE_QUANTITY
    if normalized.lower() == WELD_POWER_QUANTITY:
        return WELD_POWER_QUANTITY
    return normalized


def _apply_weld_signal_mid_percentiles(
    row: dict,
    *,
    prefix: str,
    p98: float | None = None,
) -> dict:
    row = dict(row)
    p02_key = f"{prefix}_p02"
    p98_key = f"{prefix}_p98"
    mid_key = f"{prefix}_p02_p98_mid"
    level_1_5_key = f"{prefix}_p02_p98_1_5"
    level_4_5_key = f"{prefix}_p02_p98_4_5"

    p02 = _json_safe_characteristic_value(row.get(p02_key))
    p98_value = _json_safe_characteristic_value(p98 if p98 is not None else row.get(p98_key))
    if p98_value is None:
        mid = _json_safe_characteristic_value(row.get(mid_key))
        if p02 is not None and mid is not None:
            p98_value = 2.0 * mid - p02
    if p02 is not None and p98_value is not None:
        span = p98_value - p02
        row[p98_key] = p98_value
        row[mid_key] = p02 + span * 0.5
        row[level_1_5_key] = p02 + span * (1.0 / 5.0)
        row[level_4_5_key] = p02 + span * (4.0 / 5.0)
    return row


def _apply_weld_mid_percentiles(row: dict, *, p98: float | None = None) -> dict:
    return _apply_weld_signal_mid_percentiles(row, prefix="current", p98=p98)


def _apply_weld_voltage_mid_percentiles(row: dict, *, p98: float | None = None) -> dict:
    return _apply_weld_signal_mid_percentiles(row, prefix="voltage", p98=p98)


def _apply_weld_power_mid_percentiles(row: dict, *, p98: float | None = None) -> dict:
    return _apply_weld_signal_mid_percentiles(row, prefix="power", p98=p98)


def _normalize_weld_duration_characteristic_row(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    row: dict = {}
    has_value = False
    for field in WELD_DURATION_CHARACTERISTIC_FIELDS:
        value = _json_safe_characteristic_value(raw.get(field))
        if value is not None:
            row[field] = value
            has_value = True
    if not has_value:
        return None
    return row


def _serialize_weld_duration_characteristic_row(row: dict) -> dict:
    payload: dict = {}
    for field in WELD_DURATION_CHARACTERISTIC_FIELDS:
        value = _json_safe_characteristic_value(row.get(field))
        if value is not None:
            payload[field] = value
    return payload


def _normalize_weld_voltage_characteristic_row(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    quantity = _normalize_weld_quantity(raw.get("quantity", ""))
    if quantity != WELD_VOLTAGE_QUANTITY:
        return None
    row = {"quantity": WELD_VOLTAGE_QUANTITY}
    has_value = False
    for field in WELD_VOLTAGE_CHARACTERISTIC_FIELDS:
        value = _json_safe_characteristic_value(raw.get(field))
        if value is not None:
            row[field] = value
            has_value = True
    if not has_value:
        return None
    return _apply_weld_voltage_mid_percentiles(row)


def _serialize_weld_voltage_characteristic_row(row: dict) -> dict:
    payload = {"quantity": WELD_VOLTAGE_QUANTITY}
    for field in WELD_VOLTAGE_CHARACTERISTIC_FIELDS:
        value = _json_safe_characteristic_value(row.get(field))
        if value is not None:
            payload[field] = value
    return payload


def _normalize_weld_power_characteristic_row(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    quantity = _normalize_weld_quantity(raw.get("quantity", ""))
    if quantity != WELD_POWER_QUANTITY:
        return None
    row = {"quantity": WELD_POWER_QUANTITY}
    has_value = False
    for field in WELD_POWER_CHARACTERISTIC_FIELDS:
        value = _json_safe_characteristic_value(raw.get(field))
        if value is not None:
            row[field] = value
            has_value = True
    if not has_value:
        return None
    return _apply_weld_power_mid_percentiles(row)


def _serialize_weld_power_characteristic_row(row: dict) -> dict:
    payload = {"quantity": WELD_POWER_QUANTITY}
    for field in WELD_POWER_CHARACTERISTIC_FIELDS:
        value = _json_safe_characteristic_value(row.get(field))
        if value is not None:
            payload[field] = value
    return payload


def _split_char_graphen_characteristic_fields(
    fields: dict[str, float],
) -> tuple[dict[str, float], dict[str, float], dict[str, float], dict[str, float]]:
    current_fields: dict[str, float] = {}
    voltage_fields: dict[str, float] = {}
    power_fields: dict[str, float] = {}
    duration_fields: dict[str, float] = {}
    for key, value in fields.items():
        if key in CHAR_GRAPHEN_DURATION_CHARACTERISTIC_KEYS:
            duration_fields[key] = value
        elif key in CHAR_GRAPHEN_POWER_CHARACTERISTIC_KEYS:
            power_fields[key] = value
        elif key in CHAR_GRAPHEN_VOLTAGE_CHARACTERISTIC_KEYS:
            voltage_fields[key] = value
        elif key in CHAR_GRAPHEN_CURRENT_CHARACTERISTIC_KEYS:
            current_fields[key] = value
    return current_fields, voltage_fields, power_fields, duration_fields


def _normalize_weld_characteristic_row(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    quantity = _normalize_weld_quantity(raw.get("quantity", ""))
    if quantity != WELD_CURRENT_QUANTITY:
        return None
    row = {"quantity": quantity}
    stat_fields = WELD_CURRENT_CHARACTERISTIC_FIELDS
    has_value = False
    for field in stat_fields:
        value = _json_safe_characteristic_value(raw.get(field))
        if value is not None:
            row[field] = value
            has_value = True
    if not has_value:
        return None
    if quantity == WELD_CURRENT_QUANTITY:
        row = _apply_weld_mid_percentiles(row)
    return row


def _serialize_weld_characteristic_row(row: dict) -> dict:
    quantity = _normalize_weld_quantity(row.get("quantity", "")) if "quantity" in row else ""
    if quantity == WELD_CURRENT_QUANTITY:
        payload = {
            "quantity": WELD_CURRENT_QUANTITY,
        }
        stat_fields = WELD_CURRENT_CHARACTERISTIC_FIELDS
    elif quantity == WELD_VOLTAGE_QUANTITY:
        return _serialize_weld_voltage_characteristic_row(row)
    elif quantity == WELD_POWER_QUANTITY:
        return _serialize_weld_power_characteristic_row(row)
    else:
        return _serialize_weld_duration_characteristic_row(row)
    for field in stat_fields:
        value = _json_safe_characteristic_value(row.get(field))
        if value is not None:
            payload[field] = value
    return payload


def build_weld_current_characteristic_row(
    time_s: np.ndarray,
    channels: list[tuple[str, np.ndarray, str, str]],
) -> dict | None:
    """Current statistics from cropped weld channels."""
    _key, current_a, _label, units = _find_current_channel(channels)
    arr = np.asarray(current_a, dtype=np.float64)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return None

    p02, p98 = np.percentile(finite, [2, 98])
    row = {
        "quantity": WELD_CURRENT_QUANTITY,
        "current_mean": float(np.mean(finite)),
        "current_std": float(np.std(finite)),
        "current_p02": float(p02),
    }
    skewness = _skewness_finite(finite)
    if skewness is not None:
        row["current_skewness"] = skewness
    kurtosis = _kurtosis_finite(finite)
    if kurtosis is not None:
        row["current_kurtosis"] = kurtosis
    row = _apply_weld_mid_percentiles(row, p98=float(p98))
    return row


def build_weld_voltage_characteristic_row(
    time_s: np.ndarray,
    channels: list[tuple[str, np.ndarray, str, str]],
) -> dict | None:
    """Voltage statistics from cropped weld channels."""
    _key, voltage_v, _label, _units = _find_voltage_channel(channels)
    arr = np.asarray(voltage_v, dtype=np.float64)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return None

    p02, p98 = np.percentile(finite, [2, 98])
    row = {
        "quantity": WELD_VOLTAGE_QUANTITY,
        "voltage_mean": float(np.mean(finite)),
        "voltage_std": float(np.std(finite)),
        "voltage_p02": float(p02),
    }
    skewness = _skewness_finite(finite)
    if skewness is not None:
        row["voltage_skewness"] = skewness
    kurtosis = _kurtosis_finite(finite)
    if kurtosis is not None:
        row["voltage_kurtosis"] = kurtosis
    row = _apply_weld_voltage_mid_percentiles(row, p98=float(p98))
    return row


def build_weld_power_characteristic_row(
    time_s: np.ndarray,
    channels: list[tuple[str, np.ndarray, str, str]],
) -> dict | None:
    """Power statistics from cropped weld channels (V × I)."""
    _time_s, power_channels = _compute_power_channels(time_s, channels)
    if not power_channels:
        return None
    _key, power_w, _label, _units = power_channels[0]
    arr = np.asarray(power_w, dtype=np.float64)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return None

    p02, p98 = np.percentile(finite, [2, 98])
    row = {
        "quantity": WELD_POWER_QUANTITY,
        "power_mean": float(np.mean(finite)),
        "power_std": float(np.std(finite)),
        "power_p02": float(p02),
    }
    skewness = _skewness_finite(finite)
    if skewness is not None:
        row["power_skewness"] = skewness
    kurtosis = _kurtosis_finite(finite)
    if kurtosis is not None:
        row["power_kurtosis"] = kurtosis
    row = _apply_weld_power_mid_percentiles(row, p98=float(p98))
    return row


WELD_GRENZEN_CLUSTER_S = 0.00025
WELD_GRENZEN_LEVELS = ("current_p02_p98_1_5", "current_p02_p98_4_5")
WELD_FALL_MIN_QUAD_A_PER_S2 = 1e-9


def _detect_current_threshold_crossing_arrays(
    time_s: np.ndarray,
    current_a: np.ndarray,
    threshold_a: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Return crossing times and rising flags for threshold crossings."""
    time_s = np.asarray(time_s, dtype=np.float64)
    current_a = np.asarray(current_a, dtype=np.float64)
    count = min(time_s.size, current_a.size)
    if count < 2 or not np.isfinite(threshold_a):
        return np.empty(0, dtype=np.float64), np.empty(0, dtype=bool)

    time_s = time_s[:count]
    current_a = current_a[:count]
    valid = np.isfinite(time_s) & np.isfinite(current_a)
    above = current_a >= threshold_a
    cross_mask = (above[1:] != above[:-1]) & valid[1:] & valid[:-1]
    if not np.any(cross_mask):
        return np.empty(0, dtype=np.float64), np.empty(0, dtype=bool)

    cross_indices = np.flatnonzero(cross_mask) + 1
    prev_indices = cross_indices - 1
    prev_current = current_a[prev_indices]
    curr_current = current_a[cross_indices]
    prev_time = time_s[prev_indices]
    curr_time = time_s[cross_indices]
    delta = curr_current - prev_current
    fraction = np.zeros_like(delta, dtype=np.float64)
    nonzero = delta != 0.0
    fraction[nonzero] = (threshold_a - prev_current[nonzero]) / delta[nonzero]
    fraction = np.clip(fraction, 0.0, 1.0)
    crossing_times = prev_time + fraction * (curr_time - prev_time)
    rising = above[cross_indices]
    return crossing_times, rising


def _collapse_crossing_arrays(
    crossing_times: np.ndarray,
    rising: np.ndarray,
    *,
    min_gap_s: float = WELD_GRENZEN_CLUSTER_S,
) -> tuple[np.ndarray, np.ndarray]:
    if crossing_times.size == 0:
        return crossing_times, rising

    order = np.argsort(crossing_times, kind="mergesort")
    crossing_times = crossing_times[order]
    rising = rising[order]

    keep_indices = [0]
    for index in range(1, crossing_times.size):
        if crossing_times[index] - crossing_times[keep_indices[-1]] >= min_gap_s:
            keep_indices.append(index)

    keep = np.asarray(keep_indices, dtype=np.int64)
    return crossing_times[keep], rising[keep]


def _crossing_arrays_to_boundaries(
    crossing_times: np.ndarray,
    rising: np.ndarray,
    *,
    level: str,
) -> list[dict]:
    if crossing_times.size == 0:
        return []

    return [
        {
            "time_s": round(float(time_value), 6),
            "level": level,
            "direction": "rising" if bool(is_rising) else "falling",
        }
        for time_value, is_rising in zip(crossing_times, rising)
    ]


def _detect_current_threshold_crossings(
    time_s: np.ndarray,
    current_a: np.ndarray,
    threshold_a: float,
    *,
    level: str,
) -> list[dict]:
    crossing_times, rising = _detect_current_threshold_crossing_arrays(
        time_s,
        current_a,
        threshold_a,
    )
    return _crossing_arrays_to_boundaries(crossing_times, rising, level=level)


def _collapse_grenzen_boundaries(
    boundaries: list[dict],
    *,
    min_gap_s: float = WELD_GRENZEN_CLUSTER_S,
) -> list[dict]:
    """Keep the first boundary when several fall within min_gap_s."""
    if not boundaries:
        return []

    crossing_times = np.asarray(
        [float(item["time_s"]) for item in boundaries],
        dtype=np.float64,
    )
    rising = np.asarray(
        [item.get("direction") == "rising" for item in boundaries],
        dtype=bool,
    )
    level = str(boundaries[0].get("level", ""))
    collapsed_times, collapsed_rising = _collapse_crossing_arrays(
        crossing_times,
        rising,
        min_gap_s=min_gap_s,
    )
    return _crossing_arrays_to_boundaries(
        collapsed_times,
        collapsed_rising,
        level=level,
    )


def _merge_collapsed_boundary_lists(boundary_lists: list[list[dict]]) -> list[dict]:
    merged: list[dict] = []
    for boundaries in boundary_lists:
        if boundaries:
            merged.extend(boundaries)
    if not merged:
        return []

    merged.sort(key=lambda item: float(item["time_s"]))
    return _collapse_grenzen_boundaries(merged)


def _classify_weld_region(first_a: float, last_a: float, mid_a: float) -> str:
    first_below = first_a < mid_a
    last_below = last_a < mid_a
    if first_below and last_below:
        return "low"
    if first_below and not last_below:
        return "rise"
    if not first_below and not last_below:
        return "high"
    return "fall"


def _merge_adjacent_weld_regions(regions: list[dict]) -> list[dict]:
    if not regions:
        return []

    merged = [dict(regions[0])]
    for region in regions[1:]:
        if region.get("category") == merged[-1].get("category"):
            merged[-1]["end_s"] = region["end_s"]
            continue
        merged.append(dict(region))
    return merged


def _build_weld_regions_from_boundaries(
    time_s: np.ndarray,
    current_a: np.ndarray,
    boundaries: list[dict],
    mid_a: float,
) -> list[dict]:
    time_s = np.asarray(time_s, dtype=np.float64)
    current_a = np.asarray(current_a, dtype=np.float64)
    count = min(time_s.size, current_a.size)
    if count < 1 or not np.isfinite(mid_a):
        return []

    time_s = time_s[:count]
    current_a = current_a[:count]
    finite_mask = np.isfinite(time_s) & np.isfinite(current_a)
    if not np.any(finite_mask):
        return []

    valid_times = time_s[finite_mask]
    valid_current = current_a[finite_mask]
    first_time = float(valid_times[0])
    last_time = float(valid_times[-1])
    split_times = np.asarray(
        [first_time, *(float(item["time_s"]) for item in boundaries), last_time],
        dtype=np.float64,
    )

    regions: list[dict] = []
    for index in range(split_times.size - 1):
        seg_start = float(split_times[index])
        seg_end = float(split_times[index + 1])
        if seg_end <= seg_start:
            continue

        left = int(np.searchsorted(valid_times, seg_start, side="left"))
        right = int(np.searchsorted(valid_times, seg_end, side="right"))
        if right <= left:
            continue

        first_a = float(valid_current[left])
        last_a = float(valid_current[right - 1])
        if not np.isfinite(first_a) or not np.isfinite(last_a):
            continue

        regions.append(
            {
                "start_s": round(seg_start, 6),
                "end_s": round(seg_end, 6),
                "category": _classify_weld_region(first_a, last_a, float(mid_a)),
            }
        )

    return _merge_adjacent_weld_regions(regions)


def _fit_horizontal_line(time_s: np.ndarray, current_a: np.ndarray) -> dict | None:
    if time_s.size == 0:
        return None
    intercept = float(np.mean(current_a))
    if not np.isfinite(intercept):
        return None
    return {
        "intercept_a": round(intercept, 6),
        "slope_a_per_s": 0.0,
    }


def _fit_linear_line(time_s: np.ndarray, current_a: np.ndarray) -> dict | None:
    if time_s.size == 0:
        return None
    if time_s.size == 1:
        intercept = float(current_a[0])
        if not np.isfinite(intercept):
            return None
        return {
            "intercept_a": round(intercept, 6),
            "slope_a_per_s": 0.0,
        }

    time_mean = float(np.mean(time_s))
    current_mean = float(np.mean(current_a))
    time_centered = time_s - time_mean
    denominator = float(np.dot(time_centered, time_centered))
    if denominator == 0.0:
        intercept = current_mean
        slope = 0.0
    else:
        slope = float(np.dot(time_centered, current_a - current_mean) / denominator)
        intercept = current_mean - slope * time_mean
    if not np.isfinite(slope) or not np.isfinite(intercept):
        return None
    return {
        "intercept_a": round(intercept, 6),
        "slope_a_per_s": round(slope, 6),
    }


def _best_upward_opening_quadratic_fit(
    time_s: np.ndarray,
    current_a: np.ndarray,
) -> dict | None:
    """Best y = a*t^2 + b*t + c with strictly positive a (upward opening)."""
    time_s = np.asarray(time_s, dtype=np.float64)
    current_a = np.asarray(current_a, dtype=np.float64)
    count = time_s.size
    if count < 2:
        return None

    time_span = float(np.ptp(time_s))
    current_span = float(np.ptp(current_a))
    if time_span <= 0.0:
        return None

    time2 = time_s * time_s
    design = np.column_stack([time_s, np.ones(count, dtype=np.float64)])
    scale_a = max(current_span / (time_span * time_span), 1.0)
    candidates = scale_a * np.logspace(-8.0, 8.0, 96)

    best_a = None
    best_b = None
    best_c = None
    best_rss = np.inf
    for quad_a in candidates:
        if quad_a <= WELD_FALL_MIN_QUAD_A_PER_S2:
            continue
        adjusted = current_a - quad_a * time2
        coeffs, _, _, _ = np.linalg.lstsq(design, adjusted, rcond=None)
        residual = adjusted - design @ coeffs
        rss = float(np.dot(residual, residual))
        if rss < best_rss:
            best_rss = rss
            best_a = float(quad_a)
            best_b = float(coeffs[0])
            best_c = float(coeffs[1])

    if best_a is None or best_a <= WELD_FALL_MIN_QUAD_A_PER_S2:
        return None

    return {
        "intercept_a": round(best_c, 6),
        "slope_a_per_s": round(best_b, 6),
        "quad_a_per_s2": round(best_a, 6),
    }


def _fit_upward_opening_quadratic_line(
    time_s: np.ndarray,
    current_a: np.ndarray,
) -> dict | None:
    """Fall fit: upward-opening parabola only (quad_a_per_s2 > 0), else linear."""
    if time_s.size == 0:
        return None
    if time_s.size < 3:
        linear = _fit_linear_line(time_s, current_a)
        if linear is None:
            return None
        linear["quad_a_per_s2"] = 0.0
        return linear

    quad_a, slope, intercept = np.polyfit(time_s, current_a, 2)
    if (
        np.isfinite(quad_a)
        and np.isfinite(slope)
        and np.isfinite(intercept)
        and float(quad_a) > WELD_FALL_MIN_QUAD_A_PER_S2
    ):
        return {
            "intercept_a": round(float(intercept), 6),
            "slope_a_per_s": round(float(slope), 6),
            "quad_a_per_s2": round(float(quad_a), 6),
        }

    upward = _best_upward_opening_quadratic_fit(time_s, current_a)
    if upward is not None:
        return upward

    linear = _fit_linear_line(time_s, current_a)
    if linear is None:
        return None
    linear["quad_a_per_s2"] = 0.0
    return linear


def _add_weld_region_fits(
    regions: list[dict],
    time_s: np.ndarray,
    current_a: np.ndarray,
) -> list[dict]:
    time_s = np.asarray(time_s, dtype=np.float64)
    current_a = np.asarray(current_a, dtype=np.float64)
    count = min(time_s.size, current_a.size)
    if count < 1:
        return regions

    time_s = time_s[:count]
    current_a = current_a[:count]
    finite_mask = np.isfinite(time_s) & np.isfinite(current_a)
    valid_times = time_s[finite_mask]
    valid_current = current_a[finite_mask]
    if valid_times.size == 0:
        return regions

    fitted: list[dict] = []
    for region in regions:
        region = dict(region)
        category = str(region.get("category", ""))
        start_s = float(region["start_s"])
        end_s = float(region["end_s"])
        span = end_s - start_s
        if span <= 0:
            fitted.append(region)
            continue

        if category in ("low", "high"):
            fit_start = start_s + 0.25 * span
            fit_end = start_s + 0.75 * span
            fit_fn = _fit_horizontal_line
        elif category == "fall":
            fit_start = start_s
            fit_end = end_s
            fit_fn = _fit_upward_opening_quadratic_line
        else:
            fit_start = start_s
            fit_end = end_s
            fit_fn = _fit_linear_line

        left = int(np.searchsorted(valid_times, fit_start, side="left"))
        right = int(np.searchsorted(valid_times, fit_end, side="right"))
        fit = fit_fn(valid_times[left:right], valid_current[left:right])
        if fit is not None:
            region["fit"] = fit
        fitted.append(region)
    return fitted


def _horizontal_fit_level(region: dict) -> float | None:
    fit = region.get("fit")
    if not isinstance(fit, dict):
        return None
    intercept = _json_safe_characteristic_value(fit.get("intercept_a"))
    if intercept is None:
        return None
    return float(intercept)


def _horizontal_fit_intersection_times(
    intercept: float,
    slope: float,
    horizontal_a: float,
    *,
    quad_a_per_s2: float = 0.0,
) -> list[float]:
    if abs(quad_a_per_s2) < 1e-12:
        if abs(slope) < 1e-12:
            return []
        crossing_time = (horizontal_a - intercept) / slope
        if not np.isfinite(crossing_time):
            return []
        return [float(crossing_time)]

    offset = intercept - horizontal_a
    discriminant = slope * slope - 4.0 * quad_a_per_s2 * offset
    if discriminant < 0:
        return []

    sqrt_disc = float(np.sqrt(discriminant))
    denom = 2.0 * quad_a_per_s2
    return [
        (-slope + sqrt_disc) / denom,
        (-slope - sqrt_disc) / denom,
    ]


def _select_intersection_time(
    candidates: list[float],
    *,
    upper_bound: float | None = None,
    lower_bound: float | None = None,
    reference: float | None = None,
) -> float | None:
    valid = [float(value) for value in candidates if np.isfinite(value)]
    if upper_bound is not None:
        valid = [value for value in valid if value < upper_bound]
    if lower_bound is not None:
        valid = [value for value in valid if value > lower_bound]
    if not valid:
        return None
    if reference is not None:
        return min(valid, key=lambda value: abs(value - reference))
    return valid[0]


def _find_horizontal_neighbor(
    regions: list[dict],
    index: int,
    direction: int,
) -> tuple[int, float] | None:
    probe = index + direction
    while 0 <= probe < len(regions):
        category = str(regions[probe].get("category", ""))
        if category in ("low", "high"):
            level = _horizontal_fit_level(regions[probe])
            if level is not None:
                return probe, level
        probe += direction
    return None


def _adjust_regions_with_rise_fall_intersections(regions: list[dict]) -> list[dict]:
    """Extend rise/fall fits to low/high horizontals and use crossings as boundaries."""
    if not regions:
        return []

    adjusted = [dict(region) for region in regions]
    for index, region in enumerate(adjusted):
        category = str(region.get("category", ""))
        if category not in ("rise", "fall"):
            continue

        fit = region.get("fit")
        if not isinstance(fit, dict):
            continue

        slope = _json_safe_characteristic_value(fit.get("slope_a_per_s"))
        intercept = _json_safe_characteristic_value(fit.get("intercept_a"))
        quad = _json_safe_characteristic_value(fit.get("quad_a_per_s2")) or 0.0
        if slope is None or intercept is None:
            continue
        if abs(float(slope)) < 1e-12 and abs(float(quad)) < 1e-12:
            continue

        slope = float(slope)
        intercept = float(intercept)
        quad = max(float(quad), 0.0)
        original_start = float(region["start_s"])
        original_end = float(region["end_s"])
        new_start = original_start
        new_end = original_end

        left_neighbor = _find_horizontal_neighbor(adjusted, index, -1)
        if left_neighbor is not None:
            left_index, left_level = left_neighbor
            left_time = _select_intersection_time(
                _horizontal_fit_intersection_times(
                    intercept,
                    slope,
                    left_level,
                    quad_a_per_s2=quad,
                ),
                upper_bound=original_end,
                reference=original_start,
            )
            if left_time is not None:
                new_start = left_time
                adjusted[left_index]["end_s"] = round(left_time, 6)

        right_neighbor = _find_horizontal_neighbor(adjusted, index, 1)
        if right_neighbor is not None:
            right_index, right_level = right_neighbor
            right_time = _select_intersection_time(
                _horizontal_fit_intersection_times(
                    intercept,
                    slope,
                    right_level,
                    quad_a_per_s2=quad,
                ),
                lower_bound=original_start,
                reference=original_end,
            )
            if right_time is not None:
                new_end = right_time
                adjusted[right_index]["start_s"] = round(right_time, 6)

        if new_end <= new_start:
            continue

        adjusted[index]["start_s"] = round(new_start, 6)
        adjusted[index]["end_s"] = round(new_end, 6)

    normalized = [
        region
        for region in adjusted
        if float(region["end_s"]) - float(region["start_s"]) > 1e-9
    ]
    return _merge_adjacent_weld_regions(normalized)


def _build_weld_grenzen_regions(
    time_s: np.ndarray,
    channels: list[tuple[str, np.ndarray, str, str]],
    current_row: dict | None,
) -> list[dict] | None:
    """Detect weld cycle regions (low/rise/high/fall) from current threshold crossings."""
    if not isinstance(current_row, dict):
        return None

    try:
        _key, current_a, _label, units = _find_current_channel(channels)
    except ValueError:
        return None

    stats = _apply_weld_mid_percentiles(dict(current_row))
    collapsed_boundary_lists: list[list[dict]] = []

    time_arr = np.asarray(time_s, dtype=np.float64)
    current_arr = np.asarray(current_a, dtype=np.float64)

    for level in WELD_GRENZEN_LEVELS:
        threshold = _json_safe_characteristic_value(stats.get(level))
        if threshold is None:
            continue
        crossing_times, rising = _detect_current_threshold_crossing_arrays(
            time_arr,
            current_arr,
            float(threshold),
        )
        collapsed_times, collapsed_rising = _collapse_crossing_arrays(crossing_times, rising)
        collapsed_boundary_lists.append(
            _crossing_arrays_to_boundaries(collapsed_times, collapsed_rising, level=level)
        )

    boundaries = _merge_collapsed_boundary_lists(collapsed_boundary_lists)
    mid_threshold = _json_safe_characteristic_value(stats.get("current_p02_p98_mid"))
    if mid_threshold is None:
        return None

    regions = _build_weld_regions_from_boundaries(
        time_arr,
        current_arr,
        boundaries,
        float(mid_threshold),
    )
    regions = _add_weld_region_fits(regions, time_arr, current_arr)
    regions = _adjust_regions_with_rise_fall_intersections(regions)
    if not regions:
        return None

    return regions


def build_weld_grenzen_document(
    time_s: np.ndarray,
    channels: list[tuple[str, np.ndarray, str, str]],
    current_row: dict | None,
) -> dict | None:
    """Detect boundaries where current crosses the 1/5 and 4/5 P2–P98 levels."""
    regions = _build_weld_grenzen_regions(time_s, channels, current_row)
    if not regions:
        return None

    try:
        _key, _current_a, _label, units = _find_current_channel(channels)
    except ValueError:
        return None

    stats = _apply_weld_mid_percentiles(dict(current_row or {}))
    return _serialize_grenzen_document(
        quantity="Current",
        unit=str(stats.get("unit") or units or "A"),
        regions=regions,
    )


def _serialize_grenzen_document(
    *,
    quantity: str,
    unit: str,
    regions: list[dict],
) -> dict:
    serialized_regions: list[dict] = []
    for region in regions:
        if not isinstance(region, dict):
            continue
        fit = region.get("fit")
        if not isinstance(fit, dict):
            continue
        intercept = _json_safe_characteristic_value(fit.get("intercept_a"))
        slope = _json_safe_characteristic_value(fit.get("slope_a_per_s"))
        if intercept is None or slope is None:
            continue
        fit_payload = {
            "intercept_a": intercept,
            "slope_a_per_s": slope,
        }
        if str(region.get("category", "")) == "fall":
            quad = _json_safe_characteristic_value(fit.get("quad_a_per_s2"))
            if quad is None or float(quad) < 0.0:
                continue
            fit_payload["quad_a_per_s2"] = quad
        serialized_regions.append(
            {
                "start_s": region["start_s"],
                "end_s": region["end_s"],
                "category": region["category"],
                "fit": fit_payload,
            }
        )

    return {
        "version": 6,
        "quantity": quantity,
        "unit": unit,
        "regions": serialized_regions,
    }


def _region_time_slice(
    time_s: np.ndarray,
    values: np.ndarray,
    start_s: float,
    end_s: float,
) -> tuple[np.ndarray, np.ndarray]:
    time_s = np.asarray(time_s, dtype=np.float64)
    values = np.asarray(values, dtype=np.float64)
    count = min(time_s.size, values.size)
    if count < 1:
        return np.array([]), np.array([])

    time_s = time_s[:count]
    values = values[:count]
    finite = np.isfinite(time_s) & np.isfinite(values)
    time_s = time_s[finite]
    values = values[finite]
    if time_s.size == 0:
        return np.array([]), np.array([])

    left = int(np.searchsorted(time_s, start_s, side="left"))
    right = int(np.searchsorted(time_s, end_s, side="right"))
    return time_s[left:right], values[left:right]


def _mean_finite(values: np.ndarray) -> float | None:
    valid = np.asarray(values, dtype=np.float64)
    valid = valid[np.isfinite(valid)]
    if valid.size == 0:
        return None
    return float(np.mean(valid))


def _std_finite(values: np.ndarray) -> float | None:
    valid = np.asarray(values, dtype=np.float64)
    valid = valid[np.isfinite(valid)]
    if valid.size == 0:
        return None
    return float(np.std(valid))


def _max_finite(values: np.ndarray) -> float | None:
    valid = np.asarray(values, dtype=np.float64)
    valid = valid[np.isfinite(valid)]
    if valid.size == 0:
        return None
    return float(np.max(valid))


def _min_finite(values: np.ndarray) -> float | None:
    valid = np.asarray(values, dtype=np.float64)
    valid = valid[np.isfinite(valid)]
    if valid.size == 0:
        return None
    return float(np.min(valid))


def _range_finite(values: np.ndarray) -> float | None:
    max_value = _max_finite(values)
    min_value = _min_finite(values)
    if max_value is None or min_value is None:
        return None
    return float(max_value - min_value)


def _skewness_finite(values: np.ndarray) -> float | None:
    valid = np.asarray(values, dtype=np.float64)
    valid = valid[np.isfinite(valid)]
    if valid.size < 3:
        return None
    mean = float(np.mean(valid))
    std = float(np.std(valid))
    if std < 1e-12:
        return None
    centered = (valid - mean) / std
    return float(np.mean(centered ** 3))


def _kurtosis_finite(values: np.ndarray) -> float | None:
    valid = np.asarray(values, dtype=np.float64)
    valid = valid[np.isfinite(valid)]
    if valid.size < 4:
        return None
    mean = float(np.mean(valid))
    std = float(np.std(valid))
    if std < 1e-12:
        return None
    centered = (valid - mean) / std
    # Excess kurtosis (normal distribution = 0).
    return float(np.mean(centered ** 4) - 3.0)


def _trapezoid_integral(time_s: np.ndarray, values: np.ndarray) -> float | None:
    time_arr = np.asarray(time_s, dtype=np.float64)
    value_arr = np.asarray(values, dtype=np.float64)
    count = min(time_arr.size, value_arr.size)
    if count < 2:
        return None
    time_arr = time_arr[:count]
    value_arr = value_arr[:count]
    finite = np.isfinite(time_arr) & np.isfinite(value_arr)
    time_arr = time_arr[finite]
    value_arr = value_arr[finite]
    if time_arr.size < 2:
        return None
    integrate = getattr(np, "trapezoid", None) or np.trapz
    return float(integrate(value_arr, time_arr))


def _compute_pulse_integrals(
    time_s: np.ndarray,
    current_a: np.ndarray,
    voltage_v: np.ndarray,
    start_s: float,
    end_s: float,
) -> dict[str, float]:
    region_time, region_current = _region_time_slice(time_s, current_a, start_s, end_s)
    _region_time_v, region_voltage = _region_time_slice(time_s, voltage_v, start_s, end_s)
    region_power = region_current * region_voltage
    payload: dict[str, float] = {}
    current_integral = _trapezoid_integral(region_time, region_current)
    if current_integral is not None:
        payload[CURRENT_PULSE_INTEGRAL_FIELD] = round(current_integral, 6)
    voltage_integral = _trapezoid_integral(region_time, region_voltage)
    if voltage_integral is not None:
        payload[VOLTAGE_PULSE_INTEGRAL_FIELD] = round(voltage_integral, 6)
    power_integral = _trapezoid_integral(region_time, region_power)
    if power_integral is not None:
        payload[POWER_PULSE_INTEGRAL_FIELD] = round(power_integral, 6)
    return payload


def _linear_slope_per_s(time_s: np.ndarray, values: np.ndarray) -> float | None:
    fit = _fit_linear_line(time_s, values)
    if fit is None:
        return None
    return float(fit["slope_a_per_s"])


def _evaluate_weld_fit(fit: dict, time_s: float) -> float | None:
    if not isinstance(fit, dict):
        return None
    intercept = _json_safe_characteristic_value(fit.get("intercept_a"))
    if intercept is None:
        return None
    slope = _json_safe_characteristic_value(fit.get("slope_a_per_s")) or 0.0
    quad = _json_safe_characteristic_value(fit.get("quad_a_per_s2")) or 0.0
    value = float(intercept) + float(slope) * float(time_s) + float(quad) * float(time_s) ** 2
    if not np.isfinite(value):
        return None
    return value


def _fit_threshold_crossings_in_interval(
    fit: dict,
    threshold: float,
    start_s: float,
    end_s: float,
) -> list[float]:
    if end_s <= start_s:
        return []

    intercept = _json_safe_characteristic_value(fit.get("intercept_a"))
    if intercept is None:
        return []
    slope = float(_json_safe_characteristic_value(fit.get("slope_a_per_s")) or 0.0)
    quad = float(_json_safe_characteristic_value(fit.get("quad_a_per_s2")) or 0.0)

    if abs(quad) < 1e-12:
        if abs(slope) < 1e-12:
            return []
        crossing = (float(threshold) - float(intercept)) / slope
        if start_s < crossing < end_s:
            return [float(crossing)]
        return []

    offset = float(intercept) - float(threshold)
    discriminant = slope * slope - 4.0 * quad * offset
    if discriminant < 0.0:
        return []
    sqrt_disc = float(np.sqrt(discriminant))
    denom = 2.0 * quad
    crossings = [
        (-slope + sqrt_disc) / denom,
        (-slope - sqrt_disc) / denom,
    ]
    return sorted(
        float(crossing)
        for crossing in crossings
        if start_s < float(crossing) < end_s and np.isfinite(crossing)
    )


def _on_off_duration_for_fit_segment(
    fit: dict,
    threshold: float,
    start_s: float,
    end_s: float,
) -> tuple[float, float]:
    if end_s <= start_s:
        return 0.0, 0.0

    crossings = _fit_threshold_crossings_in_interval(fit, threshold, start_s, end_s)
    boundaries = [float(start_s), *crossings, float(end_s)]
    on_duration = 0.0
    off_duration = 0.0
    for left, right in zip(boundaries[:-1], boundaries[1:]):
        if right <= left:
            continue
        midpoint = (left + right) / 2.0
        value = _evaluate_weld_fit(fit, midpoint)
        if value is None:
            continue
        segment_duration = right - left
        if value > threshold:
            on_duration += segment_duration
        else:
            off_duration += segment_duration
    return on_duration, off_duration


def _compute_cycle_on_off_durations(
    region_map: dict[str, dict],
    mid_threshold: float,
) -> tuple[float, float]:
    on_duration = 0.0
    off_duration = 0.0
    for category in WELD_CYCLE_CATEGORIES:
        region = region_map.get(category)
        if not isinstance(region, dict):
            continue
        fit = region.get("fit")
        if not isinstance(fit, dict):
            continue
        start_s = float(region["start_s"])
        end_s = float(region["end_s"])
        on_segment, off_segment = _on_off_duration_for_fit_segment(
            fit,
            mid_threshold,
            start_s,
            end_s,
        )
        on_duration += on_segment
        off_duration += off_segment
    return on_duration, off_duration


def _metrics_for_weld_region(
    category: str,
    start_s: float,
    end_s: float,
    time_s: np.ndarray,
    current_a: np.ndarray,
    voltage_v: np.ndarray,
) -> dict | None:
    duration_s = float(end_s) - float(start_s)
    if duration_s <= 0:
        return None

    region_time, region_current = _region_time_slice(time_s, current_a, start_s, end_s)
    _region_time_v, region_voltage = _region_time_slice(time_s, voltage_v, start_s, end_s)
    if region_time.size == 0:
        return {"duration_s": round(duration_s, 6)}

    payload: dict = {"duration_s": round(duration_s, 6)}
    if category in ("low", "high"):
        mean_current = _mean_finite(region_current)
        if mean_current is not None:
            payload[CURRENT_A_FIELD] = round(mean_current, 6)
        std_current = _std_finite(region_current)
        if std_current is not None:
            payload[CURRENT_STD_A_FIELD] = round(std_current, 6)
        max_current = _max_finite(region_current)
        if max_current is not None:
            payload[CURRENT_MAX_A_FIELD] = round(max_current, 6)
        min_current = _min_finite(region_current)
        if min_current is not None:
            payload[CURRENT_MIN_A_FIELD] = round(min_current, 6)
        range_current = _range_finite(region_current)
        if range_current is not None:
            payload[CURRENT_RANGE_A_FIELD] = round(range_current, 6)
        skew_current = _skewness_finite(region_current)
        if skew_current is not None:
            payload[CURRENT_SKEWNESS_A_FIELD] = round(skew_current, 6)
        kurtosis_current = _kurtosis_finite(region_current)
        if kurtosis_current is not None:
            payload[CURRENT_KURTOSIS_A_FIELD] = round(kurtosis_current, 6)
        mean_voltage = _mean_finite(region_voltage)
        if mean_voltage is not None:
            payload[VOLTAGE_V_FIELD] = round(mean_voltage, 6)
        std_voltage = _std_finite(region_voltage)
        if std_voltage is not None:
            payload[VOLTAGE_STD_V_FIELD] = round(std_voltage, 6)
        max_voltage = _max_finite(region_voltage)
        if max_voltage is not None:
            payload[VOLTAGE_MAX_V_FIELD] = round(max_voltage, 6)
        min_voltage = _min_finite(region_voltage)
        if min_voltage is not None:
            payload[VOLTAGE_MIN_V_FIELD] = round(min_voltage, 6)
        range_voltage = _range_finite(region_voltage)
        if range_voltage is not None:
            payload[VOLTAGE_RANGE_V_FIELD] = round(range_voltage, 6)
        skew_voltage = _skewness_finite(region_voltage)
        if skew_voltage is not None:
            payload[VOLTAGE_SKEWNESS_V_FIELD] = round(skew_voltage, 6)
        kurtosis_voltage = _kurtosis_finite(region_voltage)
        if kurtosis_voltage is not None:
            payload[VOLTAGE_KURTOSIS_V_FIELD] = round(kurtosis_voltage, 6)
        region_power = region_current * region_voltage
        mean_power = _mean_finite(region_power)
        if mean_power is not None:
            payload[POWER_W_FIELD] = round(mean_power, 6)
        std_power = _std_finite(region_power)
        if std_power is not None:
            payload[POWER_STD_W_FIELD] = round(std_power, 6)
        max_power = _max_finite(region_power)
        if max_power is not None:
            payload[POWER_MAX_W_FIELD] = round(max_power, 6)
        min_power = _min_finite(region_power)
        if min_power is not None:
            payload[POWER_MIN_W_FIELD] = round(min_power, 6)
        range_power = _range_finite(region_power)
        if range_power is not None:
            payload[POWER_RANGE_W_FIELD] = round(range_power, 6)
        skew_power = _skewness_finite(region_power)
        if skew_power is not None:
            payload[POWER_SKEWNESS_W_FIELD] = round(skew_power, 6)
        kurtosis_power = _kurtosis_finite(region_power)
        if kurtosis_power is not None:
            payload[POWER_KURTOSIS_W_FIELD] = round(kurtosis_power, 6)
    elif category in ("rise", "fall"):
        slope_current = _linear_slope_per_s(region_time, region_current)
        if slope_current is not None:
            payload[CURRENT_SLOPE_A_PER_S_FIELD] = round(slope_current, 6)
        slope_voltage = _linear_slope_per_s(region_time, region_voltage)
        if slope_voltage is not None:
            payload[VOLTAGE_SLOPE_V_PER_S_FIELD] = round(slope_voltage, 6)
        region_power = region_current * region_voltage
        slope_power = _linear_slope_per_s(region_time, region_power)
        if slope_power is not None:
            payload[POWER_SLOPE_W_PER_S_FIELD] = round(slope_power, 6)
    return payload


def _group_regions_into_cycles(regions: list[dict]) -> list[dict[str, dict]]:
    ordered = sorted(
        (
            region
            for region in regions
            if isinstance(region, dict)
            and str(region.get("category", "")) in WELD_CYCLE_CATEGORIES
        ),
        key=lambda region: float(region["start_s"]),
    )
    cycles: list[dict[str, dict]] = []
    current: dict[str, dict] = {}
    for region in ordered:
        category = str(region["category"])
        if category == "low" and current:
            cycles.append(current)
            current = {}
        current[category] = region
    if current:
        cycles.append(current)
    return cycles


def _serialize_char_graphen_cycle(
    index: int,
    region_map: dict[str, dict],
    time_s: np.ndarray,
    current_a: np.ndarray,
    voltage_v: np.ndarray,
    *,
    mid_threshold: float | None = None,
) -> dict | None:
    regions_out: dict[str, dict] = {}
    cycle_start: float | None = None
    cycle_end: float | None = None

    for category in WELD_CYCLE_CATEGORIES:
        region = region_map.get(category)
        if region is None:
            continue
        start_s = float(region["start_s"])
        end_s = float(region["end_s"])
        metrics = _metrics_for_weld_region(
            category,
            start_s,
            end_s,
            time_s,
            current_a,
            voltage_v,
        )
        if metrics is None:
            continue
        regions_out[category] = metrics
        cycle_start = start_s if cycle_start is None else min(cycle_start, start_s)
        cycle_end = end_s if cycle_end is None else max(cycle_end, end_s)

    if not regions_out:
        return None

    payload: dict = {"index": index, "regions": regions_out}
    if cycle_start is not None and cycle_end is not None:
        payload["start_s"] = round(cycle_start, 6)
        payload["end_s"] = round(cycle_end, 6)
        pulse_duration = cycle_end - cycle_start
        if pulse_duration > 0 and mid_threshold is not None:
            on_duration, off_duration = _compute_cycle_on_off_durations(
                region_map,
                float(mid_threshold),
            )
            payload[ON_DURATION_FIELD] = round(on_duration, 6)
            payload[OFF_DURATION_FIELD] = round(off_duration, 6)
            payload[ON_DURATION_RATIO_FIELD] = round(on_duration / pulse_duration, 6)
        payload.update(
            _compute_pulse_integrals(
                time_s,
                current_a,
                voltage_v,
                cycle_start,
                cycle_end,
            ),
        )
    return payload


def build_weld_char_graphen_document(
    time_s: np.ndarray,
    channels: list[tuple[str, np.ndarray, str, str]],
    regions: list[dict],
    *,
    mid_threshold: float | None = None,
) -> dict | None:
    if not regions:
        return None

    try:
        _key_i, current_a, _label_i, _units_i = _find_current_channel(channels)
        _key_v, voltage_v, _label_v, _units_v = _find_voltage_channel(channels)
    except ValueError:
        return None

    cycles: list[dict] = []
    for index, region_map in enumerate(_group_regions_into_cycles(regions)):
        cycle_payload = _serialize_char_graphen_cycle(
            index,
            region_map,
            time_s,
            current_a,
            voltage_v,
            mid_threshold=mid_threshold,
        )
        if cycle_payload is not None:
            cycles.append(cycle_payload)

    if not cycles:
        return None
    return {"version": 2, "cycles": cycles}


def _graph_point_value(point: dict, graph_document: dict) -> float | None:
    metric_field = str(graph_document.get("metric_field", "")).strip()
    if not metric_field:
        return None
    return _json_safe_characteristic_value(point.get(metric_field))


def _graph_point_values(graph_document: dict) -> np.ndarray:
    values: list[float] = []
    for point in graph_document.get("points") or []:
        if not isinstance(point, dict):
            continue
        value = _graph_point_value(point, graph_document)
        if value is not None:
            values.append(value)
    return np.asarray(values, dtype=np.float64)


def _char_graphen_graph_items(char_graphen_document: dict) -> list[tuple[str, dict]]:
    graphs = char_graphen_document.get("graphs")
    if not isinstance(graphs, dict):
        return []
    return [
        (str(graph_key), graph_document)
        for graph_key, graph_document in graphs.items()
        if isinstance(graph_document, dict)
    ]


def build_char_graphen_characteristic_fields(char_graphen_document: dict) -> dict[str, float]:
    """Aggregate mean/std for every char_graphen graph into characteristics keys."""
    fields: dict[str, float] = {}
    for graph_key, graph_document in _char_graphen_graph_items(char_graphen_document):
        values = _graph_point_values(graph_document)
        if values.size == 0:
            continue
        fields[f"{graph_key}_mean"] = round(float(np.mean(values)), 6)
        fields[f"{graph_key}_standarddeviation"] = round(float(np.std(values)), 6)
    return fields


def _normalize_char_graphen_graph_keys(graphs: dict) -> dict[str, dict]:
    normalized: dict[str, dict] = {}
    for graph_key, graph_document in graphs.items():
        if not isinstance(graph_document, dict):
            continue
        graph_source = str(graph_document.get("graph", "")).strip()
        region = str(graph_document.get("region", "")).strip()
        analysis = str(graph_document.get("analysis", "")).strip()
        if graph_key == PULSE_DURATION_GRAPH_KEY or graph_source == "pulse":
            mapped_key = PULSE_DURATION_GRAPH_KEY
        elif graph_key == ON_DURATION_GRAPH_KEY or (
            graph_source == "on" and analysis == "duration"
        ):
            mapped_key = ON_DURATION_GRAPH_KEY
        elif graph_key == OFF_DURATION_GRAPH_KEY or (
            graph_source == "off" and analysis == "duration"
        ):
            mapped_key = OFF_DURATION_GRAPH_KEY
        elif graph_key == ON_DURATION_RATIO_GRAPH_KEY or (
            graph_source == "on" and analysis == "ratio"
        ):
            mapped_key = ON_DURATION_RATIO_GRAPH_KEY
        elif analysis == "integral":
            mapped_key = char_graphen_graph_key(graph_source, region, analysis)
        elif analysis == "duration":
            mapped_key = char_graphen_graph_key("", region, analysis)
        elif graph_source:
            mapped_key = char_graphen_graph_key(graph_source, region, analysis)
        else:
            mapped_key = str(graph_key)
        normalized[mapped_key] = graph_document
    return normalized


def build_weld_region_graph_document(
    char_graphen_document: dict,
    *,
    graph_source: str,
    region: str,
    analysis: str,
    metric_field: str,
) -> dict | None:
    cycles = char_graphen_document.get("cycles")
    if not isinstance(cycles, list):
        return None

    points: list[dict] = []
    for cycle in cycles:
        if not isinstance(cycle, dict):
            continue
        region_data = (cycle.get("regions") or {}).get(region)
        if not isinstance(region_data, dict):
            continue

        value = _json_safe_characteristic_value(region_data.get(metric_field))
        if value is None:
            continue

        point: dict = {"index": cycle.get("index"), metric_field: value}
        start_s = _json_safe_characteristic_value(cycle.get("start_s"))
        end_s = _json_safe_characteristic_value(cycle.get("end_s"))
        if start_s is not None:
            point["start_s"] = start_s
        if end_s is not None:
            point["end_s"] = end_s
        points.append(point)

    if not points:
        return None

    payload: dict = {
        "version": 2,
        "region": region,
        "analysis": analysis,
        "metric_field": metric_field,
        "points": points,
    }
    if graph_source:
        payload["graph"] = graph_source
    return payload


def _pulse_duration_from_cycle(cycle: dict) -> float | None:
    start_s = _json_safe_characteristic_value(cycle.get("start_s"))
    end_s = _json_safe_characteristic_value(cycle.get("end_s"))
    if start_s is None or end_s is None:
        return None
    duration_s = end_s - start_s
    if duration_s <= 0:
        return None
    return round(duration_s, 6)


def _cycle_metric_value(cycle: dict, metric_field: str) -> float | None:
    return _json_safe_characteristic_value(cycle.get(metric_field))


def _build_pulse_level_graph_document(
    char_graphen_document: dict,
    *,
    graph_source: str,
    analysis: str,
    metric_field: str,
    value_from_cycle,
) -> dict | None:
    cycles = char_graphen_document.get("cycles")
    if not isinstance(cycles, list):
        return None

    points: list[dict] = []
    for cycle in cycles:
        if not isinstance(cycle, dict):
            continue
        value = value_from_cycle(cycle)
        if value is None:
            continue
        point: dict = {"index": cycle.get("index"), metric_field: value}
        start_s = _json_safe_characteristic_value(cycle.get("start_s"))
        end_s = _json_safe_characteristic_value(cycle.get("end_s"))
        if start_s is not None:
            point["start_s"] = start_s
        if end_s is not None:
            point["end_s"] = end_s
        points.append(point)

    if not points:
        return None

    return {
        "version": 2,
        "graph": graph_source,
        "region": "",
        "analysis": analysis,
        "metric_field": metric_field,
        "points": points,
    }


def build_pulse_duration_graph_document(char_graphen_document: dict) -> dict | None:
    return _build_pulse_level_graph_document(
        char_graphen_document,
        graph_source="pulse",
        analysis="duration",
        metric_field="duration_s",
        value_from_cycle=_pulse_duration_from_cycle,
    )


def build_on_duration_graph_document(char_graphen_document: dict) -> dict | None:
    return _build_pulse_level_graph_document(
        char_graphen_document,
        graph_source="on",
        analysis="duration",
        metric_field=ON_DURATION_FIELD,
        value_from_cycle=lambda cycle: _cycle_metric_value(cycle, ON_DURATION_FIELD),
    )


def build_off_duration_graph_document(char_graphen_document: dict) -> dict | None:
    return _build_pulse_level_graph_document(
        char_graphen_document,
        graph_source="off",
        analysis="duration",
        metric_field=OFF_DURATION_FIELD,
        value_from_cycle=lambda cycle: _cycle_metric_value(cycle, OFF_DURATION_FIELD),
    )


def build_on_duration_ratio_graph_document(char_graphen_document: dict) -> dict | None:
    return _build_pulse_level_graph_document(
        char_graphen_document,
        graph_source="on",
        analysis="ratio",
        metric_field=ON_DURATION_RATIO_FIELD,
        value_from_cycle=lambda cycle: _cycle_metric_value(cycle, ON_DURATION_RATIO_FIELD),
    )


def build_weld_region_graph_documents(char_graphen_document: dict) -> dict[str, dict]:
    documents: dict[str, dict] = {}
    for graph_source, region, analysis, metric_field in CHAR_GRAPHEN_GRAPH_SPECS:
        document = build_weld_region_graph_document(
            char_graphen_document,
            graph_source=graph_source,
            region=region,
            analysis=analysis,
            metric_field=metric_field,
        )
        if document is not None:
            documents[char_graphen_graph_key(graph_source, region, analysis)] = document

    pulse_document = build_pulse_duration_graph_document(char_graphen_document)
    if pulse_document is not None:
        documents[PULSE_DURATION_GRAPH_KEY] = pulse_document

    on_duration_document = build_on_duration_graph_document(char_graphen_document)
    if on_duration_document is not None:
        documents[ON_DURATION_GRAPH_KEY] = on_duration_document

    off_duration_document = build_off_duration_graph_document(char_graphen_document)
    if off_duration_document is not None:
        documents[OFF_DURATION_GRAPH_KEY] = off_duration_document

    on_ratio_document = build_on_duration_ratio_graph_document(char_graphen_document)
    if on_ratio_document is not None:
        documents[ON_DURATION_RATIO_GRAPH_KEY] = on_ratio_document

    for graph_source, _region, analysis, metric_field in PULSE_INTEGRAL_GRAPH_SPECS:
        graph_key = char_graphen_graph_key(graph_source, "", analysis)
        integral_document = _build_pulse_level_graph_document(
            char_graphen_document,
            graph_source=graph_source,
            analysis=analysis,
            metric_field=metric_field,
            value_from_cycle=lambda cycle, field=metric_field: _cycle_metric_value(cycle, field),
        )
        if integral_document is not None:
            documents[graph_key] = integral_document

    return documents


def build_char_graphen_output_document(cycles_document: dict) -> dict | None:
    graphs = build_weld_region_graph_documents(cycles_document)
    if not graphs:
        return None
    return {"version": 3, "graphs": graphs}


def write_char_graphen_file(output_path: Path, document: dict) -> None:
    output_path.write_text(
        json.dumps(document, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def load_char_graphen(path: Path) -> dict:
    """Load char_graphen.json (v3 graphs)."""
    path = Path(path)
    char_path = path if path.is_file() else path / CHAR_GRAPHEN_FILENAME
    if not char_path.is_file():
        folder_path = path.parent if path.suffix else path
        raise FileNotFoundError(f"{CHAR_GRAPHEN_FILENAME} nicht gefunden in {folder_path}.")

    document = json.loads(char_path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("Ungültiges char_graphen-JSON.")
    graphs = document.get("graphs")
    if not isinstance(graphs, dict):
        raise ValueError("char_graphen-JSON erfordert version 3 mit graphs.")
    return {
        **document,
        "graphs": _normalize_char_graphen_graph_keys(graphs),
    }


def write_grenzen_file(output_path: Path, document: dict) -> None:
    output_path.write_text(
        json.dumps(document, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def load_grenzen(path: Path) -> dict:
    path = Path(path)
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("Ungültiges Grenzen-JSON.")
    return document


def write_characteristics_file(
    output_path: Path,
    *,
    scan_fields: dict | None = None,
    weld_rows: list[dict] | None = None,
) -> None:
    payload = {
        "version": 2,
        "scan": _serialize_scan_characteristics(scan_fields or {}),
        "weld": [_serialize_weld_characteristic_row(row) for row in (weld_rows or [])],
    }
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load_characteristics(path: Path) -> dict:
    """Load scan and weld characteristics from JSON."""
    path = Path(path)
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("Ungültiges Characteristics-JSON.")
    if "weld" not in document and "scan" not in document:
        raise ValueError("Ungültiges Characteristics-JSON: scan/weld fehlt.")

    scan_fields = _normalize_scan_characteristics(document.get("scan"))
    weld_rows: list[dict] = []
    for item in document.get("weld") or []:
        if not isinstance(item, dict):
            continue
        quantity = _normalize_weld_quantity(
            item.get("quantity", "") if "quantity" in item else "",
        )
        if quantity == WELD_CURRENT_QUANTITY:
            normalized = _normalize_weld_characteristic_row(item)
        elif quantity == WELD_VOLTAGE_QUANTITY:
            normalized = _normalize_weld_voltage_characteristic_row(item)
        elif quantity == WELD_POWER_QUANTITY:
            normalized = _normalize_weld_power_characteristic_row(item)
        else:
            normalized = _normalize_weld_duration_characteristic_row(item)
        if normalized is not None:
            weld_rows.append(normalized)
    return {"scan": scan_fields, "weld": weld_rows}


def load_weld_characteristics(path: Path) -> list[dict]:
    document = load_characteristics(path)
    return list(document.get("weld") or [])


def current_stats_from_weld_h5(h5_path: Path) -> dict | None:
    """Current statistics from a weld H5 file."""
    time_s, channels = _load_weld_h5_channels(h5_path)
    row = build_weld_current_characteristic_row(time_s, channels)
    if row is None:
        return None
    result = {"unit": row.get("unit") or "A"}
    for field in WELD_CURRENT_STAT_FIELDS:
        value = _json_safe_characteristic_value(row.get(field))
        if value is not None:
            result[field] = value
    if len(result) <= 1:
        return None
    return result


def combine_profile_curvatures(
    *,
    x_curvature: float | None,
    y_curvature: float | None,
    x_r2: float | None,
    y_r2: float | None,
) -> dict[str, float]:
    """
    Combine X/Y profile curvatures with R² weights:

    1) signed weighted mean
    2) R²-weighted RMS of absolute curvatures
    """
    values: dict[str, float] = {}
    terms: list[tuple[float, float]] = []

    for kappa, r2 in ((x_curvature, x_r2), (y_curvature, y_r2)):
        if kappa is None or r2 is None:
            continue
        kappa_f = float(kappa)
        r2_f = float(r2)
        if not np.isfinite(kappa_f) or not np.isfinite(r2_f):
            continue
        weight = max(r2_f, 0.0)
        if weight <= 0:
            continue
        terms.append((kappa_f, weight))

    if not terms:
        return values

    weight_sum = float(sum(weight for _kappa, weight in terms))
    if weight_sum <= 0:
        return values

    weighted_mean = float(sum(kappa * weight for kappa, weight in terms) / weight_sum)
    weighted_rms = float(
        np.sqrt(sum((abs(kappa) ** 2) * weight for kappa, weight in terms) / weight_sum)
    )
    values["total_curvature_mean"] = round(weighted_mean, 9)
    values["total_curvature_rms"] = round(weighted_rms, 9)
    return values


def build_curvature_characteristic_fields(
    *,
    x_curvature: float | None = None,
    y_curvature: float | None = None,
    total_curvature_mean: float | None = None,
    total_curvature_rms: float | None = None,
    surface_curvature: float | None = None,
) -> dict[str, float]:
    fields: dict[str, float] = {}
    if x_curvature is not None and np.isfinite(x_curvature):
        fields["X_curvature"] = float(x_curvature)
    if y_curvature is not None and np.isfinite(y_curvature):
        fields["Y_curvature"] = float(y_curvature)
    if total_curvature_mean is not None and np.isfinite(total_curvature_mean):
        fields["Total_curvature_mean"] = float(total_curvature_mean)
    if total_curvature_rms is not None and np.isfinite(total_curvature_rms):
        fields["Total_curvature_rms"] = float(total_curvature_rms)
    if surface_curvature is not None and np.isfinite(surface_curvature):
        fields["Surface_curvature"] = float(surface_curvature)
    return fields


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


def _fill_short_false_gaps(mask: np.ndarray, max_gap: int) -> np.ndarray:
    """Keep pulsed welding as one region by filling brief below-threshold dips."""
    if max_gap <= 0 or mask.size == 0:
        return mask.astype(bool, copy=True)

    filled = mask.astype(bool, copy=True)
    true_indices = np.flatnonzero(filled)
    if true_indices.size < 2:
        return filled

    for left, right in zip(true_indices[:-1], true_indices[1:]):
        if 0 < right - left - 1 <= max_gap:
            filled[left + 1 : right] = True
    return filled


def _longest_true_run(mask: np.ndarray) -> tuple[int, int] | None:
    if not np.any(mask):
        return None

    best_start = 0
    best_end = 0
    start = None
    for index, value in enumerate(mask):
        if value and start is None:
            start = index
        elif not value and start is not None:
            if index - start > best_end - best_start:
                best_start, best_end = start, index
            start = None

    if start is not None and mask.size - start > best_end - best_start:
        best_start, best_end = start, mask.size

    return best_start, best_end


def _refine_weld_edge_sample(
    current_a: np.ndarray,
    *,
    chunk_index: int,
    chunk_samples: int,
    threshold_a: float,
    rising: bool,
) -> int:
    """Locate the sample where current crosses threshold within an edge chunk."""
    start = max(0, chunk_index * chunk_samples)
    end = min(current_a.size, (chunk_index + 2) * chunk_samples)
    if end <= start:
        return start if rising else end

    window = current_a[start:end]
    if rising:
        above = np.flatnonzero(window > threshold_a)
        if above.size:
            return start + int(above[0])
        return start

    below = np.flatnonzero(window <= threshold_a)
    if below.size:
        return start + int(below[0])
    return end


def _find_edge_in_window(
    diffs: np.ndarray,
    *,
    window_start: int,
    window_end: int,
    rising: bool,
    edge_min_a: float,
) -> int | None:
    """Return chunk index of strongest rise/fall inside [window_start, window_end)."""
    lo = max(0, window_start)
    hi = min(diffs.size, window_end)
    if hi <= lo:
        return None

    segment = diffs[lo:hi]
    if rising:
        local = int(np.argmax(segment))
        if segment[local] < edge_min_a:
            return None
    else:
        local = int(np.argmin(segment))
        if segment[local] > -edge_min_a:
            return None
    return lo + local


def _compute_channel_chunk_means(values: np.ndarray, chunk_samples: int) -> list[float]:
    means: list[float] = []
    for start in range(0, values.size, chunk_samples):
        end = min(start + chunk_samples, values.size)
        means.append(float(np.mean(values[start:end])))
    return means


def _find_weld_arc_strike_chunk(
    current_means: np.ndarray,
    voltage_means: np.ndarray,
    *,
    idle_baseline_a: float,
    idle_baseline_v: float,
    edge_min_a: float,
    search_start: int,
    search_end: int,
) -> int | None:
    """Chunk index where current rises and voltage falls strongly at the same time."""
    if current_means.size < 2 or voltage_means.size < 2:
        return None

    count = min(current_means.size, voltage_means.size)
    i_diffs = np.diff(current_means[:count])
    v_diffs = np.diff(voltage_means[:count])
    if i_diffs.size == 0:
        return None

    v_span = max(idle_baseline_v - float(np.min(voltage_means[:count])), 1.0)
    edge_min_v = max(WELD_EDGE_AMPLITUDE_FRACTION * v_span, idle_baseline_v * 0.02)

    lo = max(0, search_start)
    hi = min(i_diffs.size, search_end)
    for chunk_index in range(lo, hi):
        if i_diffs[chunk_index] >= edge_min_a and v_diffs[chunk_index] <= -edge_min_v:
            return chunk_index

    return None


def _apply_weld_start_delay(sample_index: int, time_s: np.ndarray, *, config: WeldConfig) -> int:
    rate = _estimate_sample_rate(time_s, config)
    delay_samples = max(1, int(round(WELD_START_DELAY_S * rate)))
    return min(sample_index + delay_samples, max(time_s.size - 1, 0))


def _find_weld_transient_end_sample(
    current_a: np.ndarray,
    voltage_v: np.ndarray,
    time_s: np.ndarray,
    *,
    start_sample: int,
    config: WeldConfig,
    edge_min_a: float,
    edge_min_v: float,
) -> int:
    """End of the arc-strike transient (sharp I rise + V drop) after start_sample."""
    sample_count = min(current_a.size, voltage_v.size, time_s.size)
    if sample_count <= 0:
        return 0

    rate = _estimate_sample_rate(time_s[:sample_count], config)
    window = max(1, int(round(0.001 * rate)))  # 1 ms
    max_search = max(window, int(round(0.15 * rate)))  # up to 150 ms

    lo = max(0, start_sample)
    hi = min(sample_count - window, start_sample + max_search)
    last_active = lo

    step = max(1, window // 2)
    i_threshold = edge_min_a * 0.05
    v_threshold = edge_min_v * 0.05
    for index in range(lo, hi, step):
        i_window = current_a[index : index + window]
        v_window = voltage_v[index : index + window]
        if i_window.size < 2 or v_window.size < 2:
            break
        di = float(i_window[-1] - i_window[0])
        dv = float(v_window[-1] - v_window[0])
        if di >= i_threshold or dv <= -v_threshold:
            last_active = index + window

    return min(last_active, sample_count - 1)


def _find_weld_active_range(
    current_a: np.ndarray,
    time_s: np.ndarray,
    *,
    config: WeldConfig,
    voltage_v: np.ndarray | None = None,
) -> tuple[int, int, float, float]:
    """Crop weld by arc strike at start (V drop + I rise, then delay) and current fall at end."""
    chunk_samples, chunk_means_list = _compute_weld_chunk_means(current_a, time_s, config=config)
    means = np.asarray(chunk_means_list, dtype=float)

    if means.size < WELD_BASELINE_MIN_CHUNKS:
        raise ValueError(
            f"Nicht genug Idle-Messwerte für die Baseline "
            f"(mindestens {WELD_BASELINE_MIN_CHUNKS} Chunks erforderlich)."
        )

    idle_baseline_a = float(np.mean(means[:WELD_BASELINE_MIN_CHUNKS]))
    margin_a = config.threshold_v * config.current_scale
    threshold_a = idle_baseline_a + margin_a

    peak_a = float(np.max(means))
    amplitude_a = max(peak_a - idle_baseline_a, margin_a)
    if peak_a <= threshold_a:
        raise ValueError("Schweißphase konnte nicht erkannt werden (kein Stromanstieg).")

    # Keep short pulse dips inside one weld region (~0.5 s).
    gap_chunks = max(1, int(round(0.5 / WELD_CHUNK_FRACTION_S)))
    active_mask = _fill_short_false_gaps(means > threshold_a, gap_chunks)
    active_run = _longest_true_run(active_mask)
    if active_run is None:
        raise ValueError("Schweißphase konnte nicht erkannt werden.")

    run_start, run_end = active_run
    diffs = np.diff(means)
    if diffs.size == 0:
        raise ValueError("Schweißphase konnte nicht erkannt werden.")

    edge_min_a = max(WELD_EDGE_AMPLITUDE_FRACTION * amplitude_a, margin_a)
    # Search for rise just before/at envelope start, fall at/after envelope end.
    search_pad = max(2, gap_chunks)
    rise_edge = _find_edge_in_window(
        diffs,
        window_start=run_start - search_pad,
        window_end=min(run_start + search_pad, run_end),
        rising=True,
        edge_min_a=edge_min_a,
    )
    fall_edge = _find_edge_in_window(
        diffs,
        window_start=max(run_start, run_end - search_pad - 1),
        window_end=min(diffs.size, run_end + search_pad),
        rising=False,
        edge_min_a=edge_min_a,
    )

    if rise_edge is None:
        rise_edge = max(0, run_start - 1)
    if fall_edge is None:
        fall_edge = min(diffs.size - 1, max(run_end - 1, rise_edge))

    if fall_edge <= rise_edge:
        raise ValueError("Schweißphase konnte nicht erkannt werden (kein Stromabfall nach Anstieg).")

    strike_edge = rise_edge
    edge_min_v = None
    if voltage_v is not None and voltage_v.size > 0:
        sample_count = min(current_a.size, voltage_v.size, time_s.size)
        voltage_means = np.asarray(
            _compute_channel_chunk_means(voltage_v[:sample_count], chunk_samples),
            dtype=float,
        )
        idle_baseline_v = float(np.mean(voltage_means[:WELD_BASELINE_MIN_CHUNKS]))
        v_span = max(idle_baseline_v - float(np.min(voltage_means)), 1.0)
        edge_min_v = max(WELD_EDGE_AMPLITUDE_FRACTION * v_span, idle_baseline_v * 0.02)
        arc_strike_chunk = _find_weld_arc_strike_chunk(
            means,
            voltage_means,
            idle_baseline_a=idle_baseline_a,
            idle_baseline_v=idle_baseline_v,
            edge_min_a=edge_min_a,
            search_start=max(0, run_start - search_pad),
            search_end=min(run_end + search_pad, means.size),
        )
        if arc_strike_chunk is not None:
            strike_edge = arc_strike_chunk

    start_index = _refine_weld_edge_sample(
        current_a,
        chunk_index=strike_edge,
        chunk_samples=chunk_samples,
        threshold_a=threshold_a,
        rising=True,
    )
    if voltage_v is not None and voltage_v.size > 0 and edge_min_v is not None:
        sample_count = min(current_a.size, voltage_v.size, time_s.size)
        start_index = _find_weld_transient_end_sample(
            current_a[:sample_count],
            voltage_v[:sample_count],
            time_s[:sample_count],
            start_sample=start_index,
            config=config,
            edge_min_a=edge_min_a,
            edge_min_v=edge_min_v,
        )
    start_index = _apply_weld_start_delay(start_index, time_s, config=config)
    end_index = _refine_weld_edge_sample(
        current_a,
        chunk_index=fall_edge,
        chunk_samples=chunk_samples,
        threshold_a=threshold_a,
        rising=False,
    )

    if end_index <= start_index:
        raise ValueError("Keine Messdaten in der erkannten Schweißphase vorhanden.")

    return start_index, end_index, idle_baseline_a, threshold_a


def _crop_center_time_window(
    time_s: np.ndarray,
    start_index: int,
    end_index: int,
    *,
    duration_s: float = WELD_CROPPED_CENTER_DURATION_S,
) -> tuple[int, int]:
    """Narrow [start_index, end_index) to duration_s centered in the active weld span."""
    if end_index <= start_index or duration_s <= 0:
        return start_index, end_index

    active_time = np.asarray(time_s[start_index:end_index], dtype=np.float64)
    if active_time.size <= 0:
        return start_index, end_index

    span_s = float(active_time[-1] - active_time[0])
    if span_s <= duration_s:
        return start_index, end_index

    center_time = (float(active_time[0]) + float(active_time[-1])) / 2.0
    half = duration_s / 2.0
    window_start = center_time - half
    window_end = center_time + half

    new_start = int(np.searchsorted(time_s, window_start, side="left"))
    new_end = int(np.searchsorted(time_s, window_end, side="right"))
    new_start = max(start_index, new_start)
    new_end = min(end_index, new_end)
    if new_end <= new_start:
        return start_index, end_index
    return new_start, new_end


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
    _voltage_key, voltage_v, _voltage_label, _voltage_units = _find_voltage_channel(channels)

    start_index, end_index, idle_baseline_a, threshold_a = _find_weld_active_range(
        current_a,
        time_s,
        config=weld_config,
        voltage_v=voltage_v,
    )
    active_start_index = start_index
    active_end_index = end_index
    start_index, end_index = _crop_center_time_window(time_s, start_index, end_index)
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
        "active_weld_start_time_s": round(float(time_s[active_start_index]), 6),
        "active_weld_end_time_s": round(float(time_s[active_end_index - 1]), 6),
        "cropped_center_duration_s": WELD_CROPPED_CENTER_DURATION_S,
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
    generate_options: dict[str, bool] | None = None,
) -> dict:
    options = resolve_scan_generate_options(
        normalize_generate_options(generate_options, SCAN_GENERATE_KEYS),
    )
    if not any(options.values()):
        return {}

    experiment_id = experiment_id.strip().upper()
    scan_path = Path(scan_path)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    with scan_path.open("r", encoding="utf-8") as handle:
        scan_document = json.load(handle)

    scan_dir = output_folder / SCAN_SUBDIR
    scan_dir.mkdir(parents=True, exist_ok=True)

    document = generate_analyzing_document(
        scan_document,
        experiment_id=experiment_id,
        source_json_file=scan_path.name,
        threshold_mm=threshold_mm,
        scan_speed_mm_s=scan_speed_mm_s,
        scan_duration_s=scan_duration_s,
    )

    result: dict = {
        "profile_count": document["profile_count"],
        "baseline_profile_count": document["baseline_profile_count"],
        "probe_threshold_mm": document["probe_threshold_mm"],
        "source_json_file": scan_path.name,
        "filter_kernel_size": FILTER_KERNEL_SIZE,
    }

    if options["cropped_scan"]:
        _dump_json(scan_dir / CROPPED_SCAN_FILENAME, document, compact=True)
        result["scan_file"] = CROPPED_SCAN_FILENAME

    if options["64_64_scan"]:
        grid_document = generate_64_64_scan_document(document)
        _dump_json(scan_dir / SCAN_64_64_FILENAME, grid_document, compact=True)
        result["64_64_scan_file"] = SCAN_64_64_FILENAME

    filtered_document = None
    if (
        options["filtered"]
        or options["x_profile"]
        or options["y_profile"]
        or options["characteristics"]
    ):
        filtered_document = generate_filtered_scan_document(document)
        if options["filtered"]:
            _dump_json(scan_dir / FILTERED_SCAN_FILENAME, filtered_document, compact=True)
            result["filtered_scan_file"] = FILTERED_SCAN_FILENAME

    if options["x_profile"] or options["y_profile"]:
        if filtered_document is None:
            filtered_document = generate_filtered_scan_document(document)

        x_profile = None
        y_profile = None
        if options["x_profile"]:
            x_profile = generate_x_profile_document(filtered_document)
            _dump_json(scan_dir / X_PROFILE_FILENAME, x_profile)
            result["x_profile_file"] = X_PROFILE_FILENAME
            result["x_profile_point_count"] = x_profile["point_count"]
        if options["y_profile"]:
            y_profile = generate_y_profile_document(filtered_document)
            _dump_json(scan_dir / Y_PROFILE_FILENAME, y_profile)
            result["y_profile_file"] = Y_PROFILE_FILENAME
            result["y_profile_point_count"] = y_profile["point_count"]

        if x_profile is not None and y_profile is not None:
            x_hyperbola = x_profile.get("hyperbola") or {}
            y_hyperbola = y_profile.get("hyperbola") or {}
            x_curvature = x_hyperbola.get("curvature_1_per_m")
            y_curvature = y_hyperbola.get("curvature_1_per_m")
            if x_curvature is None and x_hyperbola.get("curvature_1_per_mm") is not None:
                x_curvature = float(x_hyperbola["curvature_1_per_mm"]) * 1000.0
            if y_curvature is None and y_hyperbola.get("curvature_1_per_mm") is not None:
                y_curvature = float(y_hyperbola["curvature_1_per_mm"]) * 1000.0
            combined = combine_profile_curvatures(
                x_curvature=x_curvature,
                y_curvature=y_curvature,
                x_r2=x_hyperbola.get("r2"),
                y_r2=y_hyperbola.get("r2"),
            )
            result.update(
                {
                    "x_curvature": x_curvature,
                    "y_curvature": y_curvature,
                    **combined,
                },
            )

    if filtered_document is not None:
        surface = compute_filtered_surface_curvature(filtered_document)
        if surface is not None:
            result["surface_curvature"] = surface["curvature_1_per_m"]

    return result


def run_analyze_weld(
    experiment_id: str,
    weld_path: Path,
    output_folder: Path,
    *,
    config: WeldConfig | None = None,
    weld_speed_m_per_min: float | None = None,
    generate_options: dict[str, bool] | None = None,
) -> dict:
    options = resolve_weld_generate_options(
        normalize_generate_options(generate_options, WELD_GENERATE_KEYS),
    )
    if not any(options.values()):
        return {}

    experiment_id = experiment_id.strip().upper()
    weld_path = Path(weld_path)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    weld_dir = output_folder / WELD_SUBDIR
    weld_dir.mkdir(parents=True, exist_ok=True)

    document = generate_analyzing_weld_h5(
        weld_path,
        experiment_id=experiment_id,
        source_h5_file=weld_path.name,
        config=config,
    )

    result: dict = {
        "weld_sample_count": document["sample_count"],
        "weld_duration_s": document["duration_s"],
        "weld_start_time_s": document["weld_start_time_s"],
        "weld_end_time_s": document["weld_end_time_s"],
        "weld_idle_baseline_a": document["idle_baseline_a"],
        "weld_threshold_a": document["threshold_a"],
        "source_h5_file": weld_path.name,
    }

    if options["cropped"]:
        save_time_s, save_channels = _as_float32_weld_payload(
            document["time_s"],
            document["channels"],
        )
        _save_weld_h5(
            weld_dir / CROPPED_WELD_FILENAME,
            save_time_s,
            save_channels,
            compression="lzf",
        )
        result["weld_file"] = CROPPED_WELD_FILENAME

    if options["power"]:
        power_time_s, power_channels = _compute_power_channels(
            document["time_s"],
            document["channels"],
        )
        _save_weld_h5(weld_dir / POWER_H5_FILENAME, power_time_s, power_channels, compression="lzf")
        result["power_file"] = POWER_H5_FILENAME

    need_basic_rows = options["characteristics"] or options["grenzen"] or options["char_graphen"]
    current_row = None
    voltage_row = None
    power_row = None
    weld_characteristic_rows: list[dict] = []

    if need_basic_rows:
        current_row = build_weld_current_characteristic_row(document["time_s"], document["channels"])
        voltage_row = build_weld_voltage_characteristic_row(document["time_s"], document["channels"])
        power_row = build_weld_power_characteristic_row(document["time_s"], document["channels"])
        if options["characteristics"]:
            if current_row is not None:
                weld_characteristic_rows.append(current_row)
            if voltage_row is not None:
                weld_characteristic_rows.append(voltage_row)
            if power_row is not None:
                weld_characteristic_rows.append(power_row)

    grenzen_file = None
    char_graphen_file = None
    if options["grenzen"] or options["char_graphen"]:
        grenzen_regions = _build_weld_grenzen_regions(
            document["time_s"],
            document["channels"],
            current_row,
        )
        if grenzen_regions is not None:
            try:
                _key, _current_a, _label, channel_units = _find_current_channel(document["channels"])
            except ValueError:
                channel_units = "A"
            stats = _apply_weld_mid_percentiles(dict(current_row or {}))
            mid_threshold = _json_safe_characteristic_value(stats.get("current_p02_p98_mid"))

            if options["grenzen"]:
                grenzen_document = _serialize_grenzen_document(
                    quantity="Current",
                    unit=str(stats.get("unit") or channel_units or "A"),
                    regions=grenzen_regions,
                )
                write_grenzen_file(weld_dir / GRENZEN_FILENAME, grenzen_document)
                grenzen_file = GRENZEN_FILENAME

            if options["char_graphen"]:
                char_graphen_document = build_weld_char_graphen_document(
                    document["time_s"],
                    document["channels"],
                    grenzen_regions,
                    mid_threshold=mid_threshold,
                )
                if char_graphen_document is not None:
                    char_graphen_output = build_char_graphen_output_document(char_graphen_document)
                    if char_graphen_output is not None:
                        write_char_graphen_file(weld_dir / CHAR_GRAPHEN_FILENAME, char_graphen_output)
                        char_graphen_file = CHAR_GRAPHEN_FILENAME
                    if options["characteristics"]:
                        char_graphen_source = char_graphen_output or char_graphen_document
                        char_fields = build_char_graphen_characteristic_fields(char_graphen_source)
                        current_char_fields, voltage_char_fields, power_char_fields, duration_char_fields = (
                            _split_char_graphen_characteristic_fields(char_fields)
                        )
                        if current_char_fields:
                            if current_row is not None:
                                current_row.update(current_char_fields)
                            else:
                                weld_characteristic_rows.append(
                                    {"quantity": WELD_CURRENT_QUANTITY, **current_char_fields},
                                )
                        if voltage_char_fields:
                            if voltage_row is not None:
                                voltage_row.update(voltage_char_fields)
                            else:
                                weld_characteristic_rows.append(
                                    {"quantity": WELD_VOLTAGE_QUANTITY, **voltage_char_fields},
                                )
                        if power_char_fields:
                            if power_row is not None:
                                power_row.update(power_char_fields)
                            else:
                                weld_characteristic_rows.append(
                                    {"quantity": WELD_POWER_QUANTITY, **power_char_fields},
                                )
                        if duration_char_fields:
                            duration_row = _normalize_weld_duration_characteristic_row(duration_char_fields)
                            if duration_row is not None:
                                weld_characteristic_rows.append(duration_row)

    if options["characteristics"]:
        result["weld_characteristic_rows"] = weld_characteristic_rows
    if grenzen_file is not None:
        result["grenzen_file"] = grenzen_file
    if char_graphen_file is not None:
        result["char_graphen_file"] = char_graphen_file
    return result


def _characteristic_document_from_analyze_result(result: dict) -> dict:
    scan_fields = build_curvature_characteristic_fields(
        x_curvature=result.get("x_curvature"),
        y_curvature=result.get("y_curvature"),
        total_curvature_mean=result.get("total_curvature_mean"),
        total_curvature_rms=result.get("total_curvature_rms"),
        surface_curvature=result.get("surface_curvature"),
    )
    weld_rows = list(result.get("weld_characteristic_rows") or [])
    return {"scan": scan_fields, "weld": weld_rows}


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
    weld_speed_m_per_min: float | None = None,
    scan_generate_options: dict[str, bool] | None = None,
    weld_generate_options: dict[str, bool] | None = None,
    output_folder: Path | None = None,
) -> dict:
    if scan_path is None and weld_path is None:
        raise ValueError("Weder Scan- noch Weld-Datei vorhanden.")

    scan_options = resolve_scan_generate_options(
        normalize_generate_options(scan_generate_options, SCAN_GENERATE_KEYS),
    )
    weld_options = resolve_weld_generate_options(
        normalize_generate_options(weld_generate_options, WELD_GENERATE_KEYS),
    )

    run_scan = scan_path is not None and any(scan_options.values())
    run_weld = weld_path is not None and any(weld_options.values())
    if not run_scan and not run_weld:
        raise ValueError("Keine Generate-Optionen ausgewählt.")

    experiment_id = experiment_id.strip().upper()
    output_dir = Path(output_dir)
    if output_folder is None:
        timestamp = datetime.now()
        analyze_folder = build_analyze_folder_name(experiment_id, timestamp)
        output_folder = output_dir / analyze_folder
    else:
        output_folder = Path(output_folder)
        analyze_folder = output_folder.name
    output_folder.mkdir(parents=True, exist_ok=True)

    result: dict = {
        "success": True,
        "experiment_id": experiment_id,
        "analyze_folder": analyze_folder,
    }

    jobs = []
    if run_scan:
        jobs.append(
            (
                "scan",
                lambda: run_analyze_scan(
                    experiment_id,
                    scan_path,
                    output_folder,
                    threshold_mm=threshold_mm,
                    scan_speed_mm_s=scan_speed_mm_s,
                    scan_duration_s=scan_duration_s,
                    generate_options=scan_options,
                ),
            )
        )
    if run_weld:
        jobs.append(
            (
                "weld",
                lambda: run_analyze_weld(
                    experiment_id,
                    weld_path,
                    output_folder,
                    config=weld_config,
                    weld_speed_m_per_min=weld_speed_m_per_min,
                    generate_options=weld_options,
                ),
            )
        )

    if len(jobs) == 1:
        result.update(jobs[0][1]())
    else:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {pool.submit(fn): name for name, fn in jobs}
            for future in as_completed(futures):
                result.update(future.result())

    write_scan_characteristics = run_scan and scan_options["characteristics"]
    write_weld_characteristics = run_weld and weld_options["characteristics"]
    if write_scan_characteristics or write_weld_characteristics:
        char_path = output_folder / CHARACTERISTICS_FILENAME
        existing_doc = None
        if char_path.is_file():
            try:
                existing_doc = load_characteristics(char_path)
            except ValueError:
                existing_doc = None

        if write_scan_characteristics:
            scan_fields = build_curvature_characteristic_fields(
                x_curvature=result.get("x_curvature"),
                y_curvature=result.get("y_curvature"),
                total_curvature_mean=result.get("total_curvature_mean"),
                total_curvature_rms=result.get("total_curvature_rms"),
                surface_curvature=result.get("surface_curvature"),
            )
        elif existing_doc:
            scan_fields = dict(existing_doc.get("scan") or {})
        else:
            scan_fields = {}

        if write_weld_characteristics:
            weld_rows = list(result.get("weld_characteristic_rows") or [])
        elif existing_doc:
            weld_rows = list(existing_doc.get("weld") or [])
        else:
            weld_rows = []

        if scan_fields or weld_rows:
            write_characteristics_file(
                char_path,
                scan_fields=scan_fields,
                weld_rows=weld_rows,
            )
            result["characteristics_file"] = CHARACTERISTICS_FILENAME
        elif char_path.is_file():
            char_path.unlink()

    return result
