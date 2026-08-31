"""Polynomial Elastic Net training on a View-export Excel table.

Nested CV: outer leave-one-path-out (PATH ID), inner shuffled 5-fold for α/ρ.
Features are expanded up to a chosen max degree (1–5), then mRMR; the best
degree in that range is picked by mean outer RMSE.
No new experiment values.
"""

from __future__ import annotations

import json
from datetime import datetime
from math import comb
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.linear_model import ElasticNet, ElasticNetCV
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

TARGET_COLUMNS = ("curvature_x", "curvature_y", "curvature_surface_mean")
LEGACY_CATEGORY_NAMES = {"zielgröße", "default", "pfad", "weld"}
PATH_IDS = ("ME", "PO", "SO", "SI", "LI")
GROUP_CANDIDATES = ("PATH ID", "path_id", "PATH_ID")
ID_CANDIDATES = ("ID", "id")
SKIP_COLUMNS = {
    "COUNT",
    "count",
    "SERIES",
    "series",
    "NUMBER",
    "number",
    "ID",
    "id",
    "PATH ID",
    "path_id",
    "PATH_ID",
}
SKIP_PREFIXES = (
    "curvature_total",
    "curvature_surface",
)
AUTO_FEATURE_KS = (8, 12, 16, 20, 24)
INNER_CV_FOLDS = 5
POLY_DEGREE_MIN = 1
POLY_DEGREE_MAX = 5
MAX_POLY_TERMS = 4000
MAX_MRMR_CANDIDATES = 250


def _norm_name(name) -> str:
    if name is None or (isinstance(name, float) and np.isnan(name)):
        return ""
    return str(name).strip()


def _is_category_row(values) -> bool:
    texts = [_norm_name(value) for value in values]
    nonempty = [item for item in texts if item]
    if not nonempty:
        return False
    return all(item.lower() in LEGACY_CATEGORY_NAMES for item in nonempty)


def _forward_fill_categories(values) -> list[str]:
    filled: list[str] = []
    last = ""
    for value in values:
        text = _norm_name(value)
        if text:
            last = text
        filled.append(last)
    return filled


def read_export_columns(path: Path) -> tuple[list[dict[str, str]], bool]:
    header = pd.read_excel(path, sheet_name=0, header=None, nrows=2)
    names = [_norm_name(value) for value in header.iloc[0].tolist()]
    raw_second = header.iloc[1].tolist() if header.shape[0] > 1 else []
    has_categories = _is_category_row(_forward_fill_categories(raw_second))
    columns = []
    for name in names:
        if not name or name.lower().startswith("unnamed"):
            continue
        columns.append({"name": name})
    return columns, has_categories


def resolve_training_target(columns: list[dict], roles: dict) -> str:
    for item in columns:
        name = _norm_name(item.get("name"))
        if not name or name in SKIP_COLUMNS or name in GROUP_CANDIDATES:
            continue
        return name
    targets = [name for name in (roles.get("targets") or []) if name]
    if targets:
        return targets[0]
    raise ValueError("Keine Zielgröße in train.xlsx. Die Zielgröße muss die erste Spalte sein.")


def load_dataset(path: Path) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    _columns, has_categories = read_export_columns(path)
    raw = pd.read_excel(path, sheet_name=0, header=None)
    start = 2 if has_categories else 1
    names = [_norm_name(value) for value in raw.iloc[0].tolist()]
    frame = raw.iloc[start:].copy()
    frame.columns = names
    keep = [col for col in frame.columns if col and not str(col).lower().startswith("unnamed")]
    frame = frame.loc[:, keep].reset_index(drop=True)
    roles = classify_columns(frame.columns)
    return frame, roles


def classify_columns(columns) -> dict[str, list[str]]:
    names = [_norm_name(col) for col in columns]
    group = next((name for name in GROUP_CANDIDATES if name in names), None)
    experiment_id = next((name for name in ID_CANDIDATES if name in names), None)
    target = ""
    for name in names:
        if name in GROUP_CANDIDATES or name in SKIP_COLUMNS:
            continue
        target = name
        break
    targets = [target] if target else []
    skip = set(SKIP_COLUMNS)
    skip.update(targets)
    skip.update(name for name in TARGET_COLUMNS if name != target)
    if experiment_id:
        skip.add(experiment_id)
    features = []
    for name in names:
        if name in skip:
            continue
        if any(name.startswith(prefix) for prefix in SKIP_PREFIXES):
            continue
        features.append(name)
    return {
        "targets": targets,
        "features": features,
        "group": group,
        "id": experiment_id,
    }


def _path_id_codes() -> dict[str, float]:
    return {path_id: float(index) for index, path_id in enumerate(PATH_IDS)}


def _numeric_series(frame: pd.DataFrame, name: str) -> pd.Series:
    series = frame[name]
    if name in GROUP_CANDIDATES:
        labels = series.astype(str).str.strip().str.upper()
        mapped = labels.map(_path_id_codes())
        return pd.Series(mapped, index=frame.index, dtype="float64")
    return pd.to_numeric(series, errors="coerce")


def _numeric_matrix(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if not columns:
        return pd.DataFrame(index=frame.index)
    present = [name for name in columns if name in frame.columns]
    if not present:
        return pd.DataFrame(index=frame.index)
    data = {name: _numeric_series(frame, name) for name in present}
    return pd.DataFrame(data, index=frame.index)


def variance_filter(x: pd.DataFrame, min_std: float = 1e-9) -> list[str]:
    kept = []
    for column in x.columns:
        series = x[column]
        if series.nunique(dropna=True) <= 1:
            continue
        std = float(series.std(skipna=True))
        if np.isfinite(std) and std > min_std:
            kept.append(column)
    return kept


def _spearman_abs(left: np.ndarray, right: np.ndarray) -> float:
    mask = np.isfinite(left) & np.isfinite(right)
    if int(np.count_nonzero(mask)) < 5:
        return 0.0
    a = pd.Series(left[mask])
    b = pd.Series(right[mask])
    if a.nunique() <= 1 or b.nunique() <= 1:
        return 0.0
    value = a.corr(b, method="spearman")
    if value is None or not np.isfinite(value):
        return 0.0
    return abs(float(value))


def fcq_mrmr(x: pd.DataFrame, y: np.ndarray, k: int) -> list[str]:
    columns = list(x.columns)
    if not columns:
        return []
    k = max(1, min(int(k), len(columns)))
    y = np.asarray(y, dtype=float)
    relevance = {col: _spearman_abs(x[col].to_numpy(dtype=float), y) for col in columns}
    selected: list[str] = []
    remaining = set(columns)
    while remaining and len(selected) < k:
        best_name = None
        best_score = -1e18
        for name in remaining:
            redundancy = 0.0
            if selected:
                redundancy = float(
                    np.mean(
                        [
                            _spearman_abs(
                                x[name].to_numpy(dtype=float),
                                x[other].to_numpy(dtype=float),
                            )
                            for other in selected
                        ]
                    )
                )
            score = relevance[name] - redundancy
            if score > best_score:
                best_score = score
                best_name = name
        if best_name is None:
            break
        selected.append(best_name)
        remaining.remove(best_name)
    return selected


class PolyThenSelect(BaseEstimator, TransformerMixin):
    def __init__(self, degree: int, input_features: list[str], selected: list[str]):
        self.degree = int(degree)
        self.input_features = [str(item) for item in input_features]
        self.selected = [str(item) for item in selected]

    def fit(self, x, y=None):
        self.poly_ = PolynomialFeatures(degree=self.degree, include_bias=False)
        self.poly_.fit(np.asarray(x, dtype=float))
        names = [str(item) for item in self.poly_.get_feature_names_out(self.input_features)]
        index = {name: i for i, name in enumerate(names)}
        missing = [name for name in self.selected if name not in index]
        if missing:
            raise ValueError("Polynomterme fehlen nach der Erweiterung: " + ", ".join(missing[:8]))
        self.indices_ = np.array([index[name] for name in self.selected], dtype=int)
        return self

    def transform(self, x):
        expanded = self.poly_.transform(np.asarray(x, dtype=float))
        return expanded[:, self.indices_]


def _n_poly_terms(n_features: int, degree: int) -> int:
    if n_features <= 0 or degree < 1:
        return 0
    return int(comb(n_features + degree, degree) - 1)


def _limit_poly_inputs(
    x: pd.DataFrame,
    y: np.ndarray,
    columns: list[str],
    degree: int,
) -> list[str]:
    remaining = [name for name in columns if name in x.columns]
    free = list(remaining)
    while free and _n_poly_terms(len(free), degree) > MAX_POLY_TERMS:
        weakest = min(free, key=lambda name: _spearman_abs(x[name].to_numpy(dtype=float), y))
        free.remove(weakest)
    kept = set(free)
    return [name for name in remaining if name in kept]


def _poly_degrees_up_to(max_degree: int) -> list[int]:
    high = min(POLY_DEGREE_MAX, max(POLY_DEGREE_MIN, int(max_degree)))
    return list(range(POLY_DEGREE_MIN, high + 1))


def _empty_poly_spec(columns: list[str]) -> dict:
    return {"degree": None, "poly_inputs": list(columns)}


def _is_better_cv(new: dict, best: dict | None) -> bool:
    if best is None:
        return True
    if new["mean_rmse"] < best["mean_rmse"]:
        return True
    if new["mean_rmse"] != best["mean_rmse"]:
        return False
    new_degree = new.get("degree")
    best_degree = best.get("degree")
    if new_degree is not None and best_degree is not None and new_degree != best_degree:
        return new_degree < best_degree
    return new["k"] < best["k"]


def _inner_random_cv_splits(
    n: int,
    n_splits: int = INNER_CV_FOLDS,
) -> list[tuple[np.ndarray, np.ndarray]] | None:
    if n < 4:
        return None
    folds = max(2, min(int(n_splits), n))
    splitter = KFold(n_splits=folds, shuffle=True, random_state=0)
    splits = [(train_idx, held_idx) for train_idx, held_idx in splitter.split(np.arange(n))]
    if len(splits) < 2:
        return None
    return splits


def _linear_estimator(splits: list[tuple[np.ndarray, np.ndarray]] | None):
    if splits is None:
        return "enet", ElasticNet(alpha=1e-3, l1_ratio=0.5, max_iter=20000, random_state=0)
    return "enet", ElasticNetCV(
        l1_ratio=[0.2, 0.5, 0.8],
        cv=splits,
        max_iter=20000,
        random_state=0,
    )


def _fit_learner(
    x: np.ndarray,
    y: np.ndarray,
    learner: str = "elasticnet",
    *,
    cv: str = "lopo",
    cv_folds: int = 5,
    groups: np.ndarray | pd.Series | None = None,
    degree: int | None = None,
    poly_inputs: list[str] | None = None,
    selected_terms: list[str] | None = None,
) -> Pipeline:
    del cv, cv_folds, groups
    n = int(np.asarray(x).shape[0])
    splits = _inner_random_cv_splits(n, INNER_CV_FOLDS)
    est_name, estimator = _linear_estimator(splits)
    steps = []
    if degree is not None and poly_inputs and selected_terms:
        steps.append(
            (
                "poly_select",
                PolyThenSelect(int(degree), list(poly_inputs), list(selected_terms)),
            )
        )
    steps.append(("scale", StandardScaler()))
    steps.append((est_name, estimator))
    model = Pipeline(steps)
    model.fit(x, y)
    return model


def _estimator(model: Pipeline):
    return model.steps[-1][1]


def _expanded_feature_names(model: Pipeline, columns: list[str]) -> list[str]:
    selector = model.named_steps.get("poly_select")
    if selector is not None:
        return [str(item) for item in selector.selected]
    names = [str(item) for item in columns]
    poly = model.named_steps.get("poly")
    if poly is None:
        return names
    return [str(item) for item in poly.get_feature_names_out(names)]


def _coef_vector(est) -> np.ndarray:
    return np.asarray(est.coef_, dtype=float).ravel()


def _coefficient_map(model: Pipeline, columns: list[str]) -> dict[str, float]:
    names = _expanded_feature_names(model, columns)
    est = _estimator(model)
    coef = np.asarray(est.coef_, dtype=float).ravel()
    return {name: float(value) for name, value in zip(names, coef)}


def _intercept_value(est) -> float:
    return float(np.asarray(est.intercept_, dtype=float).ravel()[0])


def _fold_scores(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float | None]:
    y_true = np.asarray(y_true, dtype=float).ravel()
    y_pred = np.asarray(y_pred, dtype=float).ravel()
    residual = y_true - y_pred
    rmse = float(np.sqrt(np.mean(np.square(residual))))
    ss_res = float(np.sum(np.square(residual)))
    centered = y_true - np.mean(y_true)
    ss_tot = float(np.sum(np.square(centered)))
    r2 = None
    if ss_tot > 1e-18:
        r2 = float(1.0 - ss_res / ss_tot)
    return rmse, r2


def reproducibility_ceiling(frame: pd.DataFrame, target: str, roles: dict) -> dict:
    y = pd.to_numeric(frame[target], errors="coerce")
    valid = y.notna()
    y = y[valid]
    if y.size < 4:
        return {"rmse_noise": None, "r2_ceiling": None, "n_groups": 0}
    group_cols = []
    for name in ("WFS [m/min]", "WFS", "wfs", "WS [m/min]", "WS", "ws"):
        if name in frame.columns:
            group_cols.append(name)
    group_name = roles.get("group")
    if group_name:
        group_cols.append(group_name)
    if not group_cols:
        rmse = float(y.std(ddof=1))
        return {"rmse_noise": rmse, "r2_ceiling": None, "n_groups": 0}
    grouped = frame.loc[valid, group_cols].copy()
    grouped["_y"] = y.to_numpy()
    stats = grouped.groupby(group_cols, dropna=False)["_y"].agg(["std", "count"])
    repeats = stats[stats["count"] >= 2]["std"].dropna()
    if repeats.empty:
        return {"rmse_noise": None, "r2_ceiling": None, "n_groups": 0}
    rmse_noise = float(np.sqrt(np.mean(np.square(repeats.to_numpy(dtype=float)))))
    total_std = float(y.std(ddof=1))
    r2_ceiling = None
    if total_std > 1e-12:
        r2_ceiling = float(max(0.0, 1.0 - (rmse_noise**2) / (total_std**2)))
    return {
        "rmse_noise": rmse_noise,
        "r2_ceiling": r2_ceiling,
        "n_groups": int(repeats.size),
    }


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    yt = y_true[mask]
    yp = y_pred[mask]
    if yt.size == 0:
        return {"rmse": None, "mae": None, "r2": None, "n": 0}
    resid = yt - yp
    ss_res = float(np.sum(resid**2))
    ss_tot = float(np.sum((yt - float(np.mean(yt))) ** 2))
    r2 = float(1.0 - ss_res / ss_tot) if ss_tot > 0 else None
    return {
        "rmse": float(np.sqrt(ss_res / yt.size)),
        "mae": float(np.mean(np.abs(resid))),
        "r2": r2,
        "n": int(yt.size),
    }


def _design(
    frame: pd.DataFrame, columns: list[str], *, fill: pd.Series | None = None
) -> tuple[pd.DataFrame, pd.Series]:
    matrix = _numeric_matrix(frame, columns)
    if fill is None:
        fill = matrix.median(numeric_only=True)
    return matrix.fillna(fill), fill


def _train_test_design(
    train_frame: pd.DataFrame,
    test_frame: pd.DataFrame,
    columns: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    x_train, fill = _design(train_frame, columns)
    x_test, _ = _design(test_frame, columns, fill=fill)
    return x_train, x_test


def _try_id_values(frame: pd.DataFrame, roles: dict) -> pd.Series | None:
    id_col = roles.get("id")
    if not id_col or id_col not in frame.columns:
        return None
    return frame[id_col].astype(str).str.strip().str.upper()


def _try_group_values(frame: pd.DataFrame, roles: dict) -> pd.Series | None:
    group_col = roles.get("group")
    if not group_col or group_col not in frame.columns:
        return None
    return frame[group_col].astype(str).str.strip().str.upper()


def _select_on_frame(
    work: pd.DataFrame,
    y: np.ndarray,
    feature_cols: list[str],
    k: int,
    *,
    learner: str = "elasticnet",
    cv: str = "lopo",
    cv_folds: int = 5,
    groups: np.ndarray | pd.Series | None = None,
    degree: int | None = None,
) -> tuple[list[str], list[str], dict]:
    pool = list(dict.fromkeys(feature_cols))
    x_raw, _ = _design(work, pool)
    kept = variance_filter(x_raw)
    if not kept:
        return [], [], _empty_poly_spec([])

    x_var = x_raw.loc[:, [name for name in kept if name in x_raw.columns]]
    spec = _empty_poly_spec(list(x_var.columns))
    if degree is not None:
        degree = max(1, int(degree))
        poly_inputs = _limit_poly_inputs(x_var, y, list(x_var.columns), degree)
        if not poly_inputs:
            return [], [], _empty_poly_spec([])
        x_in = x_var.loc[:, poly_inputs]
        poly = PolynomialFeatures(degree=degree, include_bias=False)
        expanded = poly.fit_transform(x_in.to_numpy(dtype=float))
        names = [str(item) for item in poly.get_feature_names_out(list(poly_inputs))]
        x_var = pd.DataFrame(expanded, index=x_in.index, columns=names)
        spec = {"degree": degree, "poly_inputs": list(poly_inputs)}
        if len(x_var.columns) > MAX_MRMR_CANDIDATES:
            scores = {
                name: _spearman_abs(x_var[name].to_numpy(dtype=float), y)
                for name in x_var.columns
            }
            ordered = sorted(scores, key=scores.get, reverse=True)
            keep = ordered[:MAX_MRMR_CANDIDATES]
            x_var = x_var.loc[:, [name for name in keep if name in x_var.columns]]
    k_total = max(0, int(k))
    rank_n = min(len(x_var.columns), max(k_total, 1) + 8)
    ranked = fcq_mrmr(x_var, y, rank_n)
    selected = ranked[:k_total] if k_total else []
    columns = list(dict.fromkeys(selected))
    if spec.get("degree") is None:
        spec["poly_inputs"] = list(columns)
    return selected, columns, spec


def _fit_selected(
    frame: pd.DataFrame,
    y: np.ndarray,
    selected: list[str],
    columns: list[str],
    spec: dict,
    learner: str,
    *,
    cv: str,
    cv_folds: int,
) -> tuple[Pipeline, pd.Series, list[str]]:
    degree = spec.get("degree")
    poly_inputs = list(spec.get("poly_inputs") or columns)
    if degree is None:
        x_train, fill = _design(frame, columns)
        model = _fit_learner(
            x_train.to_numpy(dtype=float),
            y,
            learner,
            cv=cv,
            cv_folds=cv_folds,
        )
        return model, fill, columns
    x_train, fill = _design(frame, poly_inputs)
    model = _fit_learner(
        x_train.to_numpy(dtype=float),
        y,
        "elasticnet",
        cv=cv,
        cv_folds=cv_folds,
        degree=int(degree),
        poly_inputs=poly_inputs,
        selected_terms=list(selected),
    )
    return model, fill, poly_inputs


def _predict_selected(
    model: Pipeline,
    frame: pd.DataFrame,
    input_columns: list[str],
    fill: pd.Series,
) -> np.ndarray:
    x_held, _ = _design(frame, input_columns, fill=fill)
    return np.asarray(model.predict(x_held.to_numpy(dtype=float)), dtype=float).ravel()


def _iter_outer_path_folds(paths: pd.Series):
    values = np.asarray(paths)
    unique = [item for item in pd.unique(paths) if item and str(item) != "NAN"]
    order = {name: index for index, name in enumerate(PATH_IDS)}
    unique = sorted(unique, key=lambda name: (order.get(str(name), len(PATH_IDS)), str(name)))
    if len(unique) < 2:
        return
    for held in unique:
        held_mask = values == held
        train_mask = ~held_mask
        if np.any(train_mask) and np.any(held_mask):
            yield str(held), train_mask, held_mask


def _emit(progress, event: str, **data) -> None:
    if progress is None:
        return
    progress(event, **data)


def train_cell(
    train_frame: pd.DataFrame,
    roles: dict,
    *,
    target: str,
    learner: str = "polynomial",
    cv: str = "lopo",
    cv_folds: int = 5,
    poly_degree_max: int = POLY_DEGREE_MIN,
    progress=None,
) -> dict:
    if target not in train_frame.columns:
        raise ValueError(f"Zielspalte fehlt in den Trainingsdaten: {target}")

    y_train = pd.to_numeric(train_frame[target], errors="coerce")
    feature_cols = list(roles.get("features") or [])
    path_train = _try_group_values(train_frame, roles)
    id_train = _try_id_values(train_frame, roles)

    if path_train is None:
        raise ValueError("PATH-ID-Spalte fehlt für die äußere Leave-One-Path-Out-Kreuzvalidierung.")

    train_ok = y_train.notna() & path_train.ne("") & path_train.ne("NAN")
    work_train = train_frame.loc[train_ok].copy().reset_index(drop=True)
    y_train_v = y_train.loc[train_ok].to_numpy(dtype=float)
    path_train = path_train.loc[train_ok].reset_index(drop=True)
    if id_train is not None:
        id_train = id_train.loc[train_ok].reset_index(drop=True)

    if work_train.empty:
        raise ValueError(f"Zu wenige gültige Zeilen für {target}.")

    n = int(y_train_v.size)
    outer_splits = list(_iter_outer_path_folds(path_train))
    if len(outer_splits) < 2:
        raise ValueError("Zu wenige gültige PATH IDs für Leave-One-Path-Out.")

    _emit(
        progress,
        "cell_start",
        target=target,
        n_train=n,
        n_paths=len(outer_splits),
        n_folds=len(outer_splits),
        learner="polynomial",
        cv="lopo",
        cv_folds=len(outer_splits),
        feature_k_mode="auto",
        feature_k_candidates=list(AUTO_FEATURE_KS),
        poly_degree_max=int(poly_degree_max),
        poly_degrees=_poly_degrees_up_to(poly_degree_max),
    )

    ceiling = reproducibility_ceiling(work_train, target, roles)
    k_candidates = list(AUTO_FEATURE_KS)
    degree_candidates = _poly_degrees_up_to(poly_degree_max)
    history = []
    best = None

    for degree in degree_candidates:
        for k in k_candidates:
            _emit(
                progress,
                "cv_k",
                target=target,
                k=int(k),
                degree=degree,
                n_folds=len(outer_splits),
                cv="lopo",
                feature_k_mode="auto",
            )
            fold_rows = []
            selected_by_fold: dict[str, list[str]] = {}
            oof_true: list[float] = []
            oof_pred: list[float] = []
            oof_id: list[str] = []
            oof_path: list[str] = []
            rmses: list[float] = []

            for held, train_mask, held_mask in outer_splits:
                train_idx = np.flatnonzero(train_mask)
                held_idx = np.flatnonzero(held_mask)
                try:
                    selected, columns, spec = _select_on_frame(
                        work_train.iloc[train_idx],
                        y_train_v[train_idx],
                        feature_cols,
                        k,
                        learner=learner,
                        cv=cv,
                        cv_folds=INNER_CV_FOLDS,
                        groups=None,
                        degree=degree,
                    )
                    if not columns:
                        continue
                    model, fill, input_columns = _fit_selected(
                        work_train.iloc[train_idx],
                        y_train_v[train_idx],
                        selected,
                        columns,
                        spec,
                        learner,
                        cv=cv,
                        cv_folds=INNER_CV_FOLDS,
                    )
                    pred = _predict_selected(
                        model,
                        work_train.iloc[held_idx],
                        input_columns,
                        fill,
                    )
                    y_held = y_train_v[held_idx]
                    rmse, r2 = _fold_scores(y_held, pred)
                except ValueError:
                    continue
                fold_rows.append(
                    {
                        "path_id": held,
                        "rmse": rmse,
                        "r2": r2,
                        "n_held": int(held_idx.size),
                        "n_features": len(columns),
                        "degree": degree,
                    }
                )
                selected_by_fold[held] = list(selected)
                rmses.append(rmse)
                oof_true.extend(float(value) for value in y_held)
                oof_pred.extend(float(value) for value in pred)
                oof_path.extend(str(value) for value in path_train.iloc[held_idx].tolist())
                if id_train is not None:
                    oof_id.extend(str(value) for value in id_train.iloc[held_idx].tolist())
                _emit(
                    progress,
                    "cv_fold",
                    target=target,
                    k=int(k),
                    degree=degree,
                    path_id=held,
                    n_held=int(held_idx.size),
                    n_folds=len(outer_splits),
                    rmse=rmse,
                    r2=r2,
                    n_features=len(columns),
                    cv="lopo",
                )

            if not rmses:
                continue
            mean_rmse = float(np.mean(rmses))
            history.append({"k": int(k), "degree": degree, "mean_rmse": mean_rmse})
            _emit(
                progress,
                "cv_k_done",
                target=target,
                k=int(k),
                degree=degree,
                mean_rmse=mean_rmse,
            )
            record = {
                "k": int(k),
                "degree": degree,
                "mean_rmse": mean_rmse,
                "folds": fold_rows,
                "selected_by_fold": selected_by_fold,
                "oof": {
                    "id": oof_id,
                    "path_id": oof_path,
                    "y_true": oof_true,
                    "y_pred": oof_pred,
                },
            }
            if _is_better_cv(record, best):
                best = record

    if best is None:
        raise ValueError(f"Kein gültiges Modell für {target}.")

    chosen_k = int(best["k"])
    chosen_degree = best.get("degree")
    cv_rmse = best["mean_rmse"]
    _emit(
        progress,
        "cv_k_chosen",
        target=target,
        k=chosen_k,
        degree=chosen_degree,
        mean_rmse=cv_rmse,
        feature_k_mode="auto",
    )

    selected, columns, spec = _select_on_frame(
        work_train,
        y_train_v,
        feature_cols,
        chosen_k,
        learner=learner,
        cv=cv,
        cv_folds=INNER_CV_FOLDS,
        groups=None,
        degree=chosen_degree,
    )
    if not columns:
        raise ValueError(f"Keine Merkmale für das finale Modell von {target}.")
    model, fill, input_columns = _fit_selected(
        work_train,
        y_train_v,
        selected,
        columns,
        spec,
        learner,
        cv=cv,
        cv_folds=INNER_CV_FOLDS,
    )

    _emit(
        progress,
        "fit_final",
        target=target,
        k=chosen_k,
        degree=chosen_degree,
        n_features=len(columns),
        selected=list(selected),
    )
    est = _estimator(model)
    coefficients = _coefficient_map(model, input_columns)
    intercept = _intercept_value(est)

    _emit(
        progress,
        "cell_done",
        target=target,
        k=chosen_k,
        degree=chosen_degree,
        n_features=len(columns),
        mean_cv_rmse=cv_rmse,
        mean_lopo_rmse=cv_rmse,
    )
    return {
        "target": target,
        "k": chosen_k,
        "mean_lopo_rmse": cv_rmse,
        "mean_cv_rmse": cv_rmse,
        "folds": best["folds"],
        "selected": selected,
        "selected_by_fold": best["selected_by_fold"],
        "oof": best["oof"],
        "coefficients": coefficients,
        "intercept": intercept,
        "features": list(input_columns),
        "expanded_features": _expanded_feature_names(model, input_columns),
        "fill": {
            str(key): (
                None
                if value is None or pd.isna(value) or not np.isfinite(float(value))
                else float(value)
            )
            for key, value in fill.items()
        },
        "estimator": model,
        "ceiling": ceiling,
        "k_history": history,
        "n_train": n,
        "learner": "polynomial",
        "cv": "lopo",
        "cv_folds": len(outer_splits),
        "outer_cv": "leave_one_path_out",
        "inner_cv": "random_5fold",
        "feature_k": chosen_k,
        "feature_k_mode": "auto",
        "feature_k_candidates": list(AUTO_FEATURE_KS),
        "polynomial_degree": chosen_degree,
        "poly_degree_max": int(_poly_degrees_up_to(poly_degree_max)[-1]),
    }


def _json_num(value, digits: int = 6):
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(number):
        return None
    return round(number, digits)


def _oof_rows(pack: dict) -> list[dict]:
    ids = pack.get("id") or []
    paths = pack.get("path_id") or []
    ys = pack.get("y_true") or []
    hats = pack.get("y_pred") or []
    count = max(len(ys), len(hats), len(paths), len(ids))
    rows = []
    for index in range(count):
        row: dict = {}
        if index < len(ids) and ids[index]:
            row["id"] = str(ids[index])
        row["path"] = str(paths[index]) if index < len(paths) else ""
        row["y"] = _json_num(ys[index] if index < len(ys) else None)
        row["yhat"] = _json_num(hats[index] if index < len(hats) else None)
        rows.append(row)
    return rows


def _term_rows(coefficients: dict) -> list[dict]:
    rows = [
        {"name": str(name), "coef": _json_num(value)}
        for name, value in (coefficients or {}).items()
    ]
    rows.sort(key=lambda item: abs(item["coef"] or 0.0), reverse=True)
    return rows


def _build_result_json(payload: dict, model_file: str | None) -> dict:
    cells = payload.get("cells") or []
    cell = cells[0] if cells else {}
    oof = cell.get("oof") or {}
    y_true = np.asarray(oof.get("y_true") or [], dtype=float)
    y_pred = np.asarray(oof.get("y_pred") or [], dtype=float)
    scores = _metrics(y_true, y_pred) if y_true.size else {
        "rmse": cell.get("mean_cv_rmse"),
        "mae": None,
        "r2": None,
        "n": 0,
    }
    ceiling = cell.get("ceiling") or {}
    chosen_k = cell.get("k")
    chosen_degree = cell.get("polynomial_degree")
    search = []
    for row in cell.get("k_history") or []:
        item = {
            "degree": row.get("degree"),
            "k": row.get("k"),
            "cv_rmse": _json_num(row.get("mean_rmse")),
        }
        if row.get("k") == chosen_k and row.get("degree") == chosen_degree:
            item["chosen"] = True
        search.append(item)
    folds = []
    for fold in cell.get("folds") or []:
        folds.append(
            {
                "path": fold.get("path_id"),
                "n": fold.get("n_held"),
                "rmse": _json_num(fold.get("rmse")),
                "r2": _json_num(fold.get("r2")),
                "n_terms": fold.get("n_features"),
            }
        )
    terms = _term_rows(cell.get("coefficients") or {})
    report = {
        "trained_at": payload.get("trained_at"),
        "n_train": payload.get("n_train") or cell.get("n_train"),
        "target": cell.get("target"),
        "setup": {
            "learner": "polynomial_elastic_net",
            "outer_cv": "leave_one_path_out",
            "inner_cv": "random_5fold",
            "k_candidates": list(payload.get("feature_k_candidates") or AUTO_FEATURE_KS),
            "degree_max": int(payload.get("poly_degree_max") or cell.get("poly_degree_max") or 1),
            "n_paths": len(folds) or cell.get("cv_folds"),
        },
        "chosen": {
            "k": chosen_k,
            "degree": chosen_degree,
            "n_terms": len(cell.get("selected") or terms),
        },
        "metrics": {
            "cv_rmse": _json_num(scores.get("rmse") if scores.get("rmse") is not None else cell.get("mean_cv_rmse")),
            "cv_mae": _json_num(scores.get("mae")),
            "cv_r2": _json_num(scores.get("r2")),
            "n_oof": int(scores.get("n") or 0),
            "noise_rmse": _json_num(ceiling.get("rmse_noise")),
            "r2_ceiling": _json_num(ceiling.get("r2_ceiling")),
        },
        "intercept": _json_num(cell.get("intercept")),
        "terms": terms,
        "folds": folds,
        "search": search,
        "selected": {
            "final": list(cell.get("selected") or []),
            "by_path": cell.get("selected_by_fold") or {},
        },
        "predictions": _oof_rows(oof),
        "model_file": model_file,
    }
    errors = list(payload.get("errors") or [])
    if errors:
        report["errors"] = errors
    if not cell:
        report.pop("target", None)
        report["chosen"] = None
        report["terms"] = []
        report["folds"] = []
        report["search"] = []
        report["selected"] = {"final": [], "by_path": {}}
        report["predictions"] = []
    return report


def train_grid(
    train_frame: pd.DataFrame,
    roles: dict,
    *,
    targets: list[str],
    learner: str = "polynomial",
    cv: str = "lopo",
    cv_folds: int = 5,
    poly_degree_max: int = POLY_DEGREE_MIN,
    progress=None,
) -> dict:
    cells = []
    errors = []
    planned = list(targets)
    _emit(
        progress,
        "grid_start",
        total=len(planned),
        targets=list(targets),
        n_train=int(train_frame.shape[0]),
        learner="polynomial",
        cv="lopo",
        outer_cv="leave_one_path_out",
        inner_cv="random_5fold",
        feature_k_mode="auto",
        feature_k_candidates=list(AUTO_FEATURE_KS),
        poly_degree_max=int(poly_degree_max),
        poly_degrees=_poly_degrees_up_to(poly_degree_max),
    )
    for index, target in enumerate(planned, start=1):
        _emit(
            progress,
            "cell_index",
            index=index,
            total=len(planned),
            target=target,
        )
        try:
            cells.append(
                train_cell(
                    train_frame,
                    roles,
                    target=target,
                    learner="polynomial",
                    cv=cv,
                    cv_folds=cv_folds,
                    poly_degree_max=poly_degree_max,
                    progress=progress,
                )
            )
        except Exception as exc:
            errors.append({"target": target, "error": str(exc)})
            _emit(
                progress,
                "cell_error",
                index=index,
                total=len(planned),
                target=target,
                error=str(exc),
            )
    _emit(progress, "grid_done", n_cells=len(cells), n_errors=len(errors), total=len(planned))
    return {
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "n_train": int(train_frame.shape[0]),
        "cells": cells,
        "errors": errors,
        "feature_k_candidates": list(AUTO_FEATURE_KS),
        "poly_degree_max": int(_poly_degrees_up_to(poly_degree_max)[-1]),
    }


def save_run(model_dir: Path, payload: dict) -> Path:
    model_dir.mkdir(parents=True, exist_ok=True)
    model_file = None
    kept = []
    for cell in payload.get("cells") or []:
        item = dict(cell)
        estimator = item.pop("estimator", None)
        if estimator is not None:
            bundle = {
                "pipeline": estimator,
                "columns": list(item.get("features") or []),
                "target": item.get("target"),
                "fill": item.get("fill") or {},
                "learner": "polynomial",
                "k": item.get("k"),
                "selected": item.get("selected") or [],
                "trained_at": payload.get("trained_at"),
            }
            model_path = model_dir / "model.joblib"
            joblib.dump(bundle, model_path)
            model_file = model_path.name
        kept.append(item)
    report_payload = dict(payload)
    report_payload["cells"] = kept
    path = model_dir / "result.json"
    path.write_text(
        json.dumps(
            _build_result_json(report_payload, model_file),
            indent=2,
            ensure_ascii=False,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )
    return path
