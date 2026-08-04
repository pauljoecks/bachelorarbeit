"""Flask app for experiment preparation — read-only Versuchsübersicht, generate workflows."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
from flask import Flask, jsonify, redirect, render_template, request, send_file, send_from_directory, url_for

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PREPARATION_DIR = BASE_DIR / "preparation"
ACQUESITION_DIR = BASE_DIR / "acquesition"
SCRIPTS_DIR = PREPARATION_DIR / "scripts"
ACQUESITION_SCRIPTS_DIR = ACQUESITION_DIR / "scripts"
TEMPLATES_DIR = PREPARATION_DIR / "templates"
PATTERNS_DIR = TEMPLATES_DIR / "patterns"
VALID_PATH_IDS = frozenset({"SO", "LI", "SI", "ME", "PO"})
DEFAULT_DATA_DIR_PATH = "data"
DEFAULT_DATA_DIR = BASE_DIR / DEFAULT_DATA_DIR_PATH
VERSUCHSUEBERSICHT_FILENAME = "Versuchsübersicht.xlsx"
DATA_PATH_SUGGESTIONS = [
    "//han.isf.rwth-aachen.de/temp/par-jo/data",
    "data",
]

PREPARATION_DATA_DIR_NAME = "preparation"
ACQUESITION_DATA_DIR_NAME = "acquesition"
PREPARATION_PORT = int(os.environ.get("PREPARATION_PORT", "5001"))

app = Flask(__name__, template_folder=str(TEMPLATES_DIR))

data_dir: Path | None = None
versuchsuebersicht_path: str | None = None
versuchsuebersicht_data: dict | None = None
_scan_document_cache: dict = {}

GENERATE_DATA_DIR = DEFAULT_DATA_DIR / PREPARATION_DATA_DIR_NAME / "generated"
ACQUESITION_WELDING_DATA_DIR = DEFAULT_DATA_DIR / ACQUESITION_DATA_DIR_NAME / "welding"
ACQUESITION_SCANNING_DATA_DIR = DEFAULT_DATA_DIR / ACQUESITION_DATA_DIR_NAME / "scanning"

MENU_TABLE_COLUMNS = ["COUNT", "ID", "WELDED", "SCANNED", "SERIES", "NUMBER", "COMMENT"]
GENERATE_TABLE_COLUMNS = ["ID", "PATH ID", "SERIES", "NUMBER"]
GENERATE_TABLE_COLUMN_LABELS = {
    "SERIES": "S",
    "NUMBER": "N",
}
VIEW_EXCEL_VALUE_FIELDS = (
    ("COUNT", "count"),
    ("ID", "id"),
    ("PATH ID", "path_id"),
    ("WFS [m/min]", "wfs"),
    ("WS [m/min]", "ws"),
    ("SERIES", "series"),
    ("NUMBER", "number"),
)
VIEW_VECTOR_EXPORT_KEYS = frozenset({"path_id_vector", "64_64_scan"})
VIEW_META_KEYS = frozenset(key for _column, key in VIEW_EXCEL_VALUE_FIELDS)
MENU_FILTER_OPTIONS = ["WELDED", "SCANNED", "ID"]
SCANSPEED_COLUMN = "SCANSPEED [mm/s]"
ANALYZE_SCAN_FILENAME = "cropped_scan.json"
ANALYZE_WELD_FILENAME = "cropped_weld.h5"
ANALYZE_POWER_FILENAME = "power.h5"
ANALYZE_CHARACTERISTICS_FILENAME = "characteristics.json"
ANALYZE_GRENZEN_FILENAME = "grenzen.json"
ANALYZE_CHAR_GRAPHEN_FILENAME = "char_graphen.json"
ANALYZE_FILTERED_FILENAME = "filtered.json"
ANALYZE_X_PROFILE_FILENAME = "X_profile.json"
ANALYZE_Y_PROFILE_FILENAME = "Y_profile.json"
ANALYZE_64_64_SCAN_FILENAME = "64_64_scan.json"
GENERATE_SCAN_SUBDIR = "scan"
GENERATE_WELD_SUBDIR = "weld"
_GENERATE_SCAN_FILES = frozenset(
    {
        ANALYZE_SCAN_FILENAME,
        ANALYZE_FILTERED_FILENAME,
        ANALYZE_X_PROFILE_FILENAME,
        ANALYZE_Y_PROFILE_FILENAME,
        ANALYZE_64_64_SCAN_FILENAME,
    }
)
_GENERATE_WELD_FILES = frozenset(
    {
        ANALYZE_WELD_FILENAME,
        ANALYZE_POWER_FILENAME,
        ANALYZE_GRENZEN_FILENAME,
        ANALYZE_CHAR_GRAPHEN_FILENAME,
    }
)
EXCEL_INTEGER_COLUMNS = {"SERIES", "NUMBER", "RESOLUTION", "PROFILEFREQUENCY"}
EXCEL_FLOAT_COLUMNS = {"WFS [m/min]", "WS [m/min]", "SCANDURATION", SCANSPEED_COLUMN}
EXCEL_NUMERIC_COLUMNS = EXCEL_INTEGER_COLUMNS | EXCEL_FLOAT_COLUMNS
WELD_DEVICE = os.environ.get("WELD_DEVICE", "cDAQ4Mod1").strip() or "cDAQ4Mod1"
WELD_RATE = float(os.environ.get("WELD_RATE", "50000"))
WELD_THRESHOLD_V = float(os.environ.get("WELD_THRESHOLD_V", "0.2"))
WELD_PRE_TIME_S = float(os.environ.get("WELD_PRE_TIME_S", "2.0"))
WELD_POST_TIME_S = float(os.environ.get("WELD_POST_TIME_S", "2.0"))
WELD_MAX_DURATION_S = float(os.environ.get("WELD_MAX_DURATION_S", "300.0"))
WELDING_GRAPH_MAX_POINTS = 250
SCANNING_GRAPH_MAX_POINTS = 400
GRAPH_ZOOM_MAX_POINTS_SCAN = 4000
GRAPH_ZOOM_MIN_RANGE_FRACTION = 0.002
DEFAULT_TABLE_FILTER_COLUMN = "WELDED"
EXCEL_SUFFIXES = {".xlsx", ".xls", ".xlsm"}
MAX_ROWS = 1000
_DEFAULT_EXCEL_PLACEHOLDER_COLUMN = re.compile(r"^spalte\d+$", re.IGNORECASE)

_REQUIRED_EXCEL_COLUMNS = sorted(
    set(
        MENU_TABLE_COLUMNS
        + MENU_FILTER_OPTIONS
        + [
            "PATH ID",
            "WFS [m/min]",
            "WS [m/min]",
            "WIRE",
            "WIREDIA [mm]",
            "GAS",
            "GASFLOW [l/min]",
            "POWERSOURCE",
            "PROCESS",
            "RESOLUTION",
            "PROFILEFREQUENCY",
            "SCANSPEED [mm/s]",
            "SCANDURATION",
            "H5FILE",
            "JSONFILE",
            "COMMENT",
        ]
    )
)


def _find_column(columns, name):
    target = name.strip().lower()
    for column in columns:
        if str(column).strip().lower() == target:
            return str(column)
    return None


def _find_id_column(columns):
    return _find_column(columns, "id")


def _normalize_id(value):
    if value is None:
        return None
    text = str(value).strip().upper()
    return text or None


def _normalize_path_input(path_str: str) -> str:
    path_str = path_str.strip().strip('"').strip("'")
    path_str = path_str.replace("\t", "\\t")
    if path_str.startswith("\\") and not path_str.startswith("\\\\"):
        path_str = "\\" + path_str
    return path_str.replace("\\", "/")


def _format_path_for_ui(path: Path) -> str:
    try:
        return str(path.relative_to(BASE_DIR)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _resolve_path(path_str: str) -> Path:
    path_str = _normalize_path_input(path_str)
    if not path_str:
        return Path(".")
    path = Path(path_str)
    if path_str.startswith("//") or path.is_absolute():
        return path
    return BASE_DIR / path


def _clear_data_runtime_caches() -> None:
    global _scan_document_cache

    _scan_document_cache.clear()


def _configure_data_dirs(root: Path) -> None:
    global data_dir, GENERATE_DATA_DIR
    global ACQUESITION_WELDING_DATA_DIR, ACQUESITION_SCANNING_DATA_DIR

    data_dir = root.resolve()
    GENERATE_DATA_DIR = data_dir / PREPARATION_DATA_DIR_NAME / "generated"
    ACQUESITION_WELDING_DATA_DIR = data_dir / ACQUESITION_DATA_DIR_NAME / "welding"
    ACQUESITION_SCANNING_DATA_DIR = data_dir / ACQUESITION_DATA_DIR_NAME / "scanning"
    GENERATE_DATA_DIR.mkdir(parents=True, exist_ok=True)


def _find_versuchsuebersicht_excel(root: Path) -> Path:
    excel_path = root / VERSUCHSUEBERSICHT_FILENAME
    if excel_path.is_file():
        return excel_path
    raise ValueError(f'"{VERSUCHSUEBERSICHT_FILENAME}" nicht gefunden im Ordner: {root}')


def _build_id_index(rows, columns):
    id_column = _find_id_column(columns)
    if id_column is None:
        return {}
    index = {}
    for row in rows:
        normalized_id = _normalize_id(row.get(id_column))
        if normalized_id:
            index[normalized_id] = row
    return index


def _filter_rows_with_id(df):
    id_column = _find_id_column(df.columns)
    if id_column is None:
        raise ValueError('Spalte "ID" nicht gefunden.')
    id_values = df[id_column]
    has_id = id_values.notna() & (id_values.astype(str).str.strip() != "")
    return df.loc[has_id]


def _is_default_excel_placeholder_column(column_name):
    return bool(_DEFAULT_EXCEL_PLACEHOLDER_COLUMN.match(str(column_name).strip()))


def _get_excel_usecols(all_columns):
    selected = set()
    for index, column in enumerate(all_columns):
        if _is_default_excel_placeholder_column(column):
            break
        selected.add(index)
    for name in _REQUIRED_EXCEL_COLUMNS:
        for index, column in enumerate(all_columns):
            if str(column).strip().lower() == name.strip().lower():
                selected.add(index)
    return sorted(selected)


def _load_versuchsuebersicht_from_path(path):
    global versuchsuebersicht_path, versuchsuebersicht_data

    if path.suffix.lower() not in EXCEL_SUFFIXES:
        raise ValueError("Nur Excel-Dateien (.xlsx, .xls, .xlsm) werden unterstützt.")

    path = Path(path)
    header = pd.read_excel(path, nrows=0)
    all_columns = [str(column) for column in header.columns]
    df = pd.read_excel(path, nrows=MAX_ROWS, usecols=_get_excel_usecols(all_columns))
    df.columns = [str(column) for column in df.columns]
    df = _filter_rows_with_id(df)
    records = df.where(pd.notnull(df), None).to_dict(orient="records")
    columns = list(df.columns)

    versuchsuebersicht_path = str(path.resolve())
    versuchsuebersicht_data = {
        "columns": columns,
        "rows": records,
        "id_index": _build_id_index(records, columns),
    }
    return {
        "path": versuchsuebersicht_path,
        "row_count": len(records),
        "column_count": len(columns),
    }


def _load_data_dir(path: Path) -> dict:
    path = Path(path)
    if not path.is_dir():
        raise ValueError(f"Pfad muss ein Ordner sein: {path}")
    excel_path = _find_versuchsuebersicht_excel(path)
    _configure_data_dirs(path)
    _clear_data_runtime_caches()
    return _load_versuchsuebersicht_from_path(excel_path)


def _try_load_default_data_dir():
    if not DEFAULT_DATA_DIR.is_dir():
        return
    try:
        _load_data_dir(DEFAULT_DATA_DIR)
    except Exception:
        pass


def _get_load_status():
    if versuchsuebersicht_data is None:
        return {"message": "Noch nicht geladen.", "type": "idle"}
    row_count = len(versuchsuebersicht_data["rows"])
    path = _get_data_path_display()
    return {"message": f"{row_count} Zeilen geladen aus {path}.", "type": "success"}


def _get_data_path_display():
    if data_dir:
        return _format_path_for_ui(Path(data_dir))
    return DEFAULT_DATA_DIR_PATH


def _has_value(value):
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if not text:
        return False
    return text.lower() not in {"nan", "nat", "none"}


def _format_cell_value(value):
    if not _has_value(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def _parse_excel_timestamp(value):
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    text = _format_cell_value(value)
    if not text:
        return None
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime()


def _format_welded(value):
    if not _has_value(value):
        return ""
    parsed = _parse_excel_timestamp(value)
    if parsed is not None:
        return parsed.strftime("%Y-%m-%d %H:%M:%S")
    return _format_cell_value(value)


def _format_display_value(column_name, value):
    if column_name in {"WELDED", "SCANNED"}:
        return _format_welded(value)
    return _format_cell_value(value)


def _get_filter_options(columns):
    options = []
    for name in MENU_FILTER_OPTIONS:
        column = _find_column(columns, name)
        if column:
            options.append(column)
    return options


def _resolve_filter_column(requested_column):
    if versuchsuebersicht_data is None:
        return DEFAULT_TABLE_FILTER_COLUMN
    columns = versuchsuebersicht_data["columns"]
    options = _get_filter_options(columns)
    if not options:
        return DEFAULT_TABLE_FILTER_COLUMN
    if requested_column:
        matched_column = _find_column(columns, requested_column)
        if matched_column in options:
            return matched_column
    matched_default = _find_column(columns, DEFAULT_TABLE_FILTER_COLUMN)
    return matched_default if matched_default in options else options[0]


def _get_table_rows(filter_column_name):
    if versuchsuebersicht_data is None:
        return []
    columns = versuchsuebersicht_data["columns"]
    column_map = {name: _find_column(columns, name) for name in MENU_TABLE_COLUMNS}
    filter_column = _find_column(columns, filter_column_name)
    if filter_column is None:
        return []
    rows = []
    for row in versuchsuebersicht_data["rows"]:
        if not _has_value(row.get(filter_column)):
            continue
        display_row = {}
        for name in MENU_TABLE_COLUMNS:
            source_column = column_map[name]
            display_row[name] = (
                _format_display_value(name, row.get(source_column)) if source_column else ""
            )
        rows.append(display_row)
    return rows


def _cache_value_from_excel_field(field_name, value):
    if _is_blank_excel_input(value):
        return None

    if field_name in {"SCANNED", "WELDED"}:
        parsed = _parse_excel_timestamp(value)
        return parsed if parsed is not None else value

    return _excel_cell_value(field_name, value)


def _import_run_scan():
    scripts_dir = str(ACQUESITION_SCRIPTS_DIR)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import run_scan

    return run_scan


def _import_run_weld():
    scripts_dir = str(ACQUESITION_SCRIPTS_DIR)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import run_weld

    return run_weld


def _import_run_analyze():
    scripts_dir = str(SCRIPTS_DIR)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import run_analyze

    return run_analyze


def _build_weld_config():
    run_weld = _import_run_weld()
    return run_weld.WeldConfig(
        device=WELD_DEVICE,
        rate=WELD_RATE,
        threshold_v=WELD_THRESHOLD_V,
        pre_time_s=WELD_PRE_TIME_S,
        post_time_s=WELD_POST_TIME_S,
        max_duration_s=WELD_MAX_DURATION_S,
    )


def _parse_positive_float_setting(value, field_name):
    text = _format_cell_value(value)
    if not text:
        raise ValueError(f"{field_name} fehlt.")

    normalized = text.replace(",", ".")
    try:
        parsed = float(normalized)
    except ValueError as exc:
        raise ValueError(f"{field_name} muss eine Zahl sein.") from exc

    if parsed <= 0:
        raise ValueError(f"{field_name} muss größer als 0 sein.")

    return parsed


def _get_scanspeed_from_row(row):
    if versuchsuebersicht_data is None or row is None:
        return ""

    columns = versuchsuebersicht_data["columns"]
    column = _find_column(columns, SCANSPEED_COLUMN)
    if not column:
        return ""

    return _format_cell_value(row.get(column))


def _resolve_scanspeed_value(scanspeed, row=None):
    if scanspeed is not None:
        text = str(scanspeed).strip()
        if not text:
            raise ValueError(f"{SCANSPEED_COLUMN} fehlt.")
        return _parse_positive_float_setting(text, SCANSPEED_COLUMN)

    value = _get_scanspeed_from_row(row)
    if not value:
        raise ValueError(f"{SCANSPEED_COLUMN} fehlt.")
    return _parse_positive_float_setting(value, SCANSPEED_COLUMN)


def _get_scan_geometry_from_row(row):
    if versuchsuebersicht_data is None or row is None:
        raise ValueError("Keine Versuchsübersicht geladen.")

    columns = versuchsuebersicht_data["columns"]
    scan_duration_s = _parse_positive_float_setting(
        row.get(_find_column(columns, "SCANDURATION")),
        "SCANDURATION",
    )
    scan_speed_mm_s = _resolve_scanspeed_value(_get_scanspeed_from_row(row), row)
    return scan_speed_mm_s, scan_duration_s


def _get_profile_y_mm_values(document, profiles, experiment_id=None):
    run_scan = _import_run_scan()

    if profiles and all(profile.get("y_mm") is not None for profile in profiles):
        return [float(profile["y_mm"]) for profile in profiles]

    scan_speed_mm_s = document.get("scan_speed_mm_s")
    scan_duration_s = document.get("scan_duration_s")
    scan_settings = document.get("scan_settings") or {}
    if scan_speed_mm_s is None:
        scan_speed_mm_s = scan_settings.get("scan_speed_mm_s")
    if scan_duration_s is None:
        try:
            scan_duration_s = run_scan.extract_scan_duration_s(scan_settings)
        except ValueError:
            scan_duration_s = None

    normalized_id = _normalize_id(experiment_id or document.get("experiment_id"))
    if normalized_id and versuchsuebersicht_data:
        row = versuchsuebersicht_data["id_index"].get(normalized_id)
        if row is not None:
            try:
                excel_speed, excel_duration = _get_scan_geometry_from_row(row)
                if scan_speed_mm_s is None:
                    scan_speed_mm_s = excel_speed
                if scan_duration_s is None:
                    scan_duration_s = excel_duration
            except ValueError:
                pass

    if scan_speed_mm_s is None or scan_duration_s is None:
        raise ValueError(f"{SCANSPEED_COLUMN} oder SCANDURATION fehlen für y-Zuordnung.")

    temp_profiles = [{"profile_index": index} for index in range(len(profiles))]
    run_scan.assign_profile_y_mm(
        temp_profiles,
        scan_speed_mm_s=float(scan_speed_mm_s),
        scan_duration_s=float(scan_duration_s),
    )
    return [float(item["y_mm"]) for item in temp_profiles]


def _get_generate_table_rows():
    if versuchsuebersicht_data is None:
        return []

    columns = versuchsuebersicht_data["columns"]
    column_map = {name: _find_column(columns, name) for name in GENERATE_TABLE_COLUMNS}
    welded_column = _find_column(columns, "WELDED")
    scanned_column = _find_column(columns, "SCANNED")

    if welded_column is None or scanned_column is None:
        return []

    rows = []
    for row in versuchsuebersicht_data["rows"]:
        if not _has_value(row.get(welded_column)):
            continue
        if not _has_value(row.get(scanned_column)):
            continue

        display_row = {}
        for name in GENERATE_TABLE_COLUMNS:
            source_column = column_map[name]
            display_row[name] = (
                _format_display_value(name, row.get(source_column)) if source_column else ""
            )

        experiment_id = display_row.get("ID", "")
        display_row["has_analyze"] = (
            _experiment_has_valid_analyze(experiment_id) if experiment_id else False
        )
        rows.append(display_row)

    return rows


def _get_view_excel_values_for_row(row):
    if row is None or versuchsuebersicht_data is None:
        return {key: "" for _column, key in VIEW_EXCEL_VALUE_FIELDS}

    columns = versuchsuebersicht_data["columns"]
    values = {}
    for column_name, key in VIEW_EXCEL_VALUE_FIELDS:
        column = _find_column(columns, column_name)
        if column is None:
            values[key] = ""
            continue
        values[key] = _format_display_value(column_name, row.get(column))
    return values


def _get_view_value_column_labels() -> dict[str, str]:
    labels = {key: column_name for column_name, key in VIEW_EXCEL_VALUE_FIELDS}
    labels["path_id_vector"] = "PATH ID Vektor"
    labels["64_64_scan"] = "64_64_scan"
    for key in _get_target_characteristic_keys():
        labels[key] = key
    for key in _get_weld_characteristic_keys():
        labels[key] = key
    return labels


def _get_view_value_column_order() -> tuple[str, ...]:
    meta_keys = tuple(key for _column_name, key in VIEW_EXCEL_VALUE_FIELDS)
    return (
        meta_keys
        + ("path_id_vector",)
        + _get_target_characteristic_keys()
        + ("64_64_scan",)
        + _get_weld_characteristic_keys()
    )


def _serialize_path_id_vector(path_id: str | None) -> str | None:
    normalized = str(path_id or "").strip().upper()
    if normalized not in VALID_PATH_IDS:
        return None

    pattern_path = PATTERNS_DIR / f"{normalized}.json"
    if not pattern_path.is_file():
        return None

    with pattern_path.open("r", encoding="utf-8") as handle:
        paths = json.load(handle)
    if not isinstance(paths, list):
        return None
    return json.dumps(paths, ensure_ascii=False, separators=(",", ":"))


def _serialize_64_64_scan_values(experiment_id: str) -> str | None:
    grid_path, error = _resolve_64_64_scan_path_for_experiment(experiment_id)
    if error or grid_path is None:
        return None

    with grid_path.open("r", encoding="utf-8") as handle:
        document = json.load(handle)

    values = document.get("values")
    if not isinstance(values, list):
        return None
    return json.dumps(values, ensure_ascii=False, separators=(",", ":"))


def _characteristics_document_to_value_map(document) -> dict[str, float]:
    values: dict[str, float] = {}
    if not isinstance(document, dict):
        return values

    scan = document.get("scan")
    if isinstance(scan, dict):
        for key, value in scan.items():
            if isinstance(value, (int, float, np.integer, np.floating)):
                number = float(value)
                if np.isfinite(number):
                    values[str(key)] = number

    weld_rows = document.get("weld")
    if isinstance(weld_rows, list):
        for row in weld_rows:
            if not isinstance(row, dict):
                continue
            for key, value in row.items():
                if key == "quantity":
                    continue
                if isinstance(value, (int, float, np.integer, np.floating)):
                    number = float(value)
                    if np.isfinite(number):
                        values[str(key)] = number
    return values


def _resolve_view_export_cell(
    column_key: str,
    experiment_id: str,
    excel_values: dict[str, str],
    characteristics_map: dict[str, float],
):
    if column_key == "path_id_vector":
        return _serialize_path_id_vector(excel_values.get("path_id"))
    if column_key == "64_64_scan":
        return _serialize_64_64_scan_values(experiment_id)
    if column_key in VIEW_META_KEYS:
        value = excel_values.get(column_key, "")
        return value if value not in (None, "") else None
    value = characteristics_map.get(column_key)
    if value is None:
        return None
    return float(value) if isinstance(value, (int, float, np.floating)) else value


def _get_view_table_rows():
    rows = _get_generate_table_rows()
    if versuchsuebersicht_data is None or not rows:
        return rows

    id_to_source_row = {}
    id_column = _find_column(versuchsuebersicht_data["columns"], "ID")
    if id_column is not None:
        for source_row in versuchsuebersicht_data["rows"]:
            experiment_id = _format_display_value("ID", source_row.get(id_column))
            if experiment_id:
                id_to_source_row[str(experiment_id).strip().upper()] = source_row

    enriched_rows = []
    for display_row in rows:
        row = dict(display_row)
        experiment_id = str(row.get("ID", "")).strip().upper()
        source_row = id_to_source_row.get(experiment_id)
        excel_values = _get_view_excel_values_for_row(source_row)
        row["COUNT"] = excel_values.get("count", "")
        row["WFS"] = excel_values.get("wfs", "")
        row["WS"] = excel_values.get("ws", "")
        enriched_rows.append(row)

    return enriched_rows


def _excel_cell_value(field_name, value):
    if value == "" or value is None:
        return None

    if field_name not in EXCEL_NUMERIC_COLUMNS:
        return value

    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        if field_name in EXCEL_INTEGER_COLUMNS and value.is_integer():
            return int(value)
        return value

    normalized = str(value).strip().replace(",", ".")
    if not normalized:
        return None

    try:
        number = float(normalized)
    except ValueError:
        return value

    if field_name in EXCEL_INTEGER_COLUMNS and number.is_integer():
        return int(number)
    return number


def _is_blank_excel_input(value):
    if value is None:
        return True

    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass

    if isinstance(value, str) and not value.strip():
        return True

    return False


def _sanitize_h5_filename(filename):
    text = str(filename).strip()
    if not text:
        return None

    name = Path(text).name
    if not re.fullmatch(r"[\w.-]+\.h5", name, re.IGNORECASE):
        raise ValueError(f"Ungültiger H5-Dateiname: {name}")

    return name


def _get_experiment_h5_filename(experiment_id):
    if versuchsuebersicht_data is None:
        return None

    row = versuchsuebersicht_data["id_index"].get(_normalize_id(experiment_id))
    if row is None:
        return None

    column = _find_column(versuchsuebersicht_data["columns"], "H5FILE")
    if column is None:
        return None

    value = _format_cell_value(row.get(column))
    if not value:
        return None

    return _sanitize_h5_filename(value)


def _sanitize_scan_filename(filename):
    text = str(filename).strip()
    if not text:
        return None

    name = Path(text).name
    if not re.fullmatch(r"[\w.-]+\.json", name, re.IGNORECASE):
        raise ValueError(f"Ungültiger Scan-Dateiname: {name}")

    return name


def _get_experiment_scan_filename(experiment_id):
    if versuchsuebersicht_data is None:
        return None

    row = versuchsuebersicht_data["id_index"].get(_normalize_id(experiment_id))
    if row is None:
        return None

    column = _find_column(versuchsuebersicht_data["columns"], "JSONFILE")
    if column is None:
        return None

    value = _format_cell_value(row.get(column))
    if not value:
        return None

    return _sanitize_scan_filename(value)


def _load_scan_document(scan_path):
    cache_key = str(scan_path.resolve())
    mtime = scan_path.stat().st_mtime
    cached = _scan_document_cache.get(cache_key)
    if cached and cached[0] == mtime:
        return cached[1]

    with scan_path.open("r", encoding="utf-8") as handle:
        document = json.load(handle)

    if "profiles" not in document or not document["profiles"]:
        raise ValueError("Keine Profile in Scan-Datei gefunden.")

    _scan_document_cache[cache_key] = (mtime, document)
    return document


def _profile_point_stats(profile):
    valid_mask = _import_run_scan()._profile_measurement_mask(profile)
    total_points = int(valid_mask.size)
    valid_points = int(valid_mask.sum())
    return {
        "total_points": total_points,
        "valid_points": valid_points,
        "invalid_points": total_points - valid_points,
    }


def _filter_valid_profile_points(profile):
    x_mm = np.asarray(profile["x_mm"], dtype=float)
    z_mm = np.asarray(profile["z_mm"], dtype=float)
    mask = _import_run_scan()._profile_measurement_mask(profile)

    if not np.any(mask):
        return x_mm[:0], z_mm[:0]

    return x_mm[mask], z_mm[mask]


def _downsample_profile_points(x_mm, z_mm, max_points):
    x_mm = np.asarray(x_mm, dtype=float)
    z_mm = np.asarray(z_mm, dtype=float)

    if len(x_mm) <= max_points:
        return x_mm, z_mm

    indices = np.linspace(0, len(x_mm) - 1, max_points, dtype=int)
    return x_mm[indices], z_mm[indices]


def _axis_bounds(values):
    array = np.asarray(values, dtype=float)
    if array.size == 0:
        return None
    finite = array[np.isfinite(array)]
    if finite.size == 0:
        return None
    return {"min": float(finite.min()), "max": float(finite.max())}


def _compute_zoom_max_points(base_max, range_min, range_max, full_min, full_max, cap):
    if (
        range_min is None
        or range_max is None
        or full_min is None
        or full_max is None
        or full_max <= full_min
    ):
        return base_max

    full_span = full_max - full_min
    range_span = max(abs(range_max - range_min), full_span * GRAPH_ZOOM_MIN_RANGE_FRACTION)
    zoom_factor = full_span / range_span
    return min(cap, max(base_max, int(base_max * zoom_factor)))


def _filter_points_by_axis_range(x_values, y_values, axis_min, axis_max):
    x_array = np.asarray(x_values, dtype=float)
    y_array = np.asarray(y_values, dtype=float)
    if axis_min is None or axis_max is None or x_array.size == 0:
        return x_array, y_array

    lo = min(axis_min, axis_max)
    hi = max(axis_min, axis_max)
    mask = (x_array >= lo) & (x_array <= hi)
    return x_array[mask], y_array[mask]


def _scan_graph_kwargs_from_request():
    return {
        "x_min": request.args.get("x_min", type=float),
        "x_max": request.args.get("x_max", type=float),
    }


def _weld_graph_kwargs_from_request():
    return {
        "time_min": request.args.get("time_min", type=float),
        "time_max": request.args.get("time_max", type=float),
    }


def _load_scanning_profile_graph(
    scan_path,
    profile_index,
    *,
    x_min=None,
    x_max=None,
    max_points=None,
):
    document = _load_scan_document(scan_path)
    profiles = document["profiles"]
    profile_count = int(document.get("profile_count") or len(profiles))

    if profile_index < 0 or profile_index >= len(profiles):
        raise ValueError(f"Profilindex {profile_index} liegt außerhalb des Bereichs 0–{len(profiles) - 1}.")

    profile = profiles[profile_index]
    point_stats = _profile_point_stats(profile)
    y_mm = profile.get("y_mm")
    if y_mm is None:
        try:
            y_mm = _get_profile_y_mm_values(
                document,
                profiles,
                experiment_id=document.get("experiment_id"),
            )[profile_index]
        except ValueError:
            y_mm = None
    x_mm, z_mm = _filter_valid_profile_points(profile)
    x_bounds = _axis_bounds(x_mm)
    effective_max = max_points or _compute_zoom_max_points(
        SCANNING_GRAPH_MAX_POINTS,
        x_min,
        x_max,
        x_bounds["min"] if x_bounds else None,
        x_bounds["max"] if x_bounds else None,
        GRAPH_ZOOM_MAX_POINTS_SCAN,
    )
    x_mm, z_mm = _filter_points_by_axis_range(x_mm, z_mm, x_min, x_max)
    x_mm, z_mm = _downsample_profile_points(x_mm, z_mm, effective_max)

    return {
        "json_file": scan_path.name,
        "profile_index": profile_index,
        "profile_count": profile_count,
        "resolution": int(document.get("resolution") or len(profile.get("x_mm", []))),
        "demo_mode": bool(document.get("demo_mode")),
        "point_stats": point_stats,
        "y_mm": y_mm,
        "x_mm": x_mm.tolist(),
        "z_mm": z_mm.tolist(),
        "x_bounds": x_bounds,
        "point_count": int(len(x_mm)),
    }


def _load_generate_scan_heatmap(analyze_path):
    document = _load_scan_document(analyze_path)
    profiles = document.get("profiles") or []
    if not profiles:
        raise ValueError("Keine Profile in Analyse-Datei gefunden.")

    profile_count = len(profiles)
    resolution = int(document.get("resolution") or len(profiles[0].get("x_mm", [])))
    x_mm = profiles[0].get("x_mm") or []
    if not x_mm:
        raise ValueError("Keine x-Werte in Analyse-Datei gefunden.")

    x_first = float(x_mm[0])
    x_last = float(x_mm[-1])
    x_min = min(x_first, x_last)
    x_max = max(x_first, x_last)

    values = []
    positive_values = []
    for profile in profiles:
        z_row = [float(value) for value in profile.get("z_mm") or []]
        if len(z_row) != resolution:
            raise ValueError("Profilauflösung ist in der Analyse-Datei nicht konsistent.")
        values.extend(z_row)
        positive_values.extend(value for value in z_row if value > 0)

    z_scale_min = 0.0
    z_scale_max = 0.0
    if positive_values:
        sorted_values = sorted(positive_values)
        lower_index = max(0, int(len(sorted_values) * 0.02) - 1)
        upper_index = min(len(sorted_values) - 1, int(len(sorted_values) * 0.98))
        z_scale_min = float(sorted_values[lower_index])
        z_scale_max = float(sorted_values[upper_index])
        if z_scale_max <= z_scale_min:
            z_scale_min = float(sorted_values[0])
            z_scale_max = float(sorted_values[-1])

    y_mm = _get_profile_y_mm_values(
        document,
        profiles,
        experiment_id=document.get("experiment_id"),
    )

    return {
        "json_file": analyze_path.name,
        "profile_count": profile_count,
        "resolution": resolution,
        "x_min": x_min,
        "x_max": x_max,
        "x_reversed": x_first > x_last,
        "y_mm": y_mm,
        "y_min": min(y_mm),
        "y_max": max(y_mm),
        "z_scale_min": z_scale_min,
        "z_scale_max": z_scale_max,
        "values": values,
    }


def _load_grid_scan_heatmap(grid_path):
    with grid_path.open("r", encoding="utf-8") as handle:
        document = json.load(handle)

    profile_count = int(document.get("profile_count") or document.get("grid_size") or 0)
    resolution = int(document.get("resolution") or document.get("grid_size") or 0)
    values = [float(value) for value in document.get("values") or []]
    if profile_count <= 0 or resolution <= 0 or len(values) != profile_count * resolution:
        raise ValueError("Ungültiges 64×64-Scan-Raster.")

    positive_values = [value for value in values if value > 0]
    z_scale_min = 0.0
    z_scale_max = 0.0
    if positive_values:
        sorted_values = sorted(positive_values)
        lower_index = max(0, int(len(sorted_values) * 0.02) - 1)
        upper_index = min(len(sorted_values) - 1, int(len(sorted_values) * 0.98))
        z_scale_min = float(sorted_values[lower_index])
        z_scale_max = float(sorted_values[upper_index])
        if z_scale_max <= z_scale_min:
            z_scale_min = float(sorted_values[0])
            z_scale_max = float(sorted_values[-1])

    y_mm = [float(value) for value in document.get("y_mm") or []]
    if len(y_mm) != profile_count:
        raise ValueError("y_mm-Länge passt nicht zum 64×64-Scan-Raster.")

    x_min = float(document["x_min"])
    x_max = float(document["x_max"])

    return {
        "json_file": grid_path.name,
        "profile_count": profile_count,
        "resolution": resolution,
        "grid_size": profile_count,
        "x_min": x_min,
        "x_max": x_max,
        "x_reversed": bool(document.get("x_reversed")),
        "y_mm": y_mm,
        "y_min": float(document.get("y_min", min(y_mm))),
        "y_max": float(document.get("y_max", max(y_mm))),
        "z_scale_min": z_scale_min,
        "z_scale_max": z_scale_max,
        "values": values,
    }


def _resolve_64_64_scan_path_for_experiment(experiment_id):
    folder_path, error = _resolve_analyze_folder_for_experiment(experiment_id)
    if error:
        return None, error

    grid_path = _find_generated_file(folder_path, ANALYZE_64_64_SCAN_FILENAME)
    if grid_path is None:
        return None, f"{ANALYZE_64_64_SCAN_FILENAME} nicht gefunden in {folder_path.name}."

    return grid_path, None


def _resolve_scan_path_for_experiment(experiment_id):
    try:
        scan_filename = _get_experiment_scan_filename(experiment_id)
    except ValueError as exc:
        return None, str(exc)

    if not scan_filename:
        return None, "Keine Scan-Datei für diese ID."

    scan_path = ACQUESITION_SCANNING_DATA_DIR / scan_filename
    if not scan_path.is_file():
        return None, f"Scan-Datei nicht gefunden: {scan_filename}"

    return scan_path, None


def _sanitize_analyze_folder_name(folder_name):
    text = str(folder_name).strip()
    if not text:
        return None

    name = Path(text).name
    if name != text or name in {".", ".."}:
        raise ValueError(f"Ungültiger Analyse-Ordnername: {text}")

    if not re.fullmatch(r"[A-Z]{3}_\d{8}_\d{6}", name):
        raise ValueError(f"Ungültiger Analyse-Ordnername: {name}")

    return name


def _list_analyze_folders_for_experiment(experiment_id):
    normalized_id = _normalize_id(experiment_id)
    if not normalized_id or not GENERATE_DATA_DIR.is_dir():
        return []

    prefix = f"{normalized_id}_"
    folders = []
    for entry in GENERATE_DATA_DIR.iterdir():
        if not entry.is_dir() or not entry.name.startswith(prefix):
            continue
        try:
            folders.append(_sanitize_analyze_folder_name(entry.name))
        except ValueError:
            continue
    return sorted(folders)


def _get_experiment_analyze_folder(experiment_id):
    folders = _list_analyze_folders_for_experiment(experiment_id)
    if not folders:
        return None
    return folders[-1]


def _resolve_analyze_folder_for_experiment(experiment_id):
    try:
        analyze_folder = _get_experiment_analyze_folder(experiment_id)
    except ValueError as exc:
        return None, str(exc)

    if not analyze_folder:
        return None, "Kein Analyse-Ordner für diese ID."

    folder_path = GENERATE_DATA_DIR / analyze_folder
    if not folder_path.is_dir():
        return None, f"Analyse-Ordner nicht gefunden: {analyze_folder}"

    return folder_path, None


def _generated_folder_root(file_path):
    parent = Path(file_path).resolve().parent
    if parent.name in {GENERATE_SCAN_SUBDIR, GENERATE_WELD_SUBDIR}:
        return parent.parent
    return parent


def _generated_file_candidates(folder_path, filename):
    folder_path = Path(folder_path)
    if filename == ANALYZE_CHARACTERISTICS_FILENAME:
        return [folder_path / filename]
    if filename in _GENERATE_SCAN_FILES:
        return [
            folder_path / GENERATE_SCAN_SUBDIR / filename,
            folder_path / filename,
        ]
    if filename in _GENERATE_WELD_FILES:
        return [
            folder_path / GENERATE_WELD_SUBDIR / filename,
            folder_path / filename,
        ]
    return [
        folder_path / GENERATE_SCAN_SUBDIR / filename,
        folder_path / GENERATE_WELD_SUBDIR / filename,
        folder_path / filename,
    ]


def _find_generated_file(folder_path, filename):
    for candidate in _generated_file_candidates(folder_path, filename):
        if candidate.is_file():
            return candidate
    return None


def _resolve_analyze_path_for_experiment(experiment_id):
    folder_path, error = _resolve_analyze_folder_for_experiment(experiment_id)
    if error:
        return None, error

    analyze_path = _find_generated_file(folder_path, ANALYZE_SCAN_FILENAME)
    if analyze_path is None:
        return None, f"{ANALYZE_SCAN_FILENAME} nicht gefunden in {folder_path.name}."

    return analyze_path, None


def _resolve_analyze_weld_path_for_experiment(experiment_id):
    folder_path, error = _resolve_analyze_folder_for_experiment(experiment_id)
    if error:
        return None, error

    analyze_weld_path = _find_generated_file(folder_path, ANALYZE_WELD_FILENAME)
    if analyze_weld_path is None:
        return None, f"{ANALYZE_WELD_FILENAME} nicht gefunden in {folder_path.name}."

    return analyze_weld_path, None


def _current_stats_for_cropped_weld(analyze_weld_path):
    folder_path = _generated_folder_root(analyze_weld_path)
    characteristics_path = folder_path / ANALYZE_CHARACTERISTICS_FILENAME
    if characteristics_path.is_file():
        try:
            run_analyze = _import_run_analyze()
            document = run_analyze.load_characteristics(characteristics_path)
            for item in document.get("weld") or []:
                if run_analyze._normalize_weld_quantity(item.get("quantity")) != run_analyze.WELD_CURRENT_QUANTITY:
                    continue
                result = {"unit": "A"}
                for field in run_analyze.WELD_CURRENT_STAT_FIELDS:
                    value = _finite_or_none(item.get(field))
                    if value is not None:
                        result[field] = value
                if len(result) > 1:
                    return run_analyze._apply_weld_mid_percentiles(result)
        except Exception:
            pass

    try:
        return _import_run_analyze().current_stats_from_weld_h5(analyze_weld_path)
    except Exception:
        return None


def _resolve_analyze_profile_path_for_experiment(experiment_id, filename):
    folder_path, error = _resolve_analyze_folder_for_experiment(experiment_id)
    if error:
        return None, error

    profile_path = _find_generated_file(folder_path, filename)
    if profile_path is None:
        return None, f"{filename} nicht gefunden in {folder_path.name}."

    return profile_path, None


def _load_analyze_profile_graph(profile_path, *, x_min=None, x_max=None, x_field="x_mm"):
    with profile_path.open("r", encoding="utf-8") as handle:
        document = json.load(handle)

    if not isinstance(document, dict):
        raise ValueError("Ungültiges Profil-JSON.")

    x_values = document.get(x_field) or document.get("x_mm") or []
    z_field = "z_mm" if "z_mm" in document else "median_z_mm"
    z_values = document.get(z_field) or []
    x_bounds = _axis_bounds(x_values)
    effective_max = _compute_zoom_max_points(
        SCANNING_GRAPH_MAX_POINTS,
        x_min,
        x_max,
        x_bounds["min"] if x_bounds else None,
        x_bounds["max"] if x_bounds else None,
        GRAPH_ZOOM_MAX_POINTS_SCAN,
    )
    x_filtered, z_filtered = _filter_points_by_axis_range(x_values, z_values, x_min, x_max)
    x_filtered, z_filtered = _downsample_profile_points(x_filtered, z_filtered, effective_max)

    payload = dict(document)
    payload[x_field] = x_filtered.tolist()
    if z_field in payload:
        payload[z_field] = z_filtered.tolist()
    payload["x_bounds"] = x_bounds
    payload["point_count"] = int(len(x_filtered))
    return payload


def _experiment_has_valid_analyze(experiment_id):
    try:
        analyze_folder = _get_experiment_analyze_folder(experiment_id)
    except ValueError:
        return False

    if not analyze_folder:
        return False

    return (GENERATE_DATA_DIR / analyze_folder).is_dir()


def _experiment_has_valid_scan(experiment_id):
    scan_path, _error = _resolve_scan_path_for_experiment(experiment_id)
    return scan_path is not None


def _resolve_h5_path_for_experiment(experiment_id):
    try:
        h5_filename = _get_experiment_h5_filename(experiment_id)
    except ValueError as exc:
        return None, str(exc)

    if not h5_filename:
        return None, "Keine H5-Datei für diese ID."

    h5_path = ACQUESITION_WELDING_DATA_DIR / h5_filename
    if not h5_path.is_file():
        return None, f"H5-Datei nicht gefunden: {h5_filename}"

    return h5_path, None


def _experiment_has_valid_weld(experiment_id):
    h5_path, _error = _resolve_h5_path_for_experiment(experiment_id)
    return h5_path is not None


def _welding_graph_stride(sample_count, max_points):
    if sample_count <= 0 or sample_count <= max_points:
        return 1
    return max(1, (sample_count + max_points - 1) // max_points)


def _h5_searchsorted(dataset, value, sample_count, side="left"):
    lo = 0
    hi = sample_count
    while lo < hi:
        mid = (lo + hi) // 2
        if float(dataset[mid]) < value:
            lo = mid + 1
        else:
            hi = mid

    if side == "right":
        while lo < sample_count and float(dataset[lo]) <= value:
            lo += 1
    return lo


def _time_slice_indices(time_dataset, sample_count, time_min=None, time_max=None):
    if time_min is None or time_max is None or sample_count <= 0:
        return 0, sample_count

    lo = min(time_min, time_max)
    hi = max(time_min, time_max)
    slice_start = _h5_searchsorted(time_dataset, lo, sample_count, side="left")
    slice_end = _h5_searchsorted(time_dataset, hi, sample_count, side="right")
    slice_end = max(slice_start + 1, min(sample_count, slice_end))
    return slice_start, slice_end


def _read_h5_dataset_for_graph(dataset, max_points, *, step=None):
    sample_count = int(dataset.shape[0]) if dataset.shape else 0
    if sample_count <= 0:
        return np.array([], dtype=float)

    read_step = step if step is not None else _welding_graph_stride(sample_count, max_points)
    if read_step <= 1 and sample_count <= max_points:
        return np.asarray(dataset, dtype=float)

    values = np.asarray(dataset[::read_step], dtype=float)
    if values.size > max_points:
        values = values[:max_points]
    return values


def _channel_kind_from_h5_attrs(label, units) -> str:
    label_l = str(label or "").strip().lower()
    units_l = str(units or "").strip().lower()
    if label_l in {"strom", "current"} or units_l in {"a", "amp", "ampere"}:
        return "current"
    if label_l in {"spannung", "voltage"} or units_l in {"v", "volt", "volts"}:
        return "voltage"
    if label_l in {"power", "leistung"} or units_l in {"w", "watt", "watts"}:
        return "power"
    return "unknown"


def _infer_legacy_channel_kinds(channels: list[dict[str, object]]) -> None:
    if not channels:
        return

    by_key = {str(channel["key"]): channel for channel in channels}
    channel_0 = by_key.get("channel_0")
    channel_1 = by_key.get("channel_1")
    if channel_0 is None or channel_1 is None:
        return

    kind_0 = str(channel_0.get("kind") or "unknown")
    kind_1 = str(channel_1.get("kind") or "unknown")
    if kind_0 != "unknown" and kind_1 != "unknown":
        return

    # Legacy layout: channel_0 = voltage, channel_1 = current.
    if kind_0 == "unknown":
        channel_0["kind"] = "voltage"
    if kind_1 == "unknown":
        channel_1["kind"] = "current"


def _canonical_weld_channel_name(kind: str, units: str) -> str:
    unit_text = str(units or "").strip()
    if kind == "current":
        return f"Strom [{unit_text or 'A'}]"
    if kind == "voltage":
        return f"Spannung [{unit_text or 'V'}]"
    if kind == "power":
        return f"Leistung [{unit_text or 'W'}]"
    return ""


def _normalize_weld_graph_channels(channels: list[dict[str, object]]) -> list[dict[str, object]]:
    """Map H5 channels to canonical German names and stable kind order."""
    if not channels:
        return channels

    for channel in channels:
        label = str(channel.get("label") or "")
        units = str(channel.get("units") or "")
        kind = _channel_kind_from_h5_attrs(label, units)
        channel["kind"] = kind

    _infer_legacy_channel_kinds(channels)

    kind_order = {"current": 0, "voltage": 1, "power": 2, "unknown": 3}
    channels.sort(
        key=lambda channel: (
            kind_order.get(str(channel.get("kind") or "unknown"), 9),
            str(channel.get("key") or ""),
        ),
    )

    normalized: list[dict[str, object]] = []
    for channel in channels:
        kind = str(channel.get("kind") or "unknown")
        units = str(channel.get("units") or "")
        canonical_name = _canonical_weld_channel_name(kind, units)
        normalized.append(
            {
                "key": channel["key"],
                "name": canonical_name or str(channel.get("name") or channel["key"]),
                "kind": kind,
                "values": channel["values"],
            }
        )
    return normalized


def _format_h5_channel_name(dataset, fallback_name):
    label = dataset.attrs.get("label")
    units = dataset.attrs.get("units")
    if label and units:
        return f"{label} [{units}]"
    if label:
        return str(label)
    return fallback_name


def _load_welding_graph_from_h5(h5_path, *, time_min=None, time_max=None, max_points=None):
    with h5py.File(h5_path, "r") as h5_file:
        if "time_s" not in h5_file:
            raise ValueError('Datensatz "time_s" nicht gefunden.')

        time_dataset = h5_file["time_s"]
        sample_count = int(time_dataset.shape[0]) if time_dataset.shape else 0
        if sample_count <= 0:
            raise ValueError("Keine Messpunkte in H5-Datei gefunden.")

        time_bounds = {
            "min": float(time_dataset[0]),
            "max": float(time_dataset[-1]),
        }
        if time_bounds["max"] < time_bounds["min"]:
            time_bounds = {"min": time_bounds["max"], "max": time_bounds["min"]}

        slice_start, slice_end = _time_slice_indices(
            time_dataset,
            sample_count,
            time_min,
            time_max,
        )
        slice_count = max(slice_end - slice_start, 1)
        effective_max = max_points or WELDING_GRAPH_MAX_POINTS
        step = _welding_graph_stride(slice_count, effective_max)
        time_s = np.asarray(time_dataset[slice_start:slice_end:step], dtype=float)

        channels = []
        for key in sorted(name for name in h5_file.keys() if name.startswith("channel_")):
            dataset = h5_file[key]
            values = np.asarray(dataset[slice_start:slice_end:step], dtype=float)
            point_count = min(time_s.size, values.size)
            channels.append(
                {
                    "key": key,
                    "label": str(dataset.attrs.get("label", key)),
                    "units": str(dataset.attrs.get("units", "")),
                    "name": _format_h5_channel_name(dataset, key),
                    "values": values[:point_count],
                }
            )
            time_s = time_s[:point_count]

    if not channels:
        raise ValueError("Keine Messkanäle in H5-Datei gefunden.")

    channels = _normalize_weld_graph_channels(channels)

    full_span = time_bounds["max"] - time_bounds["min"]
    sample_rate_hz = None
    if full_span > 0 and sample_count > 1:
        sample_rate_hz = (sample_count - 1) / full_span

    return {
        "time_s": np.asarray(time_s, dtype=float).tolist(),
        "time_bounds": time_bounds,
        "point_count": int(len(time_s)),
        "raw_sample_count": sample_count,
        "graph_max_points": effective_max,
        "sample_rate_hz": sample_rate_hz,
        "channels": [
            {
                "key": channel["key"],
                "name": channel["name"],
                "kind": channel.get("kind"),
                "values": np.asarray(channel["values"], dtype=float).tolist(),
            }
            for channel in channels
        ],
    }



def _delete_analyze_folder(folder_name):
    if not folder_name:
        return None

    safe_folder = _sanitize_analyze_folder_name(folder_name)
    if not safe_folder:
        return None

    folder_path = (GENERATE_DATA_DIR / safe_folder).resolve()
    generate_root = GENERATE_DATA_DIR.resolve()
    if generate_root not in folder_path.parents or not folder_path.is_dir():
        return None

    shutil.rmtree(folder_path)
    return safe_folder


def _delete_existing_analyze_folder(experiment_id):
    deleted = None
    for folder_name in _list_analyze_folders_for_experiment(experiment_id):
        deleted = _delete_analyze_folder(folder_name) or deleted
    return deleted


def _get_weld_speed_m_per_min_from_row(row):
    if versuchsuebersicht_data is None or row is None:
        return None

    columns = versuchsuebersicht_data["columns"]
    column = _find_column(columns, "WS [m/min]")
    if column is None:
        return None

    value = row.get(column)
    if value is None or pd.isna(value):
        return None

    try:
        speed = float(value)
    except (TypeError, ValueError):
        return None

    if speed <= 0:
        return None
    return speed


def _get_optional_float_from_row(row, column_name):
    if versuchsuebersicht_data is None or row is None:
        return None

    column = _find_column(versuchsuebersicht_data["columns"], column_name)
    if column is None:
        return None

    value = row.get(column)
    if value is None or pd.isna(value):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _get_generate_weld_params_from_row(row):
    if versuchsuebersicht_data is None or row is None:
        return {
            "path_id": None,
            "wfs_m_per_min": None,
            "ws_m_per_min": None,
        }

    columns = versuchsuebersicht_data["columns"]
    path_col = _find_column(columns, "PATH ID")
    path_id = None
    if path_col is not None:
        raw_path = row.get(path_col)
        if raw_path is not None and not pd.isna(raw_path):
            path_id = str(raw_path).strip().upper() or None

    wfs = _get_optional_float_from_row(row, "WFS [m/min]")
    ws = _get_weld_speed_m_per_min_from_row(row)
    return {
        "path_id": path_id,
        "wfs_m_per_min": round(wfs, 6) if wfs is not None else None,
        "ws_m_per_min": round(ws, 6) if ws is not None else None,
    }


def _json_safe(value):
    if isinstance(value, (float, np.floating)):
        number = float(value)
        if not np.isfinite(number):
            return None
        return number
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _resolve_analyze_characteristics_path_for_experiment(experiment_id):
    folder_path, error = _resolve_analyze_folder_for_experiment(experiment_id)
    if error:
        return None, error

    json_path = _find_generated_file(folder_path, ANALYZE_CHARACTERISTICS_FILENAME)
    if json_path is None:
        return None, f"{ANALYZE_CHARACTERISTICS_FILENAME} nicht gefunden in {folder_path.name}."

    return json_path, None


def _resolve_analyze_grenzen_path_for_experiment(experiment_id):
    folder_path, error = _resolve_analyze_folder_for_experiment(experiment_id)
    if error:
        return None, error

    json_path = _find_generated_file(folder_path, ANALYZE_GRENZEN_FILENAME)
    if json_path is None:
        return None, f"{ANALYZE_GRENZEN_FILENAME} nicht gefunden in {folder_path.name}."

    return json_path, None


def _filter_grenzen_for_time_range(document, time_min=None, time_max=None):
    if not isinstance(document, dict):
        return None

    if time_min is None or time_max is None or time_max <= time_min:
        return document

    filtered = dict(document)
    regions = []
    for item in document.get("regions") or []:
        if not isinstance(item, dict):
            continue
        start_s = float(item.get("start_s", 0.0))
        end_s = float(item.get("end_s", 0.0))
        if end_s < time_min or start_s > time_max:
            continue
        clipped = dict(item)
        clipped["start_s"] = round(max(start_s, time_min), 6)
        clipped["end_s"] = round(min(end_s, time_max), 6)
        regions.append(clipped)
    filtered["regions"] = regions
    return filtered


def _current_row_from_characteristics_document(document) -> dict | None:
    if not isinstance(document, dict):
        return None
    run_analyze = _import_run_analyze()
    for item in document.get("weld") or []:
        if (
            isinstance(item, dict)
            and run_analyze._normalize_weld_quantity(item.get("quantity"))
            == run_analyze.WELD_CURRENT_QUANTITY
        ):
            return item
    return None


def _grenzen_for_cropped_weld(analyze_weld_path, *, time_min=None, time_max=None):
    folder_path = _generated_folder_root(analyze_weld_path)
    grenzen_path = _find_generated_file(folder_path, ANALYZE_GRENZEN_FILENAME)
    if grenzen_path is not None:
        try:
            document = _import_run_analyze().load_grenzen(grenzen_path)
            if int(document.get("version") or 0) < 6 or not document.get("regions") or any(
                not isinstance(item, dict) or not item.get("fit")
                or (
                    item.get("category") == "fall"
                    and item.get("fit", {}).get("quad_a_per_s2") is None
                )
                for item in document.get("regions") or []
            ):
                raise ValueError("Grenzen-JSON veraltet oder unvollständig.")
            return _filter_grenzen_for_time_range(document, time_min, time_max)
        except Exception:
            pass

    try:
        run_analyze = _import_run_analyze()
        time_s, channels = run_analyze._load_weld_h5_channels(analyze_weld_path)
        current_row = None
        characteristics_path = folder_path / ANALYZE_CHARACTERISTICS_FILENAME
        if characteristics_path.is_file():
            characteristics = run_analyze.load_characteristics(characteristics_path)
            current_row = _current_row_from_characteristics_document(characteristics)
        if current_row is None:
            current_row = run_analyze.build_weld_current_characteristic_row(time_s, channels)
        document = run_analyze.build_weld_grenzen_document(time_s, channels, current_row)
    except Exception:
        return None

    return _filter_grenzen_for_time_range(document, time_min, time_max)


def _load_analyze_characteristics_document(experiment_id):
    characteristics_path, error = _resolve_analyze_characteristics_path_for_experiment(
        experiment_id,
    )
    if error:
        return None, None, error

    document = _import_run_analyze().load_characteristics(characteristics_path)
    return characteristics_path, document, None


def _finite_or_none(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(number):
        return None
    return number


def _get_characteristic_keys() -> tuple[str, ...]:
    return _import_run_analyze().list_all_characteristic_keys()


def _get_target_characteristic_keys() -> tuple[str, ...]:
    return _import_run_analyze().SCAN_CHARACTERISTIC_FIELDS


def _get_weld_characteristic_keys() -> tuple[str, ...]:
    return _import_run_analyze().list_weld_characteristic_keys()


@app.context_processor
def inject_nav_context():
    return {
        "load_status": _get_load_status(),
        "data_path": _get_data_path_display(),
        "data_path_suggestions": DATA_PATH_SUGGESTIONS,
        "table_column_labels": GENERATE_TABLE_COLUMN_LABELS,
        "characteristic_rows": _get_characteristic_keys(),
        "target_characteristic_keys": _get_target_characteristic_keys(),
        "weld_characteristic_keys": _get_weld_characteristic_keys(),
        "scan_generate_keys": _import_run_analyze().SCAN_GENERATE_KEYS,
        "weld_generate_keys": _import_run_analyze().WELD_GENERATE_KEYS,
    }


@app.get("/")
def index():
    return redirect(url_for("generate"))


@app.get("/generate")
def generate():
    table_rows = _get_generate_table_rows()
    return render_template(
        "generate.html",
        active_page="generate",
        table_rows=table_rows,
        table_columns=GENERATE_TABLE_COLUMNS,
    )


@app.get("/view")
def view():
    table_rows = _get_view_table_rows()
    view_excel_by_id = {}
    for row in table_rows:
        experiment_id = str(row.get("ID", "")).strip().upper()
        if not experiment_id:
            continue
        view_excel_by_id[experiment_id] = {
            "count": row.get("COUNT", ""),
            "id": experiment_id,
            "path_id": row.get("PATH ID", ""),
            "wfs": row.get("WFS", ""),
            "ws": row.get("WS", ""),
            "series": row.get("SERIES", ""),
            "number": row.get("NUMBER", ""),
        }
    return render_template(
        "view.html",
        active_page="view",
        table_rows=table_rows,
        table_columns=GENERATE_TABLE_COLUMNS,
        view_excel_by_id=view_excel_by_id,
    )


@app.get("/api/view/<experiment_id>/excel-values")
def get_view_excel_values(experiment_id):
    if versuchsuebersicht_data is None:
        return jsonify(error="Keine Versuchsübersicht geladen. Bitte oben auf Laden klicken."), 400

    if not re.fullmatch(r"[A-Z]{3}", experiment_id):
        return jsonify(error="ID muss aus 3 Großbuchstaben bestehen."), 400

    row = versuchsuebersicht_data["id_index"].get(_normalize_id(experiment_id))
    if row is None:
        return jsonify(error="ID nicht gefunden."), 404

    return jsonify(
        id=experiment_id,
        excel=_json_safe(_get_view_excel_values_for_row(row)),
    )


@app.post("/api/view/export")
def export_view_values():
    if versuchsuebersicht_data is None:
        return jsonify(error="Keine Versuchsübersicht geladen. Bitte oben auf Laden klicken."), 400

    payload = request.get_json(silent=True) or {}
    raw_ids = payload.get("ids")
    raw_columns = payload.get("columns")
    if not isinstance(raw_ids, list) or not raw_ids:
        return jsonify(error="Keine IDs für den Export angegeben."), 400
    if not isinstance(raw_columns, list) or not raw_columns:
        return jsonify(error="Keine Spalten für den Export ausgewählt."), 400

    column_labels = _get_view_value_column_labels()
    valid_column_order = _get_view_value_column_order()
    valid_keys = set(valid_column_order)

    columns: list[str] = []
    for raw_key in raw_columns:
        key = str(raw_key).strip()
        if key in valid_keys and key not in columns:
            columns.append(key)
    if not columns:
        return jsonify(error="Keine gültigen Spalten für den Export ausgewählt."), 400

    experiment_ids: list[str] = []
    for raw_id in raw_ids:
        normalized = _normalize_id(raw_id)
        if normalized and normalized not in experiment_ids:
            experiment_ids.append(normalized)
    if not experiment_ids:
        return jsonify(error="Keine gültigen IDs für den Export angegeben."), 400

    export_rows = []
    for experiment_id in experiment_ids:
        source_row = versuchsuebersicht_data["id_index"].get(experiment_id)
        excel_values = _get_view_excel_values_for_row(source_row)
        characteristics_map: dict[str, float] = {}
        try:
            _path, document, error = _load_analyze_characteristics_document(experiment_id)
            if not error and document:
                characteristics_map = _characteristics_document_to_value_map(document)
        except Exception:
            characteristics_map = {}

        row = {"ID": experiment_id}
        for column_key in columns:
            if column_key == "id":
                continue
            header = column_labels.get(column_key, column_key)
            row[header] = _resolve_view_export_cell(
                column_key,
                experiment_id,
                excel_values,
                characteristics_map,
            )
        export_rows.append(row)

    value_columns = [key for key in columns if key != "id"]
    sheet_columns = ["ID"] + [column_labels[key] for key in value_columns]
    dataframe = pd.DataFrame(export_rows, columns=sheet_columns)
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, sheet_name="values")
    buffer.seek(0)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"value_export_{stamp}.xlsx"
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.get("/select")
def select_page():
    table_rows = _get_generate_table_rows()
    return render_template(
        "select.html",
        active_page="select",
        table_rows=table_rows,
        table_columns=GENERATE_TABLE_COLUMNS,
    )


@app.post("/api/generate/<experiment_id>")
def run_generate(experiment_id):
    if versuchsuebersicht_path is None or versuchsuebersicht_data is None:
        return jsonify(error="Keine Versuchsübersicht geladen. Bitte oben auf Laden klicken."), 400

    if not re.fullmatch(r"[A-Z]{3}", experiment_id):
        return jsonify(error="ID muss aus 3 Großbuchstaben bestehen."), 400

    row = versuchsuebersicht_data["id_index"].get(_normalize_id(experiment_id))
    if row is None:
        return jsonify(error="ID nicht gefunden."), 404

    scan_path = None
    scan_error = None
    if _experiment_has_valid_scan(experiment_id):
        scan_path, scan_error = _resolve_scan_path_for_experiment(experiment_id)

    h5_path = None
    h5_error = None
    if _experiment_has_valid_weld(experiment_id):
        h5_path, h5_error = _resolve_h5_path_for_experiment(experiment_id)

    if scan_path is None and h5_path is None:
        messages = []
        if scan_error:
            messages.append(scan_error)
        if h5_error:
            messages.append(h5_error)
        if not messages:
            messages.append("Für diese ID liegt keine gültige Scan- oder H5-Datei vor.")
        return jsonify(error=" ".join(messages)), 400

    payload = request.get_json(silent=True) or {}
    run_analyze_module = _import_run_analyze()
    scan_generate_options = payload.get("scan")
    weld_generate_options = payload.get("weld")

    try:
        scan_options_normalized = run_analyze_module.normalize_generate_options(
            scan_generate_options,
            run_analyze_module.SCAN_GENERATE_KEYS,
        )
        weld_options_normalized = run_analyze_module.normalize_generate_options(
            weld_generate_options,
            run_analyze_module.WELD_GENERATE_KEYS,
        )
        scan_options = run_analyze_module.resolve_scan_generate_options(scan_options_normalized)
        weld_options = run_analyze_module.resolve_weld_generate_options(weld_options_normalized)
        has_scan_selection = scan_path is not None and any(scan_options.values())
        has_weld_selection = h5_path is not None and any(weld_options.values())
        if not has_scan_selection and not has_weld_selection:
            return jsonify(error="Keine Generate-Optionen ausgewählt."), 400
    except Exception as exc:
        return jsonify(error=f"Ungültige Generate-Optionen: {exc}"), 400

    try:
        scan_speed_mm_s = None
        scan_duration_s = None
        if scan_path is not None:
            scan_speed_mm_s, scan_duration_s = _get_scan_geometry_from_row(row)
        weld_speed_m_per_min = None
        if h5_path is not None:
            weld_speed_m_per_min = _get_weld_speed_m_per_min_from_row(row)

        existing_folder_name = _get_experiment_analyze_folder(experiment_id)
        output_folder = None
        deleted_artifacts = []
        if existing_folder_name:
            output_folder = (GENERATE_DATA_DIR / existing_folder_name).resolve()
            generate_root = GENERATE_DATA_DIR.resolve()
            if generate_root in output_folder.parents and output_folder.is_dir():
                deleted_artifacts = run_analyze_module.delete_regenerate_artifacts(
                    output_folder,
                    scan_options_normalized,
                    weld_options_normalized,
                )

        result = run_analyze_module.run_analyze(
            experiment_id,
            GENERATE_DATA_DIR,
            scan_path=scan_path,
            weld_path=h5_path,
            weld_config=_build_weld_config(),
            scan_speed_mm_s=scan_speed_mm_s,
            scan_duration_s=scan_duration_s,
            weld_speed_m_per_min=weld_speed_m_per_min,
            scan_generate_options=scan_generate_options,
            weld_generate_options=weld_generate_options,
            output_folder=output_folder,
        )
        result["has_analyze"] = _experiment_has_valid_analyze(experiment_id)
        if deleted_artifacts:
            result["deleted_artifacts"] = deleted_artifacts
        return jsonify(**result)
    except Exception as exc:
        return jsonify(error=f"Probendaten konnten nicht generiert werden: {exc}"), 500


def _aggregate_generate_artifact_status(present_count: int, total_count: int) -> str:
    if total_count <= 0 or present_count <= 0:
        return "none"
    if present_count >= total_count:
        return "all"
    return "partial"


def _build_generate_artifact_status(valid_ids: list[str]) -> dict:
    run_analyze_module = _import_run_analyze()
    total_count = len(valid_ids)
    scan_status = {key: "none" for key in run_analyze_module.SCAN_GENERATE_KEYS}
    weld_status = {key: "none" for key in run_analyze_module.WELD_GENERATE_KEYS}

    if total_count == 0:
        return {
            "id_count": 0,
            "scan": scan_status,
            "weld": weld_status,
        }

    scan_present = {key: 0 for key in run_analyze_module.SCAN_GENERATE_KEYS}
    weld_present = {key: 0 for key in run_analyze_module.WELD_GENERATE_KEYS}

    for experiment_id in valid_ids:
        folder_path, _error = _resolve_analyze_folder_for_experiment(experiment_id)
        if folder_path is None:
            continue

        for key in run_analyze_module.SCAN_GENERATE_KEYS:
            if run_analyze_module.experiment_has_generate_artifact(
                folder_path,
                section="scan",
                key=key,
            ):
                scan_present[key] += 1

        for key in run_analyze_module.WELD_GENERATE_KEYS:
            if run_analyze_module.experiment_has_generate_artifact(
                folder_path,
                section="weld",
                key=key,
            ):
                weld_present[key] += 1

    for key, count in scan_present.items():
        scan_status[key] = _aggregate_generate_artifact_status(count, total_count)
    for key, count in weld_present.items():
        weld_status[key] = _aggregate_generate_artifact_status(count, total_count)

    return {
        "id_count": total_count,
        "scan": scan_status,
        "weld": weld_status,
    }


@app.post("/api/generate/status")
def get_generate_status():
    payload = request.get_json(silent=True) or {}
    raw_ids = payload.get("ids")
    if not isinstance(raw_ids, list):
        return jsonify(error="ids muss eine Liste sein."), 400

    valid_ids = []
    seen = set()
    for raw_id in raw_ids:
        normalized = _normalize_id(raw_id)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        valid_ids.append(normalized)

    return jsonify(_build_generate_artifact_status(valid_ids))


@app.get("/api/generate/<experiment_id>/params")
def get_generate_params(experiment_id):
    if versuchsuebersicht_data is None:
        return jsonify(error="Keine Versuchsübersicht geladen. Bitte oben auf Laden klicken."), 400

    if not re.fullmatch(r"[A-Z]{3}", experiment_id):
        return jsonify(error="ID muss aus 3 Großbuchstaben bestehen."), 400

    row = versuchsuebersicht_data["id_index"].get(_normalize_id(experiment_id))
    if row is None:
        return jsonify(error="ID nicht gefunden."), 404

    return jsonify(
        id=experiment_id,
        params=_get_generate_weld_params_from_row(row),
        excel=_json_safe(_get_view_excel_values_for_row(row)),
    )


@app.get("/api/generate/<experiment_id>/graph")
def get_generate_graph(experiment_id):
    if versuchsuebersicht_data is None:
        return jsonify(error="Keine Versuchsübersicht geladen. Bitte oben auf Laden klicken."), 400

    if not re.fullmatch(r"[A-Z]{3}", experiment_id):
        return jsonify(error="ID muss aus 3 Großbuchstaben bestehen."), 400

    profile_index = request.args.get("profile", default=0, type=int)
    if profile_index is None or profile_index < 0:
        return jsonify(error="Profilindex muss >= 0 sein."), 400

    try:
        analyze_path, error = _resolve_analyze_path_for_experiment(experiment_id)
        if error:
            status = 404 if (
                error.startswith("Kein Analyse-Ordner")
                or error.startswith("cropped_scan.json nicht gefunden")
            ) else 400
            return jsonify(error=error), status

        graph_data = _load_scanning_profile_graph(
            analyze_path,
            profile_index,
            **_scan_graph_kwargs_from_request(),
        )
        return jsonify(id=experiment_id, **graph_data)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception as exc:
        return jsonify(error=f"Fehler beim Lesen der Analyse-Datei: {exc}"), 500


@app.get("/api/generate/<experiment_id>/filtered")
def get_generate_filtered(experiment_id):
    if versuchsuebersicht_data is None:
        return jsonify(error="Keine Versuchsübersicht geladen. Bitte oben auf Laden klicken."), 400

    if not re.fullmatch(r"[A-Z]{3}", experiment_id):
        return jsonify(error="ID muss aus 3 Großbuchstaben bestehen."), 400

    profile_index = request.args.get("profile", default=0, type=int)
    if profile_index is None or profile_index < 0:
        return jsonify(error="Profilindex muss >= 0 sein."), 400

    try:
        filtered_path, error = _resolve_analyze_profile_path_for_experiment(
            experiment_id,
            ANALYZE_FILTERED_FILENAME,
        )
        if error:
            status = 404 if (
                error.startswith("Kein Analyse-Ordner")
                or error.startswith(f"{ANALYZE_FILTERED_FILENAME} nicht gefunden")
            ) else 400
            return jsonify(error=error), status

        graph_data = _load_scanning_profile_graph(
            filtered_path,
            profile_index,
            **_scan_graph_kwargs_from_request(),
        )
        return jsonify(id=experiment_id, **graph_data)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception as exc:
        return jsonify(error=f"Fehler beim Lesen von {ANALYZE_FILTERED_FILENAME}: {exc}"), 500


@app.get("/api/generate/<experiment_id>/heatmap")
def get_generate_heatmap(experiment_id):
    if versuchsuebersicht_data is None:
        return jsonify(error="Keine Versuchsübersicht geladen. Bitte oben auf Laden klicken."), 400

    if not re.fullmatch(r"[A-Z]{3}", experiment_id):
        return jsonify(error="ID muss aus 3 Großbuchstaben bestehen."), 400

    try:
        analyze_path, error = _resolve_analyze_path_for_experiment(experiment_id)
        if error:
            status = 404 if (
                error.startswith("Kein Analyse-Ordner")
                or error.startswith("cropped_scan.json nicht gefunden")
            ) else 400
            return jsonify(error=error), status

        heatmap_data = _load_generate_scan_heatmap(analyze_path)
        return jsonify(id=experiment_id, **heatmap_data)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception as exc:
        return jsonify(error=f"Fehler beim Lesen der Analyse-Heatmap: {exc}"), 500


@app.get("/api/generate/<experiment_id>/heatmap-64")
def get_generate_heatmap_64(experiment_id):
    if versuchsuebersicht_data is None:
        return jsonify(error="Keine Versuchsübersicht geladen. Bitte oben auf Laden klicken."), 400

    if not re.fullmatch(r"[A-Z]{3}", experiment_id):
        return jsonify(error="ID muss aus 3 Großbuchstaben bestehen."), 400

    try:
        grid_path, error = _resolve_64_64_scan_path_for_experiment(experiment_id)
        if error:
            status = 404 if (
                error.startswith("Kein Analyse-Ordner")
                or error.startswith(f"{ANALYZE_64_64_SCAN_FILENAME} nicht gefunden")
            ) else 400
            return jsonify(error=error), status

        heatmap_data = _load_grid_scan_heatmap(grid_path)
        return jsonify(id=experiment_id, **heatmap_data)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception as exc:
        return jsonify(error=f"Fehler beim Lesen der 64×64-Heatmap: {exc}"), 500


@app.get("/api/generate/<experiment_id>/x-profile")
def get_generate_x_profile(experiment_id):
    if versuchsuebersicht_data is None:
        return jsonify(error="Keine Versuchsübersicht geladen. Bitte oben auf Laden klicken."), 400

    if not re.fullmatch(r"[A-Z]{3}", experiment_id):
        return jsonify(error="ID muss aus 3 Großbuchstaben bestehen."), 400

    try:
        profile_path, error = _resolve_analyze_profile_path_for_experiment(
            experiment_id,
            ANALYZE_X_PROFILE_FILENAME,
        )
        if error:
            status = 404 if (
                error.startswith("Kein Analyse-Ordner")
                or error.startswith(f"{ANALYZE_X_PROFILE_FILENAME} nicht gefunden")
            ) else 400
            return jsonify(error=error), status

        scan_kwargs = _scan_graph_kwargs_from_request()
        graph_data = _load_analyze_profile_graph(profile_path, **scan_kwargs)
        return jsonify(id=experiment_id, **graph_data)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception as exc:
        return jsonify(error=f"Fehler beim Lesen von {ANALYZE_X_PROFILE_FILENAME}: {exc}"), 500


@app.get("/api/generate/<experiment_id>/y-profile")
def get_generate_y_profile(experiment_id):
    if versuchsuebersicht_data is None:
        return jsonify(error="Keine Versuchsübersicht geladen. Bitte oben auf Laden klicken."), 400

    if not re.fullmatch(r"[A-Z]{3}", experiment_id):
        return jsonify(error="ID muss aus 3 Großbuchstaben bestehen."), 400

    try:
        profile_path, error = _resolve_analyze_profile_path_for_experiment(
            experiment_id,
            ANALYZE_Y_PROFILE_FILENAME,
        )
        if error:
            status = 404 if (
                error.startswith("Kein Analyse-Ordner")
                or error.startswith(f"{ANALYZE_Y_PROFILE_FILENAME} nicht gefunden")
            ) else 400
            return jsonify(error=error), status

        graph_data = _load_analyze_profile_graph(profile_path, x_field="y_mm")
        return jsonify(id=experiment_id, **graph_data)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception as exc:
        return jsonify(error=f"Fehler beim Lesen von {ANALYZE_Y_PROFILE_FILENAME}: {exc}"), 500


@app.get("/api/generate/<experiment_id>/weld-graph")
def get_generate_weld_graph(experiment_id):
    if versuchsuebersicht_data is None:
        return jsonify(error="Keine Versuchsübersicht geladen. Bitte oben auf Laden klicken."), 400

    if not re.fullmatch(r"[A-Z]{3}", experiment_id):
        return jsonify(error="ID muss aus 3 Großbuchstaben bestehen."), 400

    try:
        analyze_weld_path, error = _resolve_analyze_weld_path_for_experiment(experiment_id)
        if error:
            status = 404 if error.startswith("Kein Analyse-Ordner") else 400
            if error.startswith("cropped_weld.h5 nicht gefunden"):
                status = 404
            return jsonify(error=error), status

        analyze_weld_filename = analyze_weld_path.name
        graph_data = _load_welding_graph_from_h5(
            analyze_weld_path,
            **_weld_graph_kwargs_from_request(),
        )

        row = versuchsuebersicht_data["id_index"].get(_normalize_id(experiment_id))
        params = _get_generate_weld_params_from_row(row)
        current_stats = _current_stats_for_cropped_weld(analyze_weld_path)
        response = {
            "id": experiment_id,
            "h5file": analyze_weld_filename,
            "params": params,
            **graph_data,
        }
        if current_stats is not None:
            response["current_stats"] = current_stats
        return jsonify(response)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception as exc:
        return jsonify(error=f"Fehler beim Lesen der Analyse-H5-Datei: {exc}"), 500


def _get_generate_derived_weld_graph(experiment_id, filename):
    if versuchsuebersicht_data is None:
        return jsonify(error="Keine Versuchsübersicht geladen. Bitte oben auf Laden klicken."), 400

    if not re.fullmatch(r"[A-Z]{3}", experiment_id):
        return jsonify(error="ID muss aus 3 Großbuchstaben bestehen."), 400

    try:
        h5_path, error = _resolve_analyze_profile_path_for_experiment(experiment_id, filename)
        if error:
            status = 404 if (
                error.startswith("Kein Analyse-Ordner")
                or error.startswith(f"{filename} nicht gefunden")
            ) else 400
            return jsonify(error=error), status

        graph_data = _load_welding_graph_from_h5(
            h5_path,
            **_weld_graph_kwargs_from_request(),
        )
        return jsonify(id=experiment_id, h5file=h5_path.name, **graph_data)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception as exc:
        return jsonify(error=f"Fehler beim Lesen von {filename}: {exc}"), 500


@app.get("/api/generate/<experiment_id>/power-graph")
def get_generate_power_graph(experiment_id):
    return _get_generate_derived_weld_graph(experiment_id, ANALYZE_POWER_FILENAME)


@app.get("/api/scanning/<experiment_id>/graph")
def get_scanning_graph(experiment_id):
    if versuchsuebersicht_data is None:
        return jsonify(error="Keine Versuchsübersicht geladen. Bitte oben auf Laden klicken."), 400

    if not re.fullmatch(r"[A-Z]{3}", experiment_id):
        return jsonify(error="ID muss aus 3 Großbuchstaben bestehen."), 400

    profile_index = request.args.get("profile", default=0, type=int)
    if profile_index is None or profile_index < 0:
        return jsonify(error="Profilindex muss >= 0 sein."), 400

    try:
        scan_path, error = _resolve_scan_path_for_experiment(experiment_id)
        if error:
            status = 404 if error.startswith("Keine Scan-Datei") else 400
            if error.startswith("Scan-Datei nicht gefunden"):
                status = 404
            return jsonify(error=error), status

        graph_data = _load_scanning_profile_graph(
            scan_path,
            profile_index,
            **_scan_graph_kwargs_from_request(),
        )
        return jsonify(id=experiment_id, **graph_data)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception as exc:
        return jsonify(error=f"Fehler beim Lesen der Scan-Datei: {exc}"), 500


@app.get("/api/scanning/<experiment_id>/profile-y")
def get_scanning_profile_y(experiment_id):
    if versuchsuebersicht_data is None:
        return jsonify(error="Keine Versuchsübersicht geladen. Bitte oben auf Laden klicken."), 400

    if not re.fullmatch(r"[A-Z]{3}", experiment_id):
        return jsonify(error="ID muss aus 3 Großbuchstaben bestehen."), 400

    try:
        scan_path, error = _resolve_scan_path_for_experiment(experiment_id)
        if error:
            status = 404 if error.startswith("Keine Scan-Datei") else 400
            if error.startswith("Scan-Datei nicht gefunden"):
                status = 404
            return jsonify(error=error), status

        document = _load_scan_document(scan_path)
        profiles = document.get("profiles") or []
        if not profiles:
            return jsonify(error="Keine Profile in Scan-Datei gefunden."), 404

        y_mm = _get_profile_y_mm_values(
            document,
            profiles,
            experiment_id=document.get("experiment_id"),
        )
        return jsonify(
            id=experiment_id,
            profile_count=len(y_mm),
            y_mm=y_mm,
            y_min=min(y_mm),
            y_max=max(y_mm),
        )
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception as exc:
        return jsonify(error=f"Fehler beim Lesen der Profilpositionen: {exc}"), 500


@app.get("/api/welding/<experiment_id>/graph")
def get_welding_graph(experiment_id):
    if versuchsuebersicht_data is None:
        return jsonify(error="Keine Versuchsübersicht geladen. Bitte oben auf Laden klicken."), 400

    if not re.fullmatch(r"[A-Z]{3}", experiment_id):
        return jsonify(error="ID muss aus 3 Großbuchstaben bestehen."), 400

    try:
        h5_path, error = _resolve_h5_path_for_experiment(experiment_id)
        if error:
            status = 404 if error.startswith("Keine H5-Datei") else 400
            if error.startswith("H5-Datei nicht gefunden"):
                status = 404
            return jsonify(error=error), status

        graph_data = _load_welding_graph_from_h5(
            h5_path,
            **_weld_graph_kwargs_from_request(),
        )
        return jsonify(id=experiment_id, h5file=h5_path.name, **graph_data)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception as exc:
        return jsonify(error=f"Fehler beim Lesen der H5-Datei: {exc}"), 500


@app.get("/api/generate/<experiment_id>/characteristics")
def get_generate_characteristics(experiment_id):
    if versuchsuebersicht_data is None:
        return jsonify(error="Keine Versuchsübersicht geladen. Bitte oben auf Laden klicken."), 400

    if not re.fullmatch(r"[A-Z]{3}", experiment_id):
        return jsonify(error="ID muss aus 3 Großbuchstaben bestehen."), 400

    try:
        characteristics_path, document, error = _load_analyze_characteristics_document(
            experiment_id,
        )
        if error:
            status = 404 if (
                error.startswith("Kein Analyse-Ordner")
                or "nicht gefunden" in error
            ) else 400
            return jsonify(error=error), status

        scan_fields = dict((document or {}).get("scan") or {})
        if not isinstance(scan_fields, dict):
            return jsonify(error="Ungültiges Characteristics-JSON: scan muss ein Objekt sein."), 400
        weld_rows = list((document or {}).get("weld") or [])
        return jsonify(
            id=experiment_id,
            file=characteristics_path.name,
            scan=_json_safe(scan_fields),
            weld=_json_safe(weld_rows),
        )
    except Exception as exc:
        return jsonify(error=f"Fehler beim Lesen der Characteristics: {exc}"), 500


@app.get("/api/generate/<experiment_id>/grenzen")
def get_generate_grenzen(experiment_id):
    if versuchsuebersicht_data is None:
        return jsonify(error="Keine Versuchsübersicht geladen. Bitte oben auf Laden klicken."), 400

    if not re.fullmatch(r"[A-Z]{3}", experiment_id):
        return jsonify(error="ID muss aus 3 Großbuchstaben bestehen."), 400

    try:
        analyze_weld_path, error = _resolve_analyze_weld_path_for_experiment(experiment_id)
        if error:
            status = 404 if error.startswith("Kein Analyse-Ordner") else 400
            if error.startswith("cropped_weld.h5 nicht gefunden"):
                status = 404
            return jsonify(error=error), status

        graph_kwargs = _weld_graph_kwargs_from_request()
        document = _grenzen_for_cropped_weld(
            analyze_weld_path,
            time_min=graph_kwargs.get("time_min"),
            time_max=graph_kwargs.get("time_max"),
        )
        if document is None:
            return jsonify(
                id=experiment_id,
                file=ANALYZE_GRENZEN_FILENAME,
                regions=[],
            )

        grenzen_path = _find_generated_file(
            _generated_folder_root(analyze_weld_path),
            ANALYZE_GRENZEN_FILENAME,
        )
        return jsonify(
            id=experiment_id,
            file=grenzen_path.name if grenzen_path is not None else ANALYZE_GRENZEN_FILENAME,
            **_json_safe(document),
        )
    except Exception as exc:
        return jsonify(error=f"Fehler beim Lesen der Grenzen: {exc}"), 500


@app.post("/api/load-versuchsuebersicht")
def load_versuchsuebersicht():
    body = request.get_json(silent=True) or {}
    path_str = body.get("path", "").strip()
    if not path_str:
        return jsonify(error="Bitte einen Pfad angeben."), 400

    path = _resolve_path(path_str)
    if not path.exists():
        return jsonify(error=f"Pfad nicht gefunden: {path}"), 404

    try:
        if path.is_dir():
            result = _load_data_dir(path)
        elif path.suffix.lower() in EXCEL_SUFFIXES:
            _configure_data_dirs(path.parent)
            result = _load_versuchsuebersicht_from_path(path)
        else:
            return jsonify(error="Bitte den data-Ordner oder die Versuchsübersicht angeben."), 400
        return jsonify(
            success=True,
            data_dir=str(data_dir),
            data_path=_get_data_path_display(),
            **result,
        )
    except Exception as exc:
        return jsonify(error=f"Fehler beim Laden: {exc}"), 500


@app.get("/api/versuchsuebersicht/status")
def versuchsuebersicht_status():
    status = _get_load_status()
    if versuchsuebersicht_data is None:
        return jsonify(loaded=False, **status)
    return jsonify(
        loaded=True,
        data_dir=str(data_dir) if data_dir else None,
        path=versuchsuebersicht_path,
        row_count=len(versuchsuebersicht_data["rows"]),
        column_count=len(versuchsuebersicht_data["columns"]),
        **status,
    )


@app.get("/api/patterns/<path_id>")
def get_weld_path_pattern(path_id):
    normalized = str(path_id).strip().upper()
    if normalized not in VALID_PATH_IDS:
        return jsonify(error=f"Unbekannte PATH ID: {path_id}"), 400

    pattern_path = PATTERNS_DIR / f"{normalized}.json"
    if not pattern_path.is_file():
        return jsonify(error=f"Pfadmuster {normalized} nicht gefunden."), 404

    with pattern_path.open("r", encoding="utf-8") as handle:
        paths = json.load(handle)

    if not isinstance(paths, list):
        return jsonify(error=f"Ungültiges Pfadmuster-Format in {normalized}.json."), 500

    return jsonify(path_id=normalized, paths=paths)


@app.get("/styles.css")
def styles():
    return send_from_directory(TEMPLATES_DIR, "styles.css")


@app.get("/<path:path>")
def static_files(path):
    return send_from_directory(BASE_DIR, path)


_try_load_default_data_dir()

if __name__ == "__main__":
    print(f"Preparation-Server auf http://localhost:{PREPARATION_PORT}")
    app.run(debug=True, port=PREPARATION_PORT, threaded=True)
