"""ElasticNet LOPO training on a View-export Excel table. No new experiment values."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import ElasticNetCV, LassoCV, RidgeCV
from sklearn.model_selection import KFold, ShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

TARGET_COLUMNS = ("curvature_x", "curvature_y", "curvature_surface_mean")
CATEGORY_ORDER = ("Zielgröße", "Default", "Pfad", "Weld")
CATEGORY_NAMES = {item.lower() for item in CATEGORY_ORDER}
PATH_IDS = ("ME", "PO", "SO", "SI", "LI")
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
UNPINNABLE_COLUMNS = {
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
    *TARGET_COLUMNS,
}
DEFAULT_COLUMN_NAMES = {
    "COUNT",
    "count",
    "ID",
    "id",
    "PATH ID",
    "path_id",
    "PATH_ID",
    "WFS",
    "WFS [m/min]",
    "wfs",
    "WS",
    "WS [m/min]",
    "ws",
    "SERIES",
    "series",
    "NUMBER",
    "number",
}
STABILITY_ROUNDS = 12
STABILITY_FRACTION = 0.55
AUTO_FEATURE_KS = (8, 12, 16, 20, 24)


def _norm_name(name) -> str:
    if name is None or (isinstance(name, float) and np.isnan(name)):
        return ""
    return str(name).strip()


def _is_category_row(values) -> bool:
    texts = [_norm_name(value) for value in values]
    nonempty = [item for item in texts if item]
    if not nonempty:
        return False
    return all(item.lower() in CATEGORY_NAMES for item in nonempty)


def _forward_fill_categories(values) -> list[str]:
    filled: list[str] = []
    last = ""
    for value in values:
        text = _norm_name(value)
        if text:
            last = text
        filled.append(last)
    return filled


def _infer_category(name: str) -> str:
    if name in TARGET_COLUMNS or name.startswith("curvature_"):
        return "Zielgröße"
    if name in DEFAULT_COLUMN_NAMES:
        return "Default"
    if name in PATH_KERNEL_FIELDS or name.startswith("path_"):
        return "Pfad"
    return "Weld"


def _canonical_category(name: str) -> str:
    lowered = name.lower()
    for item in CATEGORY_ORDER:
        if item.lower() == lowered:
            return item
    return name


def read_export_columns(path: Path) -> tuple[list[dict[str, str]], bool]:
    header = pd.read_excel(path, sheet_name=0, header=None, nrows=2)
    names = [_norm_name(value) for value in header.iloc[0].tolist()]
    raw_categories = header.iloc[1].tolist() if header.shape[0] > 1 else []
    has_categories = _is_category_row(_forward_fill_categories(raw_categories))
    categories = _forward_fill_categories(raw_categories) if has_categories else [""] * len(names)
    columns = []
    for index, name in enumerate(names):
        if not name or name.lower().startswith("unnamed"):
            continue
        category = ""
        if index < len(categories) and categories[index]:
            category = _canonical_category(categories[index])
        if not category:
            category = _infer_category(name)
        columns.append({"name": name, "category": category})
    return columns, has_categories


def is_pinnable_column(name: str, category: str = "") -> bool:
    if category == "Zielgröße":
        return False
    if name in UNPINNABLE_COLUMNS:
        return False
    if any(name.startswith(prefix) for prefix in SKIP_PREFIXES):
        return False
    return bool(name)


def group_columns_by_category(columns: list[dict[str, str]]) -> list[dict]:
    grouped: dict[str, list[str]] = {item: [] for item in CATEGORY_ORDER}
    other: list[str] = []
    for column in columns:
        category = column.get("category") or ""
        name = column.get("name") or ""
        if not name:
            continue
        if category in grouped:
            grouped[category].append(name)
        else:
            other.append(name)

    def pack(category: str, names: list[str]) -> dict:
        return {
            "category": category,
            "allows_constraints": category != "Zielgröße",
            "columns": [
                {"name": name, "pinnable": is_pinnable_column(name, category)}
                for name in names
            ],
        }

    groups = [pack(category, grouped[category]) for category in CATEGORY_ORDER if grouped[category]]
    if other:
        groups.append(pack("Weitere", other))
    return groups


def resolve_training_target(columns: list[dict], roles: dict) -> str:
    named = [item.get("name") or "" for item in columns if item.get("category") == "Zielgröße"]
    named = [name for name in named if name]
    if len(named) == 1:
        return named[0]
    if len(named) > 1:
        raise ValueError(
            "Mehrere Zielgrößen in den Daten: "
            + ", ".join(named)
            + ". Bitte nur eine Zielgröße exportieren."
        )
    targets = [name for name in (roles.get("targets") or []) if name]
    if len(targets) == 1:
        return targets[0]
    if len(targets) > 1:
        raise ValueError(
            "Mehrere Zielgrößen in den Daten: "
            + ", ".join(targets)
            + ". Bitte nur eine Zielgröße exportieren."
        )
    raise ValueError("Keine Zielgröße in train.xlsx.")


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
    targets = [name for name in names if name in TARGET_COLUMNS]
    group = next((name for name in GROUP_CANDIDATES if name in names), None)
    experiment_id = next((name for name in ID_CANDIDATES if name in names), None)
    skip = set(SKIP_COLUMNS)
    skip.update(targets)
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


def _inner_cv(n_samples: int) -> int:
    return max(2, min(5, max(n_samples // 6, 2)))


def _fit_learner(x: np.ndarray, y: np.ndarray, learner: str = "elasticnet") -> Pipeline:
    inner = _inner_cv(x.shape[0])
    name = "enet"
    if learner == "ridge":
        name = "ridge"
        estimator = RidgeCV(alphas=np.logspace(-3, 3, 13), cv=inner)
    elif learner == "lasso":
        name = "lasso"
        estimator = LassoCV(cv=inner, max_iter=20000, random_state=0)
    else:
        estimator = ElasticNetCV(
            l1_ratio=[0.2, 0.5, 0.8],
            cv=inner,
            max_iter=20000,
            random_state=0,
        )
    model = Pipeline([("scale", StandardScaler()), (name, estimator)])
    model.fit(x, y)
    return model


def _estimator(model: Pipeline):
    return model.steps[-1][1]


def stability_select(
    x: pd.DataFrame,
    y: np.ndarray,
    candidates: list[str],
    learner: str = "elasticnet",
) -> list[str]:
    if not candidates:
        return []
    n = x.shape[0]
    if n < 8 or len(candidates) <= 2:
        return list(candidates)
    counts = {name: 0 for name in candidates}
    rng = np.random.default_rng(0)
    take = max(6, int(round(n * 0.8)))
    for _ in range(STABILITY_ROUNDS):
        index = rng.choice(n, size=take, replace=False)
        subset = x.iloc[index].loc[:, candidates]
        filled = subset.fillna(subset.median(numeric_only=True))
        y_sub = y[index]
        if not np.all(np.isfinite(y_sub)):
            continue
        try:
            model = _fit_learner(filled.to_numpy(dtype=float), y_sub, learner)
        except ValueError:
            continue
        coef = np.asarray(_estimator(model).coef_, dtype=float)
        for name, value in zip(candidates, coef):
            if abs(float(value)) > 1e-12:
                counts[name] += 1
    kept = [name for name in candidates if counts[name] / STABILITY_ROUNDS >= STABILITY_FRACTION]
    return kept or list(candidates[: min(6, len(candidates))])


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
    pinned: list[str] | None = None,
    min_per_category: dict[str, int] | None = None,
    column_categories: dict[str, str] | None = None,
    learner: str = "elasticnet",
) -> tuple[list[str], list[str]]:
    pinned_cols = [name for name in (pinned or []) if name in work.columns]
    pool = list(dict.fromkeys(list(feature_cols) + pinned_cols))
    x_raw, _ = _design(work, pool)
    kept = variance_filter(x_raw)
    forced = [name for name in pinned_cols if name in x_raw.columns]
    eligible = list(dict.fromkeys(forced + kept))
    if not eligible:
        return [], []

    x_var = x_raw.loc[:, [name for name in eligible if name in x_raw.columns]]
    ranked = fcq_mrmr(x_var, y, len(x_var.columns))
    free = [name for name in ranked if name not in forced]
    k_total = max(0, int(k))
    k_free = max(0, min(k_total - len(forced), len(free)))
    ranked_free = free[:k_free] if k_free else []
    selected = stability_select(x_var, y, ranked_free, learner=learner) if ranked_free else []
    selected = list(dict.fromkeys(forced + selected))

    categories = column_categories or {}
    for category, raw_min in (min_per_category or {}).items():
        try:
            minimum = int(raw_min)
        except (TypeError, ValueError):
            continue
        if minimum <= 0:
            continue
        members = [
            name
            for name in eligible
            if categories.get(name) == category and is_pinnable_column(name, category)
        ]
        if not members:
            continue
        have = [name for name in selected if name in members]
        need = min(minimum, len(members)) - len(have)
        if need <= 0:
            continue
        for name in ranked:
            if need <= 0:
                break
            if name in members and name not in selected:
                selected.append(name)
                need -= 1

    columns = list(dict.fromkeys(selected))
    return selected, columns


def _iter_cv_splits(
    n: int,
    groups: pd.Series | None,
    cv: str,
    cv_folds: int,
):
    if cv == "lopo" and groups is not None:
        unique = [item for item in sorted(groups.unique()) if item and str(item) != "NAN"]
        if len(unique) >= 2:
            values = groups.to_numpy()
            for held in unique:
                train_mask = values != held
                held_mask = values == held
                if np.any(train_mask) and np.any(held_mask):
                    yield str(held), train_mask, held_mask
            return
    folds = max(2, min(int(cv_folds), max(n, 2)))
    if n < 4:
        return
    folds = min(folds, n)
    if cv == "random":
        splitter = ShuffleSplit(n_splits=folds, test_size=max(1.0 / folds, 1.0 / n), random_state=0)
    else:
        splitter = KFold(n_splits=folds, shuffle=True, random_state=0)
    index = np.arange(n)
    for i, (train_idx, held_idx) in enumerate(splitter.split(index), start=1):
        train_mask = np.zeros(n, dtype=bool)
        held_mask = np.zeros(n, dtype=bool)
        train_mask[train_idx] = True
        held_mask[held_idx] = True
        yield str(i), train_mask, held_mask


def _emit(progress, event: str, **data) -> None:
    if progress is None:
        return
    progress(event, **data)


def train_cell(
    train_frame: pd.DataFrame,
    roles: dict,
    *,
    target: str,
    pinned: list[str] | None = None,
    min_per_category: dict[str, int] | None = None,
    column_categories: dict[str, str] | None = None,
    learner: str = "elasticnet",
    cv: str = "lopo",
    cv_folds: int = 5,
    feature_k: int = 16,
    feature_k_mode: str = "manual",
    progress=None,
) -> dict:
    if target not in train_frame.columns:
        raise ValueError(f"Zielspalte fehlt in den Trainingsdaten: {target}")

    y_train = pd.to_numeric(train_frame[target], errors="coerce")
    feature_cols = list(roles.get("features") or [])
    groups_train = _try_group_values(train_frame, roles)

    train_ok = y_train.notna()
    if groups_train is not None:
        train_ok = train_ok & groups_train.ne("") & groups_train.ne("NAN")
    work_train = train_frame.loc[train_ok].copy()
    y_train_v = y_train.loc[train_ok].to_numpy(dtype=float)
    if groups_train is not None:
        groups_train = groups_train.loc[train_ok]

    if work_train.empty:
        raise ValueError(f"Zu wenige gültige Zeilen für {target}.")

    _emit(
        progress,
        "cell_start",
        target=target,
        n_train=int(y_train_v.size),
        learner=learner,
        cv=cv,
        cv_folds=int(cv_folds),
        feature_k=int(feature_k),
        feature_k_mode=feature_k_mode,
    )

    ceiling = reproducibility_ceiling(work_train, target, roles)
    splits = list(_iter_cv_splits(int(y_train_v.size), groups_train, cv, cv_folds))
    auto_k = str(feature_k_mode).strip().lower() == "auto"
    k_candidates = list(AUTO_FEATURE_KS) if auto_k else [max(1, int(feature_k))]
    chosen_k = k_candidates[0]
    best = None
    history = []
    if splits:
        for k in k_candidates:
            _emit(
                progress,
                "cv_k",
                target=target,
                k=int(k),
                n_folds=len(splits),
                cv=cv,
                feature_k_mode="auto" if auto_k else "manual",
            )
            fold_rows = []
            oof_true = []
            oof_pred = []
            oof_group = []
            selected_by_fold = {}
            mean_rmse = None
            try:
                for fold_name, train_mask, held_mask in splits:
                    selected, columns = _select_on_frame(
                        work_train.iloc[np.where(train_mask)[0]],
                        y_train_v[train_mask],
                        feature_cols,
                        k,
                        pinned=pinned,
                        min_per_category=min_per_category,
                        column_categories=column_categories,
                        learner=learner,
                    )
                    if not columns:
                        continue
                    x_tr, x_held = _train_test_design(
                        work_train.iloc[np.where(train_mask)[0]],
                        work_train.iloc[np.where(held_mask)[0]],
                        columns,
                    )
                    model = _fit_learner(x_tr.to_numpy(dtype=float), y_train_v[train_mask], learner)
                    pred = model.predict(x_held.to_numpy(dtype=float))
                    fold_metrics = _metrics(y_train_v[held_mask], pred)
                    _emit(
                        progress,
                        "cv_fold",
                        target=target,
                        k=int(k),
                        path_id=fold_name,
                        rmse=fold_metrics.get("rmse"),
                        r2=fold_metrics.get("r2"),
                        n_features=len(selected),
                        n_folds=len(splits),
                    )
                    fold_rows.append({"path_id": fold_name, **fold_metrics, "features": selected})
                    selected_by_fold[fold_name] = selected
                    oof_true.extend(y_train_v[held_mask].tolist())
                    oof_pred.extend(np.asarray(pred, dtype=float).tolist())
                    oof_group.extend([fold_name] * int(np.count_nonzero(held_mask)))
                if not fold_rows:
                    continue
                mean_rmse = float(
                    np.nanmean([row["rmse"] for row in fold_rows if row.get("rmse") is not None])
                )
            except ValueError:
                continue
            record = {
                "k": k,
                "mean_rmse": mean_rmse,
                "folds": fold_rows,
                "selected_by_fold": selected_by_fold,
                "oof": {"y_true": oof_true, "y_pred": oof_pred, "path_id": oof_group},
            }
            history.append({"k": k, "mean_rmse": mean_rmse})
            _emit(
                progress,
                "cv_k_done",
                target=target,
                k=int(k),
                mean_rmse=mean_rmse,
            )
            if best is None:
                best = record
            elif mean_rmse is not None and (
                best["mean_rmse"] is None
                or mean_rmse < best["mean_rmse"]
                or (mean_rmse == best["mean_rmse"] and k < best["k"])
            ):
                best = record
        if best is not None:
            chosen_k = int(best["k"])
            _emit(
                progress,
                "cv_k_chosen",
                target=target,
                k=chosen_k,
                mean_rmse=best["mean_rmse"],
                feature_k_mode="auto" if auto_k else "manual",
            )

    selected, columns = _select_on_frame(
        work_train,
        y_train_v,
        feature_cols,
        chosen_k,
        pinned=pinned,
        min_per_category=min_per_category,
        column_categories=column_categories,
        learner=learner,
    )
    if not columns:
        raise ValueError(f"Kein gültiges Modell für {target}.")

    _emit(
        progress,
        "fit_final",
        target=target,
        k=chosen_k,
        n_features=len(columns),
        selected=list(selected),
    )
    x_train, fill = _design(work_train, columns)
    model = _fit_learner(x_train.to_numpy(dtype=float), y_train_v, learner)
    est = _estimator(model)
    coef = np.asarray(est.coef_, dtype=float)
    intercept = float(est.intercept_)
    cv_rmse = None if best is None else best["mean_rmse"]

    _emit(
        progress,
        "cell_done",
        target=target,
        k=chosen_k,
        n_features=len(columns),
        mean_cv_rmse=cv_rmse,
    )
    return {
        "target": target,
        "k": chosen_k,
        "mean_lopo_rmse": cv_rmse,
        "mean_cv_rmse": cv_rmse,
        "folds": [] if best is None else best["folds"],
        "selected": selected,
        "selected_by_fold": {} if best is None else best["selected_by_fold"],
        "oof": {} if best is None else best["oof"],
        "coefficients": {name: float(value) for name, value in zip(columns, coef)},
        "intercept": intercept,
        "features": list(columns),
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
        "pinned": [name for name in (pinned or []) if name in columns],
        "n_train": int(y_train_v.size),
        "learner": learner,
        "cv": cv,
        "cv_folds": int(cv_folds),
        "feature_k": int(feature_k),
        "feature_k_mode": "auto" if str(feature_k_mode).strip().lower() == "auto" else "manual",
    }


def _falsification(frame: pd.DataFrame, roles: dict, cells: list[dict]) -> list[dict]:
    tests = []
    groups = None
    if roles.get("group") and roles["group"] in frame.columns:
        groups = frame[roles["group"]].astype(str).str.strip().str.upper()
    names = [_norm_name(col) for col in frame.columns]
    shrink = [name for name in ("path_A", "path_Bx", "path_By") if name in names]
    hotspot = [name for name in ("path_D_mean", "path_D_95") if name in names]

    def mean_for(path_id: str, columns: list[str]) -> dict[str, float] | None:
        if groups is None or not columns:
            return None
        subset = frame.loc[groups.eq(path_id), columns]
        if subset.empty:
            return None
        numeric = subset.apply(pd.to_numeric, errors="coerce")
        return {col: float(numeric[col].mean()) for col in columns if numeric[col].notna().any()}

    si_shrink = mean_for("SI", shrink)
    so_shrink = mean_for("SO", shrink)
    si_hot = mean_for("SI", hotspot)
    so_hot = mean_for("SO", hotspot)
    tests.append(
        {
            "id": "si_so_shrink",
            "title": "SI gegen SO, Schrumpf path_A/Bx/By",
            "expected": "Polylinie gleich, Hotspot-Gewichtung kann SI und SO unterscheiden.",
            "si": si_shrink,
            "so": so_shrink,
        }
    )
    tests.append(
        {
            "id": "si_so_hotspot",
            "title": "SI gegen SO, Hotspot path_D",
            "expected": "Hotspot-Statistik von SI und SO unterscheidet sich (umgekehrte Reihenfolge).",
            "si": si_hot,
            "so": so_hot,
        }
    )
    li_shrink = mean_for("LI", shrink)
    tests.append(
        {
            "id": "li_so_fill",
            "title": "LI-Präfix gegen SO",
            "expected": "LI hat durch die Füllung größeres path_A als SO.",
            "li": li_shrink,
            "so": so_shrink,
        }
    )

    for cell in cells:
        pack = cell.get("oof") or {}
        path_ids = pack.get("path_id") or []
        preds = pack.get("y_pred") or []
        if not path_ids:
            continue
        by_path: dict[str, list[float]] = {}
        for path_id, pred in zip(path_ids, preds):
            by_path.setdefault(str(path_id), []).append(float(pred))
        tests.append(
            {
                "id": f"cv_{cell['target']}_si_so",
                "title": f"CV-Vorhersage {cell['target']} SI gegen SO",
                "si_mean": float(np.mean(by_path["SI"])) if "SI" in by_path else None,
                "so_mean": float(np.mean(by_path["SO"])) if "SO" in by_path else None,
            }
        )
    return tests


def train_grid(
    train_frame: pd.DataFrame,
    roles: dict,
    *,
    targets: list[str],
    pinned: list[str] | None = None,
    min_per_category: dict[str, int] | None = None,
    column_categories: dict[str, str] | None = None,
    learner: str = "elasticnet",
    cv: str = "lopo",
    cv_folds: int = 5,
    feature_k: int = 16,
    feature_k_mode: str = "manual",
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
        learner=learner,
        cv=cv,
        cv_folds=int(cv_folds),
        feature_k=int(feature_k),
        feature_k_mode=feature_k_mode,
        pinned=list(pinned or []),
        min_per_category=dict(min_per_category or {}),
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
                    pinned=pinned,
                    min_per_category=min_per_category,
                    column_categories=column_categories,
                    learner=learner,
                    cv=cv,
                    cv_folds=cv_folds,
                    feature_k=feature_k,
                    feature_k_mode=feature_k_mode,
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
    comparison = []
    for cell in cells:
        comparison.append(
            {
                "target": cell["target"],
                "k": cell["k"],
                "mean_lopo_rmse": cell["mean_lopo_rmse"],
                "mean_cv_rmse": cell.get("mean_cv_rmse"),
                "r2_ceiling": (cell.get("ceiling") or {}).get("r2_ceiling"),
                "rmse_noise": (cell.get("ceiling") or {}).get("rmse_noise"),
                "n_train": cell.get("n_train"),
            }
        )
    combined = train_frame.copy()
    return {
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "n_train": int(train_frame.shape[0]),
        "roles": {key: value for key, value in roles.items() if key != "selected_by_fold"},
        "cells": cells,
        "comparison": comparison,
        "errors": errors,
        "falsification": _falsification(combined, roles, cells),
        "pinned": list(pinned or []),
        "min_per_category": dict(min_per_category or {}),
        "learner": learner,
        "cv": cv,
        "cv_folds": int(cv_folds),
        "feature_k": int(feature_k),
        "feature_k_mode": "auto" if str(feature_k_mode).strip().lower() == "auto" else "manual",
    }


def save_run(model_dir: Path, payload: dict) -> Path:
    model_dir.mkdir(parents=True, exist_ok=True)
    cells = []
    model_file = None
    for cell in payload.get("cells") or []:
        item = dict(cell)
        estimator = item.pop("estimator", None)
        if estimator is not None:
            bundle = {
                "pipeline": estimator,
                "columns": list(item.get("features") or []),
                "target": item.get("target"),
                "fill": item.get("fill") or {},
                "learner": item.get("learner") or payload.get("learner"),
                "k": item.get("k"),
                "pinned": item.get("pinned") or [],
                "selected": item.get("selected") or [],
                "metrics": item.get("metrics"),
                "trained_at": payload.get("trained_at"),
            }
            model_path = model_dir / "model.joblib"
            joblib.dump(bundle, model_path)
            model_file = model_path.name
            item["model_file"] = model_file
        cells.append(item)
    out = dict(payload)
    out["cells"] = cells
    if model_file:
        out["model_file"] = model_file
    path = model_dir / "result.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    return path
