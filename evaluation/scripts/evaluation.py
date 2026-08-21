"""Flask app for evaluation — trains ElasticNet A/B/C from train/test View-exports."""

from __future__ import annotations

import json
import math
import os
import re
import sys
import threading
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

BASE_DIR = Path(__file__).resolve().parent.parent.parent
EVALUATION_DIR = BASE_DIR / "evaluation"
SCRIPTS_DIR = EVALUATION_DIR / "scripts"
TEMPLATES_DIR = EVALUATION_DIR / "templates"
DEFAULT_DATA_DIR = BASE_DIR / "data"
EVALUATION_DATA_DIR_NAME = "evaluation"
EVALUATION_PORT = int(os.environ.get("EVALUATION_PORT", "5002"))
TRAIN_FILENAME = "train.xlsx"
TEST_FILENAME = "test.xlsx"
RESULT_FILENAME = "result.json"
SELECTION_FILENAME = "selection.json"
TRAIN_LOG_FILENAME = "train.log"
TRAIN_STATUS_FILENAME = "train_status.json"
LOG_TAIL_LIMIT = 80
LEARNER_OPTIONS = (
    ("elasticnet", "Elastic Net"),
    ("ridge", "Ridge"),
    ("lasso", "Lasso"),
)
CV_OPTIONS = (
    ("lopo", "Leave-One-Path-Out"),
    ("kfold", "k-Fold"),
    ("random", "Random Fold"),
)
DEFAULT_LEARNER = "elasticnet"
DEFAULT_CV = "lopo"
DEFAULT_CV_FOLDS = 5
DEFAULT_FEATURE_K = 16
DEFAULT_FEATURE_K_MODE = "manual"
FEATURE_K_MIN = 1
FEATURE_K_MAX = 200
FEATURE_K_MODES = ("manual", "auto")
LEARNER_IDS = {item for item, _label in LEARNER_OPTIONS}
CV_IDS = {item for item, _label in CV_OPTIONS}

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from run_model import (
    group_columns_by_category,
    load_dataset,
    read_export_columns,
    resolve_training_target,
    save_run,
    train_grid,
)

app = Flask(__name__, template_folder=str(TEMPLATES_DIR))

data_dir: Path | None = None
EVALUATION_ROOT = DEFAULT_DATA_DIR / EVALUATION_DATA_DIR_NAME
ACTIVE_MODEL_DIR: Path | None = None
_train_lock = threading.Lock()
_train_thread: threading.Thread | None = None
_train_model_dir: Path | None = None
_train_run_id: str | None = None


def _evaluation_root(root: Path) -> Path:
    return root / EVALUATION_DATA_DIR_NAME


def _set_data_dir(root: Path) -> None:
    global data_dir, EVALUATION_ROOT
    data_dir = root
    EVALUATION_ROOT = _evaluation_root(root)
    EVALUATION_ROOT.mkdir(parents=True, exist_ok=True)


def _try_load_default_data_dir() -> None:
    if DEFAULT_DATA_DIR.is_dir():
        _set_data_dir(DEFAULT_DATA_DIR)


def _sanitize_model_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", str(name).strip())
    cleaned = cleaned.strip("._")
    return cleaned[:64]


def _resolve_model_dir(raw: str) -> Path:
    text = raw.strip().strip('"')
    path = Path(text)
    if not path.parts:
        return path
    if len(path.parts) == 1:
        named = _model_dir_from_name(text)
        if named is not None:
            return named.resolve()
    if not path.is_absolute():
        path = (BASE_DIR / path).resolve()
    else:
        path = path.resolve()
    return path


def _list_model_dirs() -> list[Path]:
    if not EVALUATION_ROOT.is_dir():
        return []
    return sorted(
        [entry for entry in EVALUATION_ROOT.iterdir() if entry.is_dir() and not entry.name.startswith(".")],
        key=lambda item: item.name.lower(),
    )


def _model_dir_from_name(name: str) -> Path | None:
    cleaned = _sanitize_model_name(name)
    if not cleaned:
        return None
    return EVALUATION_ROOT / cleaned


def _empty_selection() -> dict:
    return {
        "pinned": [],
        "min_per_category": {},
        "learner": DEFAULT_LEARNER,
        "cv": DEFAULT_CV,
        "cv_folds": DEFAULT_CV_FOLDS,
        "feature_k": DEFAULT_FEATURE_K,
        "feature_k_mode": DEFAULT_FEATURE_K_MODE,
    }


def _normalize_selection(raw) -> dict:
    payload = raw if isinstance(raw, dict) else {}
    pinned = []
    for item in payload.get("pinned") or []:
        name = str(item).strip()
        if name and name not in pinned:
            pinned.append(name)
    mins: dict[str, int] = {}
    raw_mins = payload.get("min_per_category") or {}
    if isinstance(raw_mins, dict):
        for key, value in raw_mins.items():
            category = str(key).strip()
            try:
                number = int(value)
            except (TypeError, ValueError):
                continue
            if category:
                mins[category] = max(0, number)
    learner = str(payload.get("learner") or DEFAULT_LEARNER).strip().lower()
    if learner not in LEARNER_IDS:
        learner = DEFAULT_LEARNER
    cv = str(payload.get("cv") or DEFAULT_CV).strip().lower()
    if cv not in CV_IDS:
        cv = DEFAULT_CV
    try:
        cv_folds = int(payload.get("cv_folds") or DEFAULT_CV_FOLDS)
    except (TypeError, ValueError):
        cv_folds = DEFAULT_CV_FOLDS
    cv_folds = min(20, max(2, cv_folds))
    try:
        feature_k = int(payload.get("feature_k") or DEFAULT_FEATURE_K)
    except (TypeError, ValueError):
        feature_k = DEFAULT_FEATURE_K
    feature_k = min(FEATURE_K_MAX, max(FEATURE_K_MIN, feature_k))
    feature_k_mode = str(payload.get("feature_k_mode") or DEFAULT_FEATURE_K_MODE).strip().lower()
    if feature_k_mode not in FEATURE_K_MODES:
        feature_k_mode = DEFAULT_FEATURE_K_MODE
    return {
        "pinned": pinned,
        "min_per_category": mins,
        "learner": learner,
        "cv": cv,
        "cv_folds": cv_folds,
        "feature_k": feature_k,
        "feature_k_mode": feature_k_mode,
    }


def _selection_path(model_dir: Path) -> Path:
    return model_dir / SELECTION_FILENAME


def _load_selection(model_dir: Path) -> dict:
    path = _selection_path(model_dir)
    if not path.is_file():
        return _empty_selection()
    try:
        return _normalize_selection(json.loads(path.read_text(encoding="utf-8")))
    except Exception:
        return _empty_selection()


def _save_selection(model_dir: Path, payload: dict) -> dict:
    selection = _normalize_selection(payload)
    _selection_path(model_dir).write_text(
        json.dumps(selection, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return selection


def _fmt_num(value, digits: int = 4) -> str:
    if value is None:
        return "–"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return "–"
    return f"{number:.{digits}g}"


def _elapsed_s(started_at: str | None) -> float | None:
    if not started_at:
        return None
    try:
        started = datetime.fromisoformat(started_at)
    except ValueError:
        return None
    return max(0.0, (datetime.now() - started).total_seconds())


def _empty_train_status() -> dict:
    return {
        "state": "idle",
        "phase": "Bereit",
        "message": "Noch kein Training gestartet.",
        "progress": {"current": 0, "total": 0, "unit": ""},
        "current": {"target": None, "k": None, "fold": None},
        "last_metrics": None,
        "started_at": None,
        "finished_at": None,
        "elapsed_s": None,
        "log_file": TRAIN_LOG_FILENAME,
        "log_tail": [],
        "error": None,
        "run_id": None,
        "completed": [],
    }


def _train_status_path(model_dir: Path) -> Path:
    return model_dir / TRAIN_STATUS_FILENAME


def _train_log_path(model_dir: Path) -> Path:
    return model_dir / TRAIN_LOG_FILENAME


def _read_log_tail(model_dir: Path, limit: int = LOG_TAIL_LIMIT) -> list[str]:
    path = _train_log_path(model_dir)
    if not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return lines[-limit:]


def _read_train_status_file(model_dir: Path) -> dict:
    path = _train_status_path(model_dir)
    if not path.is_file():
        status = _empty_train_status()
        status["log_tail"] = _read_log_tail(model_dir)
        return status
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        status = _empty_train_status()
        status["log_tail"] = _read_log_tail(model_dir)
        return status
    status = _empty_train_status()
    if isinstance(payload, dict):
        status.update(payload)
    status["log_file"] = TRAIN_LOG_FILENAME
    status["log_tail"] = _read_log_tail(model_dir)
    return status


def _write_train_status(model_dir: Path, status: dict) -> None:
    payload = deepcopy(status)
    payload.pop("log_tail", None)
    path = _train_status_path(model_dir)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def _append_train_log(model_dir: Path, line: str) -> None:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = f"[{stamp}] {line}"
    path = _train_log_path(model_dir)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text + "\n")


def _event_line(event: str, data: dict) -> str | None:
    target = data.get("target")
    if event == "run_start":
        mins = data.get("min_per_category") or {}
        min_text = ", ".join(f"{key}≥{value}" for key, value in mins.items() if value) or "keine"
        pinned = ", ".join(data.get("pinned") or []) or "keine"
        cv = data.get("cv")
        folds = f", {data.get('cv_folds')} Folds" if cv in {"kfold", "random"} else ""
        k_text = (
            "Kennwerte=auto (8/12/16/20/24)"
            if data.get("feature_k_mode") == "auto"
            else f"Kennwerte={data.get('feature_k')}"
        )
        return (
            f"Lauf {data.get('run_id')}: Ziel {target}, "
            f"n_train={data.get('n_train')}, "
            f"Learner={data.get('learner')}, CV={cv}{folds}, "
            f"{k_text}, fest: {pinned}, min.: {min_text}"
        )
    if event == "grid_start":
        return None
    if event == "cell_index":
        return f"Trainiere {target}"
    if event == "cell_start":
        return (
            f"Starte {target} (n_train={data.get('n_train')}, "
            f"Learner={data.get('learner')}, CV={data.get('cv')})"
        )
    if event == "cv_k":
        n_folds = data.get("n_folds") or data.get("n_paths")
        return f"Kreuzvalidierung {target}: k={data.get('k')} über {n_folds} Folds"
    if event == "cv_fold":
        return (
            f"Fold {data.get('path_id')} bei k={data.get('k')}: "
            f"RMSE={_fmt_num(data.get('rmse'))}, R²={_fmt_num(data.get('r2'))}, "
            f"{data.get('n_features')} Merkmale"
        )
    if event == "cv_k_done":
        return f"k={data.get('k')} abgeschlossen, mittlere CV-RMSE={_fmt_num(data.get('mean_rmse'))}"
    if event == "cv_k_chosen":
        mode = "automatisch" if data.get("feature_k_mode") == "auto" else "manuell"
        return (
            f"Gewählte Kennwerte: {data.get('k')} ({mode}), "
            f"CV-RMSE={_fmt_num(data.get('mean_rmse'))}"
        )
    if event == "fit_final":
        selected = data.get("selected") or []
        names = ", ".join(str(item) for item in selected) if selected else "keine"
        return (
            f"Finales Fit {target}: k={data.get('k')}, "
            f"{data.get('n_features')} Merkmale: {names}"
        )
    if event == "cell_done":
        return (
            f"Fertig {target}: k={data.get('k')}, "
            f"CV-RMSE={_fmt_num(data.get('mean_cv_rmse') or data.get('mean_lopo_rmse'))}"
        )
    if event == "cell_error":
        return f"Fehler {target}: {data.get('error')}"
    if event == "grid_done":
        if data.get("n_errors"):
            return f"Training mit {data.get('n_errors')} Fehler(n) beendet"
        return None
    if event == "run_done":
        return f"Training abgeschlossen in {_fmt_num(data.get('elapsed_s'), 3)} s → {RESULT_FILENAME}, model.joblib"
    if event == "run_error":
        return f"Training fehlgeschlagen: {data.get('error')}"
    return None


def _apply_train_event(status: dict, event: str, data: dict) -> dict:
    current = dict(status.get("current") or {})
    progress = dict(status.get("progress") or {"current": 0, "total": 0})
    if event == "run_start":
        status["state"] = "running"
        status["phase"] = "Vorbereitung"
        status["message"] = "Training gestartet."
        progress["total"] = 0
        progress["current"] = 0
        progress["unit"] = ""
        status["error"] = None
        status["completed"] = []
        status["last_metrics"] = None
        current["target"] = data.get("target")
    elif event == "grid_start":
        status["state"] = "running"
        status["phase"] = "Vorbereitung"
        current["target"] = (data.get("targets") or [None])[0]
    elif event == "cell_index":
        status["state"] = "running"
        status["phase"] = "Modell"
        status["message"] = str(data.get("target") or "Training")
        current["target"] = data.get("target")
        current["k"] = None
        current["fold"] = None
    elif event == "cell_start":
        status["phase"] = "Modell"
        status["message"] = (
            f"{data.get('target')} ({data.get('n_train')} Zeilen)"
        )
        current["target"] = data.get("target")
    elif event == "cv_k":
        status["phase"] = "Kreuzvalidierung"
        status["message"] = f"k={data.get('k')} · {data.get('n_folds')} Folds"
        current["k"] = data.get("k")
        current["fold"] = None
        progress["current"] = 0
        progress["total"] = int(data.get("n_folds") or 0)
        progress["unit"] = "Folds"
    elif event == "cv_fold":
        status["phase"] = "Kreuzvalidierung"
        status["message"] = (
            f"Fold {data.get('path_id')} · k={data.get('k')} · RMSE={_fmt_num(data.get('rmse'))}"
        )
        current["k"] = data.get("k")
        current["fold"] = data.get("path_id")
        progress["current"] = int(progress.get("current") or 0) + 1
        progress["total"] = int(data.get("n_folds") or progress.get("total") or 0)
        progress["unit"] = "Folds"
    elif event == "cv_k_done":
        status["phase"] = "Kreuzvalidierung"
        status["message"] = f"k={data.get('k')} · mittlere RMSE={_fmt_num(data.get('mean_rmse'))}"
        current["k"] = data.get("k")
    elif event == "cv_k_chosen":
        status["phase"] = "Kennwerte"
        status["message"] = (
            f"Gewählt: {data.get('k')} Kennwerte · CV-RMSE={_fmt_num(data.get('mean_rmse'))}"
        )
        current["k"] = data.get("k")
        current["fold"] = None
    elif event == "fit_final":
        status["phase"] = "Finales Fit"
        status["message"] = f"k={data.get('k')} · {data.get('n_features')} Merkmale"
        current["k"] = data.get("k")
        current["fold"] = None
        progress["current"] = 1
        progress["total"] = 1
        progress["unit"] = ""
    elif event == "cell_done":
        status["phase"] = "Fertig"
        status["message"] = (
            f"{data.get('target')}: CV-RMSE={_fmt_num(data.get('mean_cv_rmse') or data.get('mean_lopo_rmse'))}"
        )
        status["last_metrics"] = {
            "target": data.get("target"),
            "k": data.get("k"),
            "mean_cv_rmse": data.get("mean_cv_rmse") or data.get("mean_lopo_rmse"),
        }
        completed = list(status.get("completed") or [])
        completed.append(status["last_metrics"])
        status["completed"] = completed
        current["k"] = data.get("k")
        current["fold"] = None
    elif event == "cell_error":
        status["phase"] = "Fehler"
        status["message"] = f"{data.get('target')}: {data.get('error')}"
        status["error"] = data.get("error")
        completed = list(status.get("completed") or [])
        completed.append(
            {
                "target": data.get("target"),
                "error": data.get("error"),
            }
        )
        status["completed"] = completed
    elif event == "grid_done":
        status["phase"] = "Abschluss"
        status["message"] = (
            f"{data.get('n_cells')} Modelle fertig, {data.get('n_errors')} Fehler"
        )
        progress["current"] = int(data.get("total") or progress.get("current") or 0)
        progress["total"] = int(data.get("total") or progress.get("total") or 0)
    elif event == "run_done":
        status["state"] = "done"
        status["phase"] = "Fertig"
        status["message"] = "Training abgeschlossen."
        status["finished_at"] = datetime.now().isoformat(timespec="seconds")
        status["error"] = None
    elif event == "run_error":
        status["state"] = "error"
        status["phase"] = "Fehler"
        status["message"] = str(data.get("error") or "Training fehlgeschlagen.")
        status["error"] = data.get("error")
        status["finished_at"] = datetime.now().isoformat(timespec="seconds")
    status["current"] = current
    status["progress"] = progress
    status["elapsed_s"] = _elapsed_s(status.get("started_at"))
    return status


def _emit_train_event(model_dir: Path, status: dict, event: str, **data) -> dict:
    line = _event_line(event, data)
    if line:
        _append_train_log(model_dir, line)
    status = _apply_train_event(status, event, data)
    _write_train_status(model_dir, status)
    return status


def _live_training() -> tuple[bool, Path | None, str | None]:
    with _train_lock:
        thread = _train_thread
        model_dir = _train_model_dir
        run_id = _train_run_id
        alive = thread is not None and thread.is_alive()
    return alive, model_dir, run_id


def _public_train_status(model_dir: Path | None) -> dict:
    if model_dir is None or not model_dir.is_dir():
        return _empty_train_status()
    status = _read_train_status_file(model_dir)
    alive, live_dir, live_run = _live_training()
    live_here = (
        alive
        and live_dir is not None
        and live_dir.resolve() == model_dir.resolve()
    )
    if live_here:
        status["state"] = "running"
        if status.get("run_id") != live_run:
            status["run_id"] = live_run
            status["phase"] = status.get("phase") or "Start"
            status["message"] = "Training läuft."
            status["error"] = None
        status["elapsed_s"] = _elapsed_s(status.get("started_at"))
    elif status.get("state") == "running":
        status["state"] = "error"
        status["phase"] = "Unterbrochen"
        status["message"] = "Training wurde unterbrochen (Server-Neustart)."
        if not status.get("error"):
            status["error"] = "unterbrochen"
        if not status.get("finished_at"):
            status["finished_at"] = datetime.now().isoformat(timespec="seconds")
    return status


def _run_training_job(
    model_dir: Path,
    run_id: str,
    target: str,
) -> None:
    global _train_thread, _train_model_dir, _train_run_id
    existing = _read_train_status_file(model_dir)
    if existing.get("run_id") == run_id:
        status = existing
        status.pop("log_tail", None)
    else:
        status = _empty_train_status()
        status["started_at"] = datetime.now().isoformat(timespec="seconds")
    status["state"] = "running"
    status["run_id"] = run_id
    if not status.get("started_at"):
        status["started_at"] = datetime.now().isoformat(timespec="seconds")
    try:
        train_path = model_dir / TRAIN_FILENAME
        train_frame, roles = load_dataset(train_path)
        if target not in train_frame.columns:
            raise ValueError(f"Zielspalte fehlt im Training: {target}")
        selection = _load_selection(model_dir)
        columns, _has_categories = read_export_columns(train_path)
        column_categories = {item["name"]: item["category"] for item in columns if item.get("name")}
        _append_train_log(model_dir, f"======== {run_id} ========")
        status = _emit_train_event(
            model_dir,
            status,
            "run_start",
            run_id=run_id,
            target=target,
            n_train=int(train_frame.shape[0]),
            learner=selection.get("learner") or DEFAULT_LEARNER,
            cv=selection.get("cv") or DEFAULT_CV,
            cv_folds=selection.get("cv_folds") or DEFAULT_CV_FOLDS,
            feature_k=selection.get("feature_k") or DEFAULT_FEATURE_K,
            feature_k_mode=selection.get("feature_k_mode") or DEFAULT_FEATURE_K_MODE,
            pinned=selection.get("pinned") or [],
            min_per_category=selection.get("min_per_category") or {},
        )

        def progress(event: str, **data) -> None:
            nonlocal status
            status = _emit_train_event(model_dir, status, event, **data)

        result = train_grid(
            train_frame,
            roles,
            targets=[target],
            pinned=selection.get("pinned") or [],
            min_per_category=selection.get("min_per_category") or {},
            column_categories=column_categories,
            learner=selection.get("learner") or DEFAULT_LEARNER,
            cv=selection.get("cv") or DEFAULT_CV,
            cv_folds=selection.get("cv_folds") or DEFAULT_CV_FOLDS,
            feature_k=selection.get("feature_k") or DEFAULT_FEATURE_K,
            feature_k_mode=selection.get("feature_k_mode") or DEFAULT_FEATURE_K_MODE,
            progress=progress,
        )
        path = save_run(model_dir, result)
        elapsed = _elapsed_s(status.get("started_at"))
        _emit_train_event(model_dir, status, "run_done", elapsed_s=elapsed, result_file=path.name)
    except Exception as exc:
        try:
            _emit_train_event(model_dir, status, "run_error", error=str(exc))
        except Exception:
            _append_train_log(model_dir, f"Training fehlgeschlagen: {exc}")
    finally:
        with _train_lock:
            if _train_run_id == run_id:
                _train_thread = None
                _train_model_dir = None
                _train_run_id = None


def _train_column_groups(model_dir: Path) -> dict:
    train_path = model_dir / TRAIN_FILENAME
    if not train_path.is_file():
        return {"groups": [], "n_rows": None, "error": f"{TRAIN_FILENAME} fehlt."}
    try:
        columns, _has_categories = read_export_columns(train_path)
        frame, _roles = load_dataset(train_path)
        return {
            "groups": group_columns_by_category(columns),
            "n_rows": int(frame.shape[0]),
            "error": None,
        }
    except Exception as exc:
        return {"groups": [], "n_rows": None, "error": str(exc)}


def _excel_summary(path: Path | None) -> dict | None:
    if path is None or not path.is_file():
        return None
    frame, roles = load_dataset(path)
    return {
        "file": path.name,
        "n_rows": int(frame.shape[0]),
        "columns": list(frame.columns),
        "roles": roles,
        "targets_present": roles.get("targets") or [],
        "n_features": len(roles.get("features") or []),
    }


def _active_train_path() -> Path | None:
    if ACTIVE_MODEL_DIR is None:
        return None
    path = ACTIVE_MODEL_DIR / TRAIN_FILENAME
    return path if path.is_file() else None


def _active_test_path() -> Path | None:
    if ACTIVE_MODEL_DIR is None:
        return None
    path = ACTIVE_MODEL_DIR / TEST_FILENAME
    return path if path.is_file() else None


def _model_payload(model_dir: Path) -> dict:
    train_path = model_dir / TRAIN_FILENAME
    test_path = model_dir / TEST_FILENAME
    result_path = model_dir / RESULT_FILENAME
    train_error = None
    test_error = None
    train = None
    test = None
    try:
        train = _excel_summary(train_path if train_path.is_file() else None)
    except Exception as exc:
        train_error = str(exc)
    try:
        test = _excel_summary(test_path if test_path.is_file() else None)
    except Exception as exc:
        test_error = str(exc)
    return {
        "name": model_dir.name,
        "path": str(model_dir),
        "train": train,
        "test": test,
        "train_error": train_error,
        "test_error": test_error,
        "has_result": result_path.is_file(),
    }


def _load_status() -> dict:
    if ACTIVE_MODEL_DIR is None:
        return {"type": "idle", "message": "Modellordner wählen."}
    parts = []
    train = _active_train_path()
    test = _active_test_path()
    if train:
        parts.append(f"{TRAIN_FILENAME} da")
    else:
        parts.append("kein Training")
    if test:
        parts.append(f"{TEST_FILENAME} da")
    else:
        parts.append("kein Test")
    return {"type": "success", "message": f"{ACTIVE_MODEL_DIR.name}: {', '.join(parts)}"}


@app.context_processor
def inject_nav_context():
    suggestions = [str(path) for path in _list_model_dirs()]
    active_path = str(ACTIVE_MODEL_DIR) if ACTIVE_MODEL_DIR else str(EVALUATION_ROOT)
    return {
        "data_path": active_path,
        "data_path_suggestions": suggestions,
        "load_status": _load_status(),
        "evaluation_root": str(EVALUATION_ROOT),
    }


@app.get("/")
def index():
    train_overview = None
    selection = _empty_selection()
    if ACTIVE_MODEL_DIR is not None and ACTIVE_MODEL_DIR.is_dir():
        train_overview = _train_column_groups(ACTIVE_MODEL_DIR)
        selection = _load_selection(ACTIVE_MODEL_DIR)
    return render_template(
        "index.html",
        active_page="evaluate",
        model_name=ACTIVE_MODEL_DIR.name if ACTIVE_MODEL_DIR else None,
        train_overview=train_overview,
        selection=selection,
        learner_options=LEARNER_OPTIONS,
        cv_options=CV_OPTIONS,
    )


@app.post("/api/models")
def create_model():
    payload = request.get_json(silent=True) or {}
    name = _sanitize_model_name(str(payload.get("name") or ""))
    if not name:
        return jsonify(error="Bitte einen Modellnamen angeben."), 400
    EVALUATION_ROOT.mkdir(parents=True, exist_ok=True)
    target = EVALUATION_ROOT / name
    if target.exists():
        return jsonify(error=f"Ordner existiert schon: {name}"), 400
    target.mkdir(parents=True, exist_ok=False)
    global ACTIVE_MODEL_DIR
    ACTIVE_MODEL_DIR = target
    return jsonify(ok=True, model=_model_payload(target))


@app.post("/api/models/load")
def load_model():
    global ACTIVE_MODEL_DIR
    payload = request.get_json(silent=True) or {}
    raw = str(payload.get("path") or "").strip()
    if not raw:
        return jsonify(error="Pfad fehlt."), 400
    path = _resolve_model_dir(raw)
    if (path / EVALUATION_DATA_DIR_NAME).is_dir():
        _set_data_dir(path)
        return jsonify(
            error="Bitte einen Modellordner unter data/evaluation wählen.",
            path=str(EVALUATION_ROOT),
            models=[item.name for item in _list_model_dirs()],
        ), 400
    if path.resolve() == EVALUATION_ROOT.resolve():
        return jsonify(
            error="Bitte einen Modellordner wählen.",
            path=str(EVALUATION_ROOT),
            models=[item.name for item in _list_model_dirs()],
        ), 400
    if not path.is_dir():
        return jsonify(error=f"Ordner nicht gefunden: {path}"), 400
    if path.parent.resolve() != EVALUATION_ROOT.resolve():
        return jsonify(error="Modellordner müssen direkt in data/evaluation liegen."), 400
    ACTIVE_MODEL_DIR = path
    return jsonify(ok=True, model=_model_payload(path), path=str(path))


@app.get("/api/models")
def list_models():
    items = [_model_payload(path) for path in _list_model_dirs()]
    return jsonify(models=items, root=str(EVALUATION_ROOT))


@app.post("/api/models/upload/<kind>")
def upload_split(kind):
    global ACTIVE_MODEL_DIR
    if kind not in {"train", "test"}:
        return jsonify(error="Ungültige Dateiart."), 400
    if ACTIVE_MODEL_DIR is None or not ACTIVE_MODEL_DIR.is_dir():
        return jsonify(error="Zuerst einen Modellordner laden oder anlegen."), 400
    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        return jsonify(error="Keine Excel-Datei."), 400
    filename = Path(uploaded.filename).name
    if not filename.lower().endswith(".xlsx"):
        return jsonify(error="Bitte eine .xlsx-Datei laden (View-Export)."), 400
    target_name = TRAIN_FILENAME if kind == "train" else TEST_FILENAME
    target = ACTIVE_MODEL_DIR / target_name
    uploaded.save(target)
    try:
        summary = _excel_summary(target)
    except Exception as exc:
        return jsonify(error=f"Excel konnte nicht gelesen werden: {exc}"), 400
    return jsonify(ok=True, kind=kind, dataset=summary, model=_model_payload(ACTIVE_MODEL_DIR))


@app.post("/api/models/selection")
def save_selection():
    if ACTIVE_MODEL_DIR is None or not ACTIVE_MODEL_DIR.is_dir():
        return jsonify(error="Zuerst einen Modellordner laden."), 400
    payload = request.get_json(silent=True) or {}
    selection = _save_selection(ACTIVE_MODEL_DIR, payload)
    return jsonify(ok=True, selection=selection)


@app.post("/api/train")
def train():
    global _train_thread, _train_model_dir, _train_run_id
    if ACTIVE_MODEL_DIR is None or not ACTIVE_MODEL_DIR.is_dir():
        return jsonify(error="Zuerst einen Modellordner laden."), 400
    train_path = _active_train_path()
    if train_path is None:
        return jsonify(error="Trainings-Excel fehlt (train.xlsx)."), 400
    try:
        columns, _has_categories = read_export_columns(train_path)
        _train_frame, roles = load_dataset(train_path)
        target = resolve_training_target(columns, roles)
    except Exception as exc:
        return jsonify(error=str(exc)), 400
    alive, live_dir, _live_run = _live_training()
    if alive:
        name = live_dir.name if live_dir else "unbekannt"
        return jsonify(error=f"Es läuft bereits ein Training ({name})."), 409
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_dir = ACTIVE_MODEL_DIR
    starter = _empty_train_status()
    starter["state"] = "running"
    starter["phase"] = "Start"
    starter["message"] = f"Training wird gestartet ({target})."
    starter["run_id"] = run_id
    starter["started_at"] = datetime.now().isoformat(timespec="seconds")
    starter["current"] = {"target": target, "k": None, "fold": None}
    starter["progress"] = {"current": 0, "total": 0, "unit": ""}
    _write_train_status(model_dir, starter)
    thread = threading.Thread(
        target=_run_training_job,
        args=(model_dir, run_id, target),
        name=f"train-{model_dir.name}-{run_id}",
        daemon=True,
    )
    with _train_lock:
        _train_thread = thread
        _train_model_dir = model_dir
        _train_run_id = run_id
    thread.start()
    return jsonify(ok=True, run_id=run_id, log_file=TRAIN_LOG_FILENAME)


@app.get("/api/train/status")
def train_status():
    if ACTIVE_MODEL_DIR is None:
        return jsonify(_empty_train_status())
    return jsonify(_public_train_status(ACTIVE_MODEL_DIR))


@app.get("/api/result")
def get_result():
    if ACTIVE_MODEL_DIR is None:
        return jsonify(error="Kein Modell geladen."), 404
    path = ACTIVE_MODEL_DIR / RESULT_FILENAME
    if not path.is_file():
        return jsonify(error="Noch kein Ergebnis."), 404
    return jsonify(json.loads(path.read_text(encoding="utf-8")))


@app.get("/styles.css")
def styles():
    return send_from_directory(TEMPLATES_DIR, "styles.css")


_try_load_default_data_dir()

if __name__ == "__main__":
    print(f"Evaluation-Server auf http://localhost:{EVALUATION_PORT}")
    app.run(debug=True, port=EVALUATION_PORT, threaded=True)
