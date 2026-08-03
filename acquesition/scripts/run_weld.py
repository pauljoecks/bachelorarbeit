#!/usr/bin/env python3
"""Run a welding measurement with threshold trigger and save results to data/welding."""

from __future__ import annotations

import argparse
import collections
import json
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import h5py
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = BASE_DIR / "data" / "welding"

try:
    import nidaqmx
    from nidaqmx.constants import AcquisitionType, TerminalConfiguration

    NIDAQMX_AVAILABLE = True
except ImportError:
    NIDAQMX_AVAILABLE = False


class WeldError(Exception):
    pass


@dataclass(frozen=True)
class WeldConfig:
    device: str = "cDAQ4Mod1"
    channels: tuple[int, int] = (0, 1)  # ai0 = voltage, ai1 = current
    rate: float = 50_000.0
    threshold_v: float = 0.2  # DAQ input volts on trigger channel (~10 A)
    trigger_channel: int = 1  # index into channels tuple (current)
    pre_time_s: float = 2.0
    post_time_s: float = 2.0
    max_duration_s: float = 300.0
    voltage_scale: float = 10.0  # V_real = V_daq * scale
    current_scale: float = 50.0  # A_real = V_daq * scale
    demo_rate_hz: float = 1_000.0

    @property
    def trigger_channel_index(self) -> int:
        try:
            return self.channels.index(self.trigger_channel)
        except ValueError as exc:
            raise WeldError(
                f"Trigger-Kanal ai{self.trigger_channel} ist nicht in {self.channels} enthalten."
            ) from exc


_weld_progress_lock = threading.RLock()
_weld_progress_state = {
    "active": False,
    "experiment_id": None,
    "demo_mode": False,
    "status": "idle",
    "message": "",
    "elapsed_s": 0.0,
    "current_a": None,
    "voltage_v": None,
    "plot_buffer": [],
    "last_plot_time": 0.0,
}
_MAX_LIVE_PLOT_POINTS = 600
_LIVE_PLOT_INTERVAL_S = 1.0


def begin_weld_progress(experiment_id: str, *, demo: bool = False) -> None:
    with _weld_progress_lock:
        _weld_progress_state.update(
            {
                "active": True,
                "experiment_id": experiment_id.strip().upper(),
                "demo_mode": bool(demo),
                "status": "waiting",
                "message": "Warte auf Schweißsignal...",
                "elapsed_s": 0.0,
                "current_a": None,
                "voltage_v": None,
                "plot_buffer": [],
                "last_plot_time": 0.0,
            }
        )


def end_weld_progress() -> None:
    with _weld_progress_lock:
        _weld_progress_state.update(
            {
                "active": False,
                "experiment_id": None,
                "demo_mode": False,
                "status": "idle",
                "message": "",
                "elapsed_s": 0.0,
                "current_a": None,
                "voltage_v": None,
                "plot_buffer": [],
                "last_plot_time": 0.0,
            }
        )


def update_weld_progress(
    *,
    status: str | None = None,
    message: str | None = None,
    elapsed_s: float | None = None,
) -> None:
    with _weld_progress_lock:
        if not _weld_progress_state["active"]:
            return
        if status is not None:
            _weld_progress_state["status"] = status
        if message is not None:
            _weld_progress_state["message"] = message
        if elapsed_s is not None:
            _weld_progress_state["elapsed_s"] = float(elapsed_s)


def get_weld_progress(experiment_id: str) -> dict | None:
    normalized_id = experiment_id.strip().upper()
    with _weld_progress_lock:
        if not _weld_progress_state["active"]:
            return None
        if _weld_progress_state["experiment_id"] != normalized_id:
            return None
        return dict(_weld_progress_state)


def get_weld_plot_data(experiment_id: str, since: int = 0) -> dict | None:
    normalized_id = experiment_id.strip().upper()
    with _weld_progress_lock:
        if not _weld_progress_state["active"]:
            return None
        if _weld_progress_state["experiment_id"] != normalized_id:
            return None
        since_index = max(0, int(since))
        plot_buffer = _weld_progress_state["plot_buffer"]
        return {
            "active": True,
            "points": plot_buffer[since_index:],
            "total": len(plot_buffer),
            "current_a": _weld_progress_state.get("current_a"),
            "voltage_v": _weld_progress_state.get("voltage_v"),
        }


def _update_weld_live_chunk(
    *,
    voltage_raw: np.ndarray,
    current_raw: np.ndarray,
    config: WeldConfig,
    elapsed_s: float,
) -> None:
    current_a = float(np.mean(current_raw)) * config.current_scale
    voltage_v = float(np.mean(voltage_raw)) * config.voltage_scale

    with _weld_progress_lock:
        if not _weld_progress_state["active"]:
            return

        _weld_progress_state["current_a"] = round(current_a, 2)
        _weld_progress_state["voltage_v"] = round(voltage_v, 2)

        last_plot_time = float(_weld_progress_state.get("last_plot_time") or 0.0)
        if elapsed_s - last_plot_time < _LIVE_PLOT_INTERVAL_S:
            return

        _weld_progress_state["last_plot_time"] = elapsed_s
        _weld_progress_state["plot_buffer"].append(
            {
                "t": round(elapsed_s, 1),
                "current_a": round(current_a, 2),
                "voltage_v": round(voltage_v, 2),
            }
        )
        if len(_weld_progress_state["plot_buffer"]) > _MAX_LIVE_PLOT_POINTS:
            _weld_progress_state["plot_buffer"] = _weld_progress_state["plot_buffer"][
                -_MAX_LIVE_PLOT_POINTS:
            ]


def _build_output_basename(experiment_id: str, timestamp: datetime) -> str:
    return f"{experiment_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}"


def _save_weld_h5(
    h5_path: Path,
    time_s: np.ndarray,
    channels: list[tuple[str, np.ndarray, str, str]],
) -> None:
    with h5py.File(h5_path, "w") as h5_file:
        h5_file.create_dataset("time_s", data=time_s, compression="gzip")
        for key, values, label, units in channels:
            dataset = h5_file.create_dataset(key, data=values, compression="gzip")
            dataset.attrs["label"] = label
            dataset.attrs["units"] = units


def _build_channel_payload(
    current_a: np.ndarray,
    voltage_v: np.ndarray,
) -> list[tuple[str, np.ndarray, str, str]]:
    return [
        ("channel_0", current_a.astype(float), "Strom", "A"),
        ("channel_1", voltage_v.astype(float), "Spannung", "V"),
    ]


def _concat_channel_chunks(chunks: list[np.ndarray]) -> np.ndarray:
    if not chunks:
        return np.array([], dtype=float)
    return np.concatenate(chunks)


def _scale_ai0_to_voltage(raw: np.ndarray, config: WeldConfig) -> np.ndarray:
    return raw.astype(float) * config.voltage_scale


def _scale_ai1_to_current(raw: np.ndarray, config: WeldConfig) -> np.ndarray:
    return raw.astype(float) * config.current_scale


def _extract_scaled_channels(
    raw_channels: list[np.ndarray],
    config: WeldConfig,
) -> tuple[np.ndarray, np.ndarray]:
    channel_map = {config.channels[index]: raw_channels[index] for index in range(len(raw_channels))}
    voltage_raw = channel_map.get(config.channels[0])
    current_raw = channel_map.get(config.channels[1])
    if voltage_raw is None or current_raw is None:
        raise WeldError("Spannungs- und Stromkanal konnten nicht zugeordnet werden.")

    min_len = min(len(voltage_raw), len(current_raw))
    voltage_v = _scale_ai0_to_voltage(voltage_raw[:min_len], config)
    current_a = _scale_ai1_to_current(current_raw[:min_len], config)
    return current_a, voltage_v


def _generate_demo_chunk(
    *,
    elapsed_s: float,
    chunk_len: int,
    config: WeldConfig,
    rng: np.random.Generator,
) -> np.ndarray:
    weld_start_s = 3.0
    weld_end_s = 11.0
    dt = 1.0 / config.demo_rate_hz
    times = elapsed_s + np.arange(chunk_len, dtype=float) * dt
    raw_current = np.zeros(chunk_len, dtype=float)

    welding = (times >= weld_start_s) & (times <= weld_end_s)
    raw_current[welding] = (150.0 + rng.normal(0.0, 10.0, int(welding.sum()))) / config.current_scale
    idle = ~welding
    if idle.any():
        raw_current[idle] = rng.normal(0.0, 0.02, int(idle.sum()))

    return raw_current


def _generate_demo_voltage_chunk(
    *,
    elapsed_s: float,
    chunk_len: int,
    config: WeldConfig,
    rng: np.random.Generator,
) -> np.ndarray:
    weld_start_s = 3.0
    weld_end_s = 11.0
    dt = 1.0 / config.demo_rate_hz
    times = elapsed_s + np.arange(chunk_len, dtype=float) * dt
    raw_voltage = np.zeros(chunk_len, dtype=float)

    welding = (times >= weld_start_s) & (times <= weld_end_s)
    raw_voltage[welding] = (22.0 + rng.normal(0.0, 1.5, int(welding.sum()))) / config.voltage_scale
    idle = ~welding
    if idle.any():
        raw_voltage[idle] = rng.normal(0.0, 0.05, int(idle.sum()))

    return raw_voltage


def _capture_demo_weld(config: WeldConfig, abort_event: threading.Event | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rate = config.demo_rate_hz
    pre_samples = max(1, int(config.pre_time_s * rate))
    chunk_samples = max(1, int(rate * 0.1))
    threshold = config.threshold_v
    trigger_index = config.trigger_channel_index

    pre_buf: list[list[np.ndarray]] | None = [
        collections.deque(maxlen=pre_samples),
        collections.deque(maxlen=pre_samples),
    ]
    all_data: list[list[np.ndarray]] = [[], []]
    threshold_crossed = False
    below_threshold_since: float | None = None
    start_time = time.time()
    sample_offset = 0
    rng = np.random.default_rng()

    update_weld_progress(status="waiting", message="Demo: Warte auf Schweißsignal...", elapsed_s=0.0)

    while True:
        if abort_event and abort_event.is_set():
            raise WeldError("Schweißen abgebrochen.")

        elapsed = time.time() - start_time
        if elapsed > config.max_duration_s:
            raise WeldError(
                f"Kein Schweißsignal innerhalb von {int(config.max_duration_s)} s erkannt."
            )

        chunk_current = _generate_demo_chunk(
            elapsed_s=sample_offset / rate,
            chunk_len=chunk_samples,
            config=config,
            rng=rng,
        )
        chunk_voltage = _generate_demo_voltage_chunk(
            elapsed_s=sample_offset / rate,
            chunk_len=chunk_samples,
            config=config,
            rng=rng,
        )
        sample_offset += chunk_samples
        data = np.vstack([chunk_voltage, chunk_current])

        update_weld_progress(elapsed_s=elapsed)
        _update_weld_live_chunk(
            voltage_raw=data[0],
            current_raw=data[1],
            config=config,
            elapsed_s=elapsed,
        )
        trigger_data = data[trigger_index]
        chunk_mean = float(np.mean(trigger_data))

        if not threshold_crossed:
            assert pre_buf is not None
            pre_buf[0].extend(data[0])
            pre_buf[1].extend(data[1])

            if chunk_mean > threshold:
                threshold_crossed = True
                for ch in range(2):
                    all_data[ch].append(np.array(pre_buf[ch], dtype=float))
                pre_buf = None
                update_weld_progress(
                    status="welding",
                    message=f"Demo: Schweißsignal erkannt ({elapsed:.0f} s)",
                )
        else:
            all_data[0].append(data[0].copy())
            all_data[1].append(data[1].copy())

            if chunk_mean <= threshold:
                if below_threshold_since is None:
                    below_threshold_since = time.time()
                elif time.time() - below_threshold_since >= config.post_time_s:
                    update_weld_progress(status="saving", message="Demo: Speichere Messdaten...")
                    break
            else:
                below_threshold_since = None

            update_weld_progress(
                status="welding",
                message=f"Demo: Aufnahme läuft ({elapsed:.0f} s)",
            )

        time.sleep(0.05)

    current_a, voltage_v = _extract_scaled_channels(
        [_concat_channel_chunks(all_data[0]), _concat_channel_chunks(all_data[1])],
        config,
    )
    num_samples = min(len(current_a), len(voltage_v))
    current_a = current_a[:num_samples]
    voltage_v = voltage_v[:num_samples]
    time_s = np.arange(num_samples, dtype=float) / rate
    return time_s, current_a, voltage_v


def _capture_hardware_weld(config: WeldConfig, abort_event: threading.Event | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if not NIDAQMX_AVAILABLE:
        raise WeldError("NI-DAQmx ist nicht verfügbar. Demo-Modus verwenden oder nidaqmx installieren.")

    rate = config.rate
    channels = config.channels
    num_channels = len(channels)
    threshold = config.threshold_v
    trigger_index = config.trigger_channel_index
    pre_samples = max(1, int(config.pre_time_s * rate))
    chunk_samples = max(1, int(rate * 0.1))

    pre_buf: list[collections.deque] | None = [
        collections.deque(maxlen=pre_samples) for _ in range(num_channels)
    ]
    all_data: list[list[np.ndarray]] = [[] for _ in range(num_channels)]
    threshold_crossed = False
    below_threshold_since: float | None = None
    start_time = time.time()

    chan_string = ", ".join(f"{config.device}/ai{ch}" for ch in channels)
    update_weld_progress(status="waiting", message="Warte auf Schweißsignal...", elapsed_s=0.0)

    with nidaqmx.Task() as task:
        task.ai_channels.add_ai_voltage_chan(
            chan_string,
            min_val=-10.0,
            max_val=10.0,
            terminal_config=TerminalConfiguration.RSE,
        )
        task.timing.cfg_samp_clk_timing(
            rate=rate,
            sample_mode=AcquisitionType.CONTINUOUS,
            samps_per_chan=chunk_samples * 10,
        )
        task.start()

        try:
            while True:
                if abort_event and abort_event.is_set():
                    raise WeldError("Schweißen abgebrochen.")

                elapsed = time.time() - start_time
                if elapsed > config.max_duration_s:
                    raise WeldError(
                        f"Kein Schweißabschluss innerhalb von {int(config.max_duration_s)} s erkannt."
                    )

                update_weld_progress(elapsed_s=elapsed)

                try:
                    raw = task.read(
                        number_of_samples_per_channel=chunk_samples,
                        timeout=5.0,
                    )
                except Exception as exc:
                    raise WeldError(f"DAQ-Lesefehler: {exc}") from exc

                data = np.array(raw, dtype=float)
                if data.ndim == 1:
                    data = data.reshape(1, -1)

                _update_weld_live_chunk(
                    voltage_raw=data[0],
                    current_raw=data[1],
                    config=config,
                    elapsed_s=elapsed,
                )

                trigger_data = data[trigger_index]
                chunk_mean = float(np.mean(trigger_data))

                if not threshold_crossed:
                    assert pre_buf is not None
                    for ch in range(num_channels):
                        pre_buf[ch].extend(data[ch])

                    if chunk_mean > threshold:
                        threshold_crossed = True
                        for ch in range(num_channels):
                            all_data[ch].append(np.array(pre_buf[ch], dtype=float))
                        pre_buf = None
                        update_weld_progress(
                            status="welding",
                            message=f"Schweißsignal erkannt ({elapsed:.0f} s)",
                        )
                else:
                    for ch in range(num_channels):
                        all_data[ch].append(data[ch].copy())

                    if chunk_mean <= threshold:
                        if below_threshold_since is None:
                            below_threshold_since = time.time()
                        elif time.time() - below_threshold_since >= config.post_time_s:
                            update_weld_progress(status="saving", message="Speichere Messdaten...")
                            break
                    else:
                        below_threshold_since = None

                    update_weld_progress(
                        status="welding",
                        message=f"Aufnahme läuft ({elapsed:.0f} s)",
                    )
        finally:
            task.stop()

    if not threshold_crossed:
        raise WeldError("Schweißsignal wurde nicht erkannt.")

    raw_channels = [_concat_channel_chunks(chunks) for chunks in all_data]
    current_a, voltage_v = _extract_scaled_channels(raw_channels, config)
    num_samples = min(len(current_a), len(voltage_v))
    if num_samples <= 0:
        raise WeldError("Keine Messdaten erfasst.")

    current_a = current_a[:num_samples]
    voltage_v = voltage_v[:num_samples]
    time_s = np.arange(num_samples, dtype=float) / rate
    return time_s, current_a, voltage_v


def run_weld(
    experiment_id: str,
    output_dir: Path,
    *,
    demo: bool = False,
    config: WeldConfig | None = None,
    abort_event: threading.Event | None = None,
) -> dict:
    experiment_id = experiment_id.strip().upper()
    if len(experiment_id) != 3 or not experiment_id.isalpha():
        raise WeldError("ID muss aus 3 Buchstaben bestehen.")

    weld_config = config or WeldConfig()
    timestamp = datetime.now()
    output_dir.mkdir(parents=True, exist_ok=True)
    basename = _build_output_basename(experiment_id, timestamp)
    h5_path = output_dir / f"{basename}.h5"

    begin_weld_progress(experiment_id, demo=demo)
    try:
        if demo:
            time_s, current_a, voltage_v = _capture_demo_weld(weld_config, abort_event=abort_event)
            effective_rate = weld_config.demo_rate_hz
        else:
            time_s, current_a, voltage_v = _capture_hardware_weld(weld_config, abort_event=abort_event)
            effective_rate = weld_config.rate

        if time_s.size <= 0:
            raise WeldError("Keine Messdaten erfasst.")

        channels = _build_channel_payload(current_a, voltage_v)
        update_weld_progress(status="saving", message="Speichere H5-Datei...")
        _save_weld_h5(h5_path, time_s, channels)

        duration_s = float(time_s[-1]) if time_s.size else 0.0
        return {
            "success": True,
            "experiment_id": experiment_id,
            "h5_file": h5_path.name,
            "sample_count": int(time_s.size),
            "duration_s": duration_s,
            "sample_rate_hz": effective_rate,
            "demo_mode": bool(demo),
        }
    finally:
        end_weld_progress()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Schweißmessung mit Trigger ausführen")
    parser.add_argument("--experiment-id", required=True, help="3-stellige Versuchs-ID")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Zielverzeichnis für H5-Dateien",
    )
    parser.add_argument("--demo", action="store_true", help="Demo-Modus ohne NI-DAQ")
    parser.add_argument("--device", default="cDAQ4Mod1", help="NI-DAQ Gerätename")
    parser.add_argument("--rate", type=float, default=50_000.0, help="Abtastrate in Hz")
    parser.add_argument("--threshold-v", type=float, default=0.2, help="Trigger-Schwelle in V (DAQ)")
    parser.add_argument("--pre-time-s", type=float, default=2.0, help="Pre-Buffer in Sekunden")
    parser.add_argument("--post-time-s", type=float, default=2.0, help="Post-Buffer in Sekunden")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = WeldConfig(
        device=args.device,
        rate=args.rate,
        threshold_v=args.threshold_v,
        pre_time_s=args.pre_time_s,
        post_time_s=args.post_time_s,
    )

    try:
        result = run_weld(
            args.experiment_id,
            Path(args.output_dir),
            demo=args.demo,
            config=config,
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except WeldError as exc:
        print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    except Exception as exc:
        print(json.dumps({"success": False, "error": f"Unerwarteter Fehler: {exc}"}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
