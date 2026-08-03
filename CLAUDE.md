# Distortion — Weld & Scan Experiment Management

## Project Overview

Web-based experiment management for automated welding and 3D scanning experiments.

An operator loads the Excel database, selects an experiment by ID, views parameters, and runs:
- **Welding** — NI-9201 DAQ acquisition with threshold trigger → HDF5 in `data/welding/`
- **Scanning** — scanCONTROL laser profile acquisition → JSON in `data/scanning/`
- **Analyzing** — post-process scan + weld data → outputs in `data/analyzing/`

The Excel database (`data/Versuchsübersicht.xlsx`) tracks experiment parameters and completion status (`WELDED`, `SCANNED`, file references).

**Active branch architecture:** `app-overhall` — main entry is `scripts/server.py`, not the legacy `aquisition/weld_app.py`.

---

## Quick Start

```bat
setup\setup-server.bat    # once: create conda env + pip deps
start-server.bat          # start Flask server on http://localhost:5000
```

**Conda environment:** `distortion` (Python 3.11)

Manual start:
```bat
conda activate distortion
pip install -r setup\requirements.txt
pip install nidaqmx          # only needed for real DAQ hardware
python scripts\server.py
```

---

## Repository Structure

```
distortion/
├── CLAUDE.md                    # This file
├── start-server.bat             # Start server (env: distortion)
├── setup/
│   ├── setup-server.bat         # One-time environment setup
│   ├── environment.yml          # Conda env name: distortion
│   └── requirements.txt         # flask, pandas, openpyxl, h5py, numpy
├── scripts/
│   ├── server.py                # *** MAIN APP — Flask web server ***
│   ├── run_weld.py              # Welding acquisition (NI-DAQmx or demo)
│   ├── run_scan.py              # Scan acquisition (scanCONTROL or demo)
│   └── run_analyze.py           # Analysis pipeline (scan + weld → analyzing/)
├── templates/                   # Flask HTML UI (menu, welding, scanning, analyzing)
│   ├── path_images/             # PATH ID SVGs: PO, LI, SI, SO, ME
│   └── patterns/                # G-code/SVG pattern assets
├── data/
│   ├── Versuchsübersicht.xlsx   # *** Canonical experiment database ***
│   ├── welding/                 # HDF5 weld captures (gitignored)
│   ├── scanning/                # JSON scan captures (gitignored)
│   └── analyzing/               # Analysis outputs (gitignored)
├── robot/                       # Fanuc robot programs & wiring docs (standalone)
├── scanCONTROL/                 # Vendor SDK — do NOT modify; pyllt bindings used by run_scan.py
└── aquisition/                  # *** LEGACY *** — old weld_app.py stack, not used by server.py
```

---

## Web App Architecture (`scripts/server.py`)

### Pages
| Route | Template | Purpose |
|---|---|---|
| `/` | redirect → `/menu` | Entry |
| `/menu` | `menu.html` | Experiment overview table |
| `/welding` | `welding.html` | Weld parameters + live plot |
| `/scanning` | `scanning.html` | Scan settings + profile graph |
| `/analyzing` | `analyzing.html` | Combined scan/weld analysis |

### Key API Endpoints
- `POST /api/load-versuchsuebersicht` — load Excel database
- `GET /api/versuchsuebersicht/status` — DB load state
- `POST /api/welding/start/<id>` — start weld acquisition
- `GET /api/welding/<id>/weld-status` — acquisition state
- `GET /api/welding/<id>/live-plot` — live plot points during weld
- `POST /api/welding/reset/<id>` — undo WELDED/H5FILE
- `POST /api/scanning/start/<id>` — start scan
- `GET /api/scanning/<id>/scan-status` — scan state
- `POST /api/analyzing/generate/<id>` — run analysis

### Backend modules
`server.py` dynamically imports sibling scripts:
- `run_weld.py` — continuous NI-DAQmx acquisition, threshold detection, HDF5 save
- `run_scan.py` — scanCONTROL profile capture via `pyllt` bindings
- `run_analyze.py` — baseline filtering, probe extraction, analyzed outputs

Excel writes are serialized via `_excel_workbook_lock`. Close the `.xlsx` in Excel before the server writes to it.

---

## Hardware

### Welding DAQ (NI-9201)
- **Chassis/module:** NI cDAQ-9171 + NI-9201
- **Device name in NI MAX:** `cDAQ4Mod1` (override via `WELD_DEVICE`)
- **Channels:** ai0 = Voltage, ai1 = Current
- **Scaling:** Voltage 10:1 divider → `V_real = V_daq × 10`. Current: 10 V = 500 A → `A_real = V_daq × 50`
- **Trigger:** ~10 A on current channel → 0.2 V at DAQ input (`WELD_THRESHOLD_V=0.2`)
- **Acquisition:** Continuous mode, 50 kS/s per channel, 2 s pre/post buffer

### Scanning (scanCONTROL)
- Laser line scanner, controlled via scanCONTROL Windows SDK
- Python bindings: `scanCONTROL/.../python_bindings/pyllt/`
- Scanner IP via `SCANNER_IP` env var (default in `start-server.bat`: `192.168.0.1`)

---

## Environment Variables

Set in `start-server.bat` or manually before starting:

| Variable | Default | Meaning |
|---|---|---|
| `SCAN_USE_DEMO` | `0` in bat | `1` = fake scan data, no hardware |
| `WELD_USE_DEMO` | `0` in bat | `1` = fake weld data, no NI-DAQ |
| `SCANNER_IP` | `192.168.0.1` | scanCONTROL sensor IP |
| `WELD_DEVICE` | `cDAQ4Mod1` | NI-DAQ device name |
| `WELD_RATE` | `50000` | Sample rate per channel (Hz) |
| `WELD_THRESHOLD_V` | `0.2` | Trigger threshold (DAQ volts) |
| `WELD_PRE_TIME_S` | `2.0` | Pre-trigger buffer (seconds) |
| `WELD_POST_TIME_S` | `2.0` | Post-trigger buffer (seconds) |
| `WELD_MAX_DURATION_S` | `300.0` | Max acquisition time (seconds) |

---

## Experiment Database

**File:** `data/Versuchsübersicht.xlsx` (~800 experiment rows)

Key columns:
- **Identity:** `COUNT`, `ID` (3-letter code), `PATH ID` (PO/LI/SI/SO/ME), `SERIES`, `NUMBER`
- **Welding params:** `WFS [m/min]`, `WS [m/min]`, `WIRE`, `GASFLOW [l/min]`, etc.
- **Scan params:** `RESOLUTION`, `PROFILEFREQUENCY`, `SCANSPEED [mm/s]`, `SCANDURATION`
- **Status (auto-written):** `WELDED`, `H5FILE`, `SCANNED`, `JSONFILE`
- **Analysis:** `ANALYZESCAN`, `ANALYZEWELD`

PATH ID options: `SO`, `PO`, `SI`, `ME`, `LI`

---

## Output File Formats

### Welding HDF5 (`data/welding/{ID}_{YYYYMMDD_HHMMSS}.h5`)
- Datasets: `time_s`, `timestamps_unix`, `channel_0` (V), `channel_1` (A)
- Values stored in **real scaled units** (not raw DAQ voltage)
- Attributes: device, sample rate, experiment metadata from Excel

### Scanning JSON (`data/scanning/{ID}_{YYYYMMDD_HHMMSS}.json`)
- Profile arrays, scan settings, timestamps

### Analyzing (`data/analyzing/`)
- Processed scan JSON and derived weld H5 files

---

## Legacy / Do Not Use for New Work

| Path | Notes |
|---|---|
| `aquisition/weld_app.py` | Old standalone Flask weld app — superseded by `scripts/server.py` |
| `aquisition/ni9201_acquire.py` | CLI acquisition script, not imported by server |
| `aquisition/mark_welded.py` | Manual CLI to mark Excel rows — server does this automatically |
| `aquisition/files/usb231_*.py` | Legacy USB-231 DAQ scripts |
| `scanCONTROL/` (except pyllt) | Vendor SDK examples/docs — reference only, do not edit |

The `aquisition/` folder name is intentionally misspelled (legacy) — do not rename.

---

## Known Pitfalls

1. **Excel locked:** Server cannot write if `Versuchsübersicht.xlsx` is open in Excel → `PermissionError`
2. **Conda network:** `setup-server.bat` needs access to `repo.anaconda.com`. On restricted networks (e.g. RWTH), use existing `distortion` env + `pip install -r setup/requirements.txt` instead
3. **nidaqmx not in requirements.txt:** Install separately via pip for real welding hardware
4. **Demo vs. real mode:** `WELD_USE_DEMO=1` / `SCAN_USE_DEMO=1` for UI testing without hardware
5. **Data gitignored:** `data/welding/`, `data/scanning/`, `data/analyzing/` are local only — not in git
6. **Excel ↔ file consistency:** `WELDED`/`H5FILE` and `SCANNED`/`JSONFILE` should always be set together; orphaned entries possible if files are deleted manually

---

## Dependencies

**Conda env `distortion`:**
- From `setup/requirements.txt`: flask, pandas, openpyxl, h5py, numpy
- Hardware (pip): `nidaqmx` (welding), scanCONTROL `pyllt` bindings (bundled in repo)

**External requirements:**
- NI-DAQmx driver (Windows) for real welding
- scanCONTROL SDK/driver for real scanning
