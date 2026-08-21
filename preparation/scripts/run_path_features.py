"""Path features for characteristics.json (normalized hotspot + shrinkage kennwerte)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np

PATH_IDS = ("ME", "PO", "SO", "SI", "LI")
STEP_MM = 1.0
PLATE_MIN_MM = 15.0
PLATE_MAX_MM = 65.0
PLATE_CENTER_MM = 0.5 * (PLATE_MIN_MM + PLATE_MAX_MM)
LREF_MM = PLATE_MAX_MM - PLATE_MIN_MM
BETA = 1.0
A_LONG = 1.0
A_TRANS = 2.0
R0_MM = 3.0
D_NORM_MM = 2.0
LAMBDA_COOL = 0.02

PATH_KERNEL_FIELDS = (
    "path_A",
    "path_Bx",
    "path_By",
    "path_C1",
    "path_C2",
    "path_C_aniso",
    "path_C_ang",
    "path_D_mean",
    "path_D_95",
    "path_Ex",
    "path_Ey",
    "path_E",
)
PATH_ID_ONEHOT_FIELDS = tuple(f"path_id_{code}" for code in PATH_IDS)
PATH_CHARACTERISTIC_FIELDS = PATH_ID_ONEHOT_FIELDS + PATH_KERNEL_FIELDS

_SCRIPTS_DIR = Path(__file__).resolve().parent
PATTERNS_DIR = _SCRIPTS_DIR.parent / "templates" / "patterns"


def _json_safe(value):
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(number):
        return None
    return number


def build_path_id_onehot_fields(path_id: str | None) -> dict[str, float]:
    normalized = str(path_id or "").strip().upper()
    return {
        key: 1.0 if normalized == code else 0.0
        for code, key in zip(PATH_IDS, PATH_ID_ONEHOT_FIELDS)
    }


def serialize_path_fields(fields: dict | None) -> dict[str, float]:
    payload: dict[str, float] = {}
    if not isinstance(fields, dict):
        return payload
    for key in PATH_CHARACTERISTIC_FIELDS:
        value = _json_safe(fields.get(key))
        if value is None:
            continue
        if key in PATH_ID_ONEHOT_FIELDS:
            payload[key] = 1.0 if value >= 0.5 else 0.0
        else:
            payload[key] = value
    return payload


def normalize_path_fields(raw) -> dict[str, float]:
    return serialize_path_fields(raw if isinstance(raw, dict) else {})


def list_path_characteristic_keys() -> tuple[str, ...]:
    return PATH_CHARACTERISTIC_FIELDS


def _load_pattern_points(path_id: str) -> np.ndarray:
    normalized = str(path_id or "").strip().upper()
    if normalized not in PATH_IDS:
        raise ValueError(f"Unbekannte PATH ID: {path_id}")
    pattern_path = PATTERNS_DIR / f"{normalized}.json"
    if not pattern_path.is_file():
        raise FileNotFoundError(f"Musterdatei fehlt: {pattern_path}")
    with pattern_path.open("r", encoding="utf-8") as handle:
        document = json.load(handle)
    if not isinstance(document, list) or not document:
        raise ValueError(f"Ungültiges Pfadmuster: {normalized}")
    polyline = document[0]
    points = np.asarray(polyline, dtype=float)
    if points.ndim != 2 or points.shape[1] != 2 or points.shape[0] < 2:
        raise ValueError(f"Pfadmuster {normalized} hat zu wenige Punkte.")
    return points


def discretize_path(points: np.ndarray, step_mm: float = STEP_MM) -> dict[str, np.ndarray]:
    diffs = np.diff(points, axis=0)
    seg_len = np.linalg.norm(diffs, axis=1)
    vertex_keep = np.concatenate(([True], seg_len > 1e-12))
    vertices = points[vertex_keep]
    if vertices.shape[0] < 2:
        raise ValueError("Pfad hat keine positive Länge.")
    seg_len = np.linalg.norm(np.diff(vertices, axis=0), axis=1)
    total = float(np.sum(seg_len))
    n_steps = max(int(np.ceil(total / max(step_mm, 1e-6))), 1)
    sample_s = np.linspace(0.0, total, n_steps + 1)
    cumulative = np.concatenate(([0.0], np.cumsum(seg_len)))
    sample_xy = np.column_stack(
        [
            np.interp(sample_s, cumulative, vertices[:, 0]),
            np.interp(sample_s, cumulative, vertices[:, 1]),
        ]
    )
    mid = 0.5 * (sample_xy[:-1] + sample_xy[1:])
    delta = sample_xy[1:] - sample_xy[:-1]
    ds = np.linalg.norm(delta, axis=1)
    valid = ds > 1e-9
    mid = mid[valid]
    delta = delta[valid]
    ds = ds[valid]
    tangent = delta / ds[:, None]
    return {
        "mid": mid,
        "tangent": tangent,
        "ds": ds,
        "length_mm": float(np.sum(ds)),
    }


@lru_cache(maxsize=8)
def _cached_segments(path_id: str, step_mm: float) -> dict[str, np.ndarray | float]:
    points = _load_pattern_points(path_id)
    return discretize_path(points, step_mm=step_mm)


def _hotspot_history(mid: np.ndarray, ds: np.ndarray) -> np.ndarray:
    n = ds.size
    if n == 0:
        return np.zeros(0, dtype=float)
    t_mid = np.cumsum(ds) - 0.5 * ds
    delta = mid[:, None, :] - mid[None, :, :]
    dist2 = np.sum(delta * delta, axis=2)
    dt = t_mid[:, None] - t_mid[None, :]
    later = np.tril(np.ones((n, n), dtype=bool), k=-1)
    dt_pos = np.where(later, dt, 0.0)
    sigma2 = np.maximum(R0_MM**2 + 2.0 * D_NORM_MM * dt_pos, 1e-12)
    weight = np.exp(-dist2 / (2.0 * sigma2)) * np.exp(-LAMBDA_COOL * dt_pos)
    weight = np.where(later, weight, 0.0)
    hotspot = weight @ ds
    peak = float(np.max(hotspot)) if hotspot.size else 0.0
    if peak > 0:
        return hotspot / peak
    return np.zeros(n, dtype=float)


def _principal_angle(vector: np.ndarray) -> float:
    angle = float(np.arctan2(vector[1], vector[0]))
    if angle < 0:
        angle += np.pi
    if angle >= np.pi:
        angle -= np.pi
    return angle


def compute_path_kernel_fields(mid: np.ndarray, tangent: np.ndarray, ds: np.ndarray) -> dict[str, float]:
    n = ds.size
    if n == 0:
        return {}
    hotspot = _hotspot_history(mid, ds)
    amplitude = ds * (1.0 + BETA * hotspot)
    normal = np.column_stack((-tangent[:, 1], tangent[:, 0]))
    tx, ty = tangent[:, 0], tangent[:, 1]
    nx, ny = normal[:, 0], normal[:, 1]

    path_a = float(np.sum(amplitude))
    path_bx = float(np.sum(amplitude * (A_LONG * tx**2 + A_TRANS * nx**2)))
    path_by = float(np.sum(amplitude * (A_LONG * ty**2 + A_TRANS * ny**2)))

    tensor = np.zeros((2, 2), dtype=float)
    for index in range(n):
        tvec = tangent[index]
        nvec = normal[index]
        tensor += amplitude[index] * (
            A_LONG * np.outer(tvec, tvec) + A_TRANS * np.outer(nvec, nvec)
        )
    eigvals, eigvecs = np.linalg.eigh(tensor)
    order = np.argsort(eigvals)[::-1]
    lambda1 = float(eigvals[order[0]])
    lambda2 = float(eigvals[order[1]])
    angle = _principal_angle(eigvecs[:, order[0]])

    offset = mid - np.array([PLATE_CENTER_MM, PLATE_CENTER_MM], dtype=float)
    moment_x = float(np.sum(amplitude * offset[:, 1]))
    moment_y = float(np.sum(amplitude * offset[:, 0]))
    denom = path_a * LREF_MM + 1e-12
    path_ex = moment_x / denom
    path_ey = moment_y / denom

    length = float(np.sum(ds))
    return {
        "path_A": path_a,
        "path_Bx": path_bx,
        "path_By": path_by,
        "path_C1": lambda1,
        "path_C2": lambda2,
        "path_C_aniso": abs(path_bx - path_by) / (path_bx + path_by + 1e-12),
        "path_C_ang": angle,
        "path_D_mean": float(np.sum(ds * hotspot) / (length + 1e-12)),
        "path_D_95": float(np.percentile(hotspot, 95)),
        "path_Ex": path_ex,
        "path_Ey": path_ey,
        "path_E": float(np.hypot(path_ex, path_ey)),
    }


def build_path_feature_fields(
    *,
    path_id: str,
    step_mm: float = STEP_MM,
) -> dict[str, float]:
    normalized = str(path_id or "").strip().upper()
    if normalized not in PATH_IDS:
        return {}

    segments = _cached_segments(normalized, float(step_mm))
    mid = np.asarray(segments["mid"], dtype=float)
    tangent = np.asarray(segments["tangent"], dtype=float)
    ds = np.asarray(segments["ds"], dtype=float)
    return compute_path_kernel_fields(mid, tangent, ds)


def build_path_fields_for_experiment(
    *,
    path_id: str | None,
) -> dict[str, float]:
    onehot = build_path_id_onehot_fields(path_id)
    if not path_id:
        return {}
    try:
        fields = build_path_feature_fields(path_id=path_id)
    except (ValueError, FileNotFoundError, OSError):
        fields = {}
    if not fields and not any(value == 1.0 for value in onehot.values()):
        return {}
    return {**fields, **onehot}
