#!/usr/bin/env python3
"""Run a scanCONTROL profile acquisition and save results to data/scanning."""

from __future__ import annotations

import argparse
import ctypes as ct
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = BASE_DIR / "data" / "scanning"
PYLLT_BINDING_DIR = (
    BASE_DIR
    / "scanCONTROL"
    / "scanCONTROL Windows SDK 4.2"
    / "C++ SDK (+python bindings)"
    / "python_bindings"
)
PYLLT_DIR = PYLLT_BINDING_DIR / "pyllt"
CPP_SDK_DIR = PYLLT_BINDING_DIR.parent

EXPOSURE_TIME_US = 100
IDLE_TIME_US = 9900
SCAN_DURATION_S = 1.0
PROFILE_FREQUENCY_TARGET = 10
SETTLE_TIME_S = 0.12
MIN_IDLE_TIME_US = 10
WARMUP_PROFILES = 3
AUTO_PRE_BUFFER_S = 1.0
AUTO_POST_BUFFER_S = 1.0
AUTO_MAX_WAIT_S = 300.0
AUTO_MAX_TOTAL_S = 600.0
AUTO_BASELINE_WINDOW = 20
AUTO_BASELINE_MIN_PROFILES = 10
AUTO_ENTRY_DEVIATION_MM = 1.5
AUTO_EXIT_DEVIATION_MM = 0.5
AUTO_ENTRY_STREAK = 3
AUTO_EXIT_STREAK = 3

_scan_progress_lock = threading.RLock()
_scan_progress_state = {
    "active": False,
    "experiment_id": None,
    "demo_mode": False,
    "latest_profile": None,
}

SCANNER_STANDOFF_HINTS_MM = {
    3000: 25,
    3001: 100,
    3002: 50,
    3003: 10,
}


class ScanSettings:
    def __init__(
        self,
        resolution: int,
        profile_frequency: float,
        exposure_us: int,
        idle_time_us: int,
        scan_duration_s: float,
        scan_duration_auto: bool = False,
    ):
        self.resolution = resolution
        self.profile_frequency = float(profile_frequency)
        self.exposure_us = exposure_us
        self.idle_time_us = idle_time_us
        self.scan_duration_s = scan_duration_s
        self.scan_duration_auto = bool(scan_duration_auto)

    @property
    def target_profile_count(self) -> int:
        return max(1, int(round(self.profile_frequency * self.scan_duration_s)))

    @classmethod
    def defaults(cls) -> "ScanSettings":
        return cls.from_profile_frequency(
            resolution=640,
            profile_frequency=PROFILE_FREQUENCY_TARGET,
            exposure_us=EXPOSURE_TIME_US,
            scan_duration_s=SCAN_DURATION_S,
        )

    @classmethod
    def from_profile_frequency(
        cls,
        resolution: int,
        profile_frequency: float,
        exposure_us: int,
        scan_duration_s: float,
        scan_duration_auto: bool = False,
    ) -> "ScanSettings":
        if profile_frequency <= 0:
            raise ScanError("PROFILEFREQUENCY muss > 0 Profile/s sein.")
        if exposure_us < 1:
            raise ScanError("EXPOSURE muss >= 1 µs sein.")
        if not scan_duration_auto and scan_duration_s <= 0:
            raise ScanError("SCANDURATION muss > 0 s sein.")
        if resolution < 1:
            raise ScanError("RESOLUTION muss >= 1 sein.")

        interval_us = 1_000_000 / profile_frequency
        idle_time_us = int(round(interval_us - exposure_us))
        if idle_time_us < MIN_IDLE_TIME_US:
            raise ScanError(
                "Berechnete Idle-Zeit zu klein "
                f"({idle_time_us} µs). EXPOSURE oder PROFILEFREQUENCY anpassen."
            )

        return cls(
            resolution=resolution,
            profile_frequency=profile_frequency,
            exposure_us=exposure_us,
            idle_time_us=idle_time_us,
            scan_duration_s=scan_duration_s if scan_duration_s > 0 else 1.0,
            scan_duration_auto=scan_duration_auto,
        )

    @classmethod
    def from_values(
        cls,
        *,
        resolution: int,
        profile_frequency: float,
        exposure_us: int,
        idle_time_us: int,
        scan_duration_s: float,
        scan_duration_auto: bool = False,
    ) -> "ScanSettings":
        return cls(
            resolution=resolution,
            profile_frequency=profile_frequency,
            exposure_us=exposure_us,
            idle_time_us=idle_time_us,
            scan_duration_s=scan_duration_s,
            scan_duration_auto=scan_duration_auto,
        )

    def profile_interval_s(self) -> float:
        return (self.exposure_us + self.idle_time_us) / 1_000_000

    def to_document(self, scan_window: dict | None = None) -> dict:
        document = {
            "resolution": self.resolution,
            "profile_frequency_hz": self.profile_frequency,
            "profile_count_target": self.target_profile_count,
            "exposure_us": self.exposure_us,
            "idle_time_us": self.idle_time_us,
            "scan_duration_s": self.scan_duration_s,
            "scan_duration_auto": self.scan_duration_auto,
        }
        if scan_window is not None:
            document["scan_window"] = scan_window
            document["scan_duration_s"] = scan_window["effective_duration_s"]
        return document


def extract_scan_duration_s(scan_settings: dict | None) -> float:
    if not scan_settings:
        raise ValueError("SCANDURATION fehlt.")

    scan_window = scan_settings.get("scan_window") or {}
    duration_s = scan_window.get("effective_duration_s", scan_settings.get("scan_duration_s"))
    if duration_s is None or str(duration_s).strip() == "":
        raise ValueError("SCANDURATION fehlt.")

    return float(duration_s)


def assign_profile_y_mm(
    profiles: list[dict],
    *,
    scan_speed_mm_s: float,
    scan_duration_s: float,
) -> None:
    profile_count = len(profiles)
    if profile_count == 0:
        return

    if scan_speed_mm_s <= 0 or scan_duration_s <= 0:
        raise ValueError("SCANSPEED und SCANDURATION müssen größer als 0 sein.")

    total_y_mm = float(scan_speed_mm_s) * float(scan_duration_s)
    if profile_count == 1:
        profiles[0]["y_mm"] = 0.0
        return

    step_mm = total_y_mm / (profile_count - 1)
    for index, profile in enumerate(profiles):
        profile["y_mm"] = round(index * step_mm, 6)


def enrich_scan_payload_with_geometry(scan_payload: dict, scan_speed_mm_s: float | None) -> None:
    if scan_speed_mm_s is None:
        return

    scan_settings = dict(scan_payload.get("scan_settings") or {})
    scan_duration_s = extract_scan_duration_s(scan_settings)
    assign_profile_y_mm(
        scan_payload["profiles"],
        scan_speed_mm_s=float(scan_speed_mm_s),
        scan_duration_s=scan_duration_s,
    )
    scan_settings["scan_speed_mm_s"] = float(scan_speed_mm_s)
    scan_payload["scan_settings"] = scan_settings


def _normalize_scan_x_mm(profiles: list[dict]) -> None:
    """Shift x_mm so the global minimum becomes 0 before persisting scan data."""
    if not profiles:
        return

    global_x_min = None
    for profile in profiles:
        for value in profile.get("x_mm") or []:
            x_value = float(value)
            global_x_min = x_value if global_x_min is None else min(global_x_min, x_value)

    if global_x_min is None or global_x_min >= 0:
        return

    for profile in profiles:
        x_mm = profile.get("x_mm")
        if not x_mm:
            continue
        profile["x_mm"] = [round(float(value) - global_x_min, 6) for value in x_mm]


def _reverse_profile_x_direction(profiles: list[dict]) -> None:
    """Mirror x with a shared maximum and reverse point order for the opposite probe edge."""
    if not profiles:
        return

    global_x_max = None
    for profile in profiles:
        for value in profile.get("x_mm") or []:
            x_value = float(value)
            global_x_max = x_value if global_x_max is None else max(global_x_max, x_value)

    if global_x_max is None:
        return

    for profile in profiles:
        x_mm = profile.get("x_mm") or []
        if len(x_mm) < 2:
            continue

        x_values = [float(value) for value in x_mm]
        z_mm = list(profile.get("z_mm") or [])
        intensities = list(profile.get("intensities") or [])

        flipped_x: list[float] = []
        flipped_z: list[float] = []
        flipped_intensities: list[int] = []
        for index in reversed(range(len(x_values))):
            flipped_x.append(round(global_x_max - x_values[index], 6))
            if index < len(z_mm):
                flipped_z.append(z_mm[index])
            if index < len(intensities):
                flipped_intensities.append(intensities[index])

        profile["x_mm"] = flipped_x
        profile["z_mm"] = flipped_z
        if intensities:
            profile["intensities"] = flipped_intensities


class ScanError(Exception):
    pass


def _python_bitness() -> int:
    return struct.calcsize("P") * 8


def _get_sdk_llt_dll_sources() -> list[Path]:
    bitness = _python_bitness()
    if bitness == 64:
        relative_paths = [
            Path("lib") / "x64" / "LLT.dll",
            Path("examples") / "bin_x64" / "LLT.dll",
        ]
    else:
        relative_paths = [
            Path("lib") / "x32" / "LLT.dll",
            Path("examples") / "bin" / "LLT.dll",
        ]

    return [CPP_SDK_DIR / relative_path for relative_path in relative_paths]


def _prepare_llt_dll() -> Path:
    target = PYLLT_DIR / "LLT.dll"
    source = None

    for candidate in _get_sdk_llt_dll_sources():
        if candidate.is_file():
            source = candidate
            break

    if source is None:
        raise ScanError(
            f"LLT.dll ({_python_bitness()}-Bit) nicht gefunden. "
            f"Erwartet unter {CPP_SDK_DIR / 'lib'}."
        )

    PYLLT_DIR.mkdir(parents=True, exist_ok=True)

    if not target.is_file() or target.stat().st_mtime < source.stat().st_mtime:
        shutil.copy2(source, target)

    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(source.parent))
        os.add_dll_directory(str(PYLLT_DIR))

    return target


def _ensure_pyllt_path() -> None:
    if not PYLLT_BINDING_DIR.is_dir():
        raise ScanError(f"pyllt-Bindings nicht gefunden: {PYLLT_BINDING_DIR}")

    binding_path = str(PYLLT_BINDING_DIR)
    if binding_path not in sys.path:
        sys.path.insert(0, binding_path)

    _prepare_llt_dll()


def _raise_on_error(return_value: int, message: str) -> None:
    if return_value < 1:
        raise ScanError(f"{message}: {return_value}")


def _interface_value_to_ip(interface_value: int) -> str:
    packed = struct.pack(">I", interface_value & 0xFFFFFFFF)
    return socket.inet_ntoa(packed)


def _ip_to_interface_value(ip_address: str) -> int:
    return struct.unpack(">I", socket.inet_aton(ip_address.strip()))[0]


def _local_ipv4_addresses() -> list[str]:
    if sys.platform != "win32":
        return []

    try:
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-NetIPAddress -AddressFamily IPv4 | "
                "Where-Object { $_.IPAddress -notlike '127.*' } | "
                "Select-Object -ExpandProperty IPAddress",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []

    addresses: list[str] = []
    for line in completed.stdout.splitlines():
        ip = line.strip()
        if ip and ip not in addresses:
            addresses.append(ip)
    return addresses


def _discover_scanners_via_gvcp(timeout_s: float = 2.0) -> list[str]:
    gvcp_port = 3956
    discovery_cmd = struct.pack(">BBHHH", 0x42, 0x11, 0x0002, 0, 0x0001)
    discover_ack_fmt = ">6HIH6s14I32s32s32s48s16s16s"
    discover_ack_size = struct.calcsize(discover_ack_fmt)
    found_ips: list[str] = []

    bind_targets = [("", gvcp_port)]
    for host_ip in _local_ipv4_addresses():
        bind_targets.append((host_ip, gvcp_port))

    for bind_ip, bind_port in bind_targets:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(timeout_s)
            sock.bind((bind_ip, bind_port))
            for broadcast_target in ("255.255.255.255", "169.254.255.255"):
                sock.sendto(discovery_cmd, (broadcast_target, gvcp_port))

            deadline = time.time() + timeout_s
            while time.time() < deadline:
                try:
                    recv_data, _recv_ip = sock.recvfrom(2048)
                except socket.timeout:
                    break
                if len(recv_data) < discover_ack_size:
                    continue
                try:
                    discover_ack = struct.unpack(discover_ack_fmt, recv_data[:discover_ack_size])
                except struct.error:
                    continue
                if discover_ack[0] != 0 or discover_ack[3] != 0x0001:
                    continue
                scanner_ip = socket.inet_ntoa(struct.pack(">I", discover_ack[14]))
                if scanner_ip not in found_ips:
                    found_ips.append(scanner_ip)
        except OSError:
            continue
        finally:
            sock.close()

    return found_ips


def _count_discovered_interfaces(return_value: int, buffer_size: int) -> int:
    if return_value == -251:
        return buffer_size
    if return_value < 0:
        return 0
    return return_value


def _discover_scanner_interfaces(llt, hllt, scanner_ip: str | None = None) -> list[int]:
    if scanner_ip:
        return [_ip_to_interface_value(scanner_ip)]

    available_interfaces = (ct.c_uint * 6)()
    discovery_errors: list[int] = []

    for method_name, discover_fn in (
        ("get_device_interfaces_fast", llt.get_device_interfaces_fast),
        ("get_device_interfaces", llt.get_device_interfaces),
    ):
        ret = discover_fn(hllt, available_interfaces, len(available_interfaces))
        count = _count_discovered_interfaces(ret, len(available_interfaces))
        if count > 0:
            return [int(available_interfaces[index]) for index in range(count)]
        if ret < 0:
            discovery_errors.append(ret)

    gvcp_ips = _discover_scanners_via_gvcp()
    if gvcp_ips:
        return [_ip_to_interface_value(ip_address) for ip_address in gvcp_ips]

    if discovery_errors:
        raise ScanError(_format_discovery_error(discovery_errors[-1]))
    raise ScanError(
        "Kein scanCONTROL gefunden. Scanner eingeschaltet und per Ethernet verbunden? "
        "Alternativ SCANNER_IP setzen oder SCAN_USE_DEMO=1 für Testläufe."
    )


def _format_discovery_error(error_code: int) -> str:
    import pyllt as llt

    if error_code == llt.ERROR_GETDEVINTERFACES_INTERNAL:
        local_ips = ", ".join(_local_ipv4_addresses()) or "keine"
        return (
            "Scanner-Suche fehlgeschlagen (SDK-Fehler -253). "
            "Das ist ein interner Fehler der Gerätesuche, kein einfaches '0 Geräte'. "
            "Prüfen: (1) scanCONTROL Configuration Tools installieren "
            "(scanCONTROL-Configuration-Tools-6-9-2.exe im Projektordner), "
            "(2) Scanner per Ethernet direkt am PC (nicht über WLAN), "
            "(3) Ethernet-Adapter eine feste IP im gleichen Subnetz geben "
            f"(z. B. 169.254.x.x; aktuelle IPv4: {local_ips}), "
            "(4) Windows-Firewall UDP-Port 3956 erlauben, "
            "(5) bekannte Scanner-IP per SCANNER_IP=... setzen. "
            "Zum Testen ohne Hardware: SCAN_USE_DEMO=1."
        )
    if error_code == llt.ERROR_GETDEVINTERFACES_CONNECTED:
        return (
            "Scanner-Suche fehlgeschlagen (-252): Gerät bereits von anderer Software verbunden. "
            "Configuration Tools oder andere SDK-Programme schließen."
        )
    if error_code == llt.ERROR_GETDEVINTERFACES_REQUEST_COUNT:
        return (
            "Scanner-Suche fehlgeschlagen (-251): Mehr als 6 scanCONTROL gefunden. "
            "Bitte SCANNER_IP auf die gewünschte Adresse setzen."
        )
    if error_code == llt.ERROR_GETDEVINTERFACES_WIN_NOT_SUPPORTED:
        return "Scanner-Suche auf diesem Windows-System nicht unterstützt (-250)."
    return f"Kein scanCONTROL gefunden: {error_code}"


def _build_output_basename(experiment_id: str, timestamp: datetime) -> str:
    return f"{experiment_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}"


def _ensure_laser_enabled(hllt, llt) -> None:
    laser_state = ct.c_uint(0)
    ret = llt.get_feature(hllt, llt.INQUIRY_FUNCTION_LASER, ct.byref(laser_state))
    if ret < 0:
        return
    if laser_state.value == llt.LASER_OFF:
        ret = llt.set_feature(hllt, llt.FEATURE_FUNCTION_LASER, llt.LASER_FULL_POWER)
        _raise_on_error(ret, "Laser konnte nicht aktiviert werden")


def _profile_has_valid_points(x, z, intensities, resolution: int) -> bool:
    for index in range(resolution):
        if intensities[index] > 0:
            return True
    for index in range(resolution):
        if abs(x[index]) > 1e-6 and abs(z[index]) > 1e-6:
            return True
    return False


def _profile_has_measurement(profile_data: dict) -> bool:
    return bool(np.any(_profile_measurement_mask(profile_data)))


def _profile_measurement_mask(profile_data: dict) -> np.ndarray:
    x_mm = np.asarray(profile_data["x_mm"], dtype=float)
    z_mm = np.asarray(profile_data["z_mm"], dtype=float)
    intensities = profile_data.get("intensities")

    if intensities is not None:
        intensities = np.asarray(intensities, dtype=float)
        mask = intensities > 0
        if np.any(mask):
            return mask

    return (np.abs(x_mm) > 1e-6) & (np.abs(z_mm) > 1e-6)


def _profile_deviation_mm(profile_data: dict, baseline_data: dict) -> float:
    mask = _profile_measurement_mask(profile_data) & _profile_measurement_mask(baseline_data)
    if not np.any(mask):
        return 0.0

    profile_z = np.asarray(profile_data["z_mm"], dtype=float)
    baseline_z = np.asarray(baseline_data["z_mm"], dtype=float)
    return float(np.mean(np.abs(profile_z[mask] - baseline_z[mask])))


def _compute_baseline_profile(profiles: list[dict]) -> dict | None:
    if not profiles:
        return None

    z_stack = np.stack([np.asarray(profile["z_mm"], dtype=float) for profile in profiles])
    intensity_stack = np.stack(
        [np.asarray(profile["intensities"], dtype=float) for profile in profiles]
    )
    return {
        "x_mm": list(profiles[0]["x_mm"]),
        "z_mm": np.median(z_stack, axis=0).astype(float).tolist(),
        "intensities": np.median(intensity_stack, axis=0).astype(int).tolist(),
    }


def _classify_probe_vs_baseline(profile_data: dict, baseline_data: dict | None) -> str:
    if baseline_data is None:
        return "uncertain"

    deviation_mm = _profile_deviation_mm(profile_data, baseline_data)
    if deviation_mm >= AUTO_ENTRY_DEVIATION_MM:
        return "present"
    if deviation_mm <= AUTO_EXIT_DEVIATION_MM:
        return "absent"
    return "uncertain"


def begin_scan_progress(experiment_id: str, *, demo: bool = False) -> None:
    normalized_id = experiment_id.strip().upper()
    with _scan_progress_lock:
        _scan_progress_state["active"] = True
        _scan_progress_state["experiment_id"] = normalized_id
        _scan_progress_state["demo_mode"] = bool(demo)
        _scan_progress_state["latest_profile"] = None


def end_scan_progress() -> None:
    with _scan_progress_lock:
        _scan_progress_state["active"] = False
        _scan_progress_state["experiment_id"] = None
        _scan_progress_state["demo_mode"] = False
        _scan_progress_state["latest_profile"] = None


def update_scan_progress_profile(profile: dict) -> None:
    with _scan_progress_lock:
        if not _scan_progress_state["active"]:
            return
        _scan_progress_state["latest_profile"] = dict(profile)


def _publish_scan_live_profile(profile_data: dict, resolution: int | None = None) -> None:
    payload = dict(profile_data)
    if resolution is not None:
        payload["resolution"] = resolution
    elif "resolution" not in payload:
        payload["resolution"] = len(payload.get("x_mm", []))
    update_scan_progress_profile(payload)


def get_scan_progress_profile(experiment_id: str) -> dict | None:
    normalized_id = experiment_id.strip().upper()
    with _scan_progress_lock:
        if not _scan_progress_state["active"]:
            return None
        if _scan_progress_state["experiment_id"] != normalized_id:
            return None
        latest = _scan_progress_state["latest_profile"]
        return dict(latest) if latest is not None else None


def get_scan_progress_demo_mode(experiment_id: str) -> bool:
    normalized_id = experiment_id.strip().upper()
    with _scan_progress_lock:
        if not _scan_progress_state["active"]:
            return False
        if _scan_progress_state["experiment_id"] != normalized_id:
            return False
        return bool(_scan_progress_state["demo_mode"])


def is_scan_in_progress(experiment_id: str) -> bool:
    normalized_id = experiment_id.strip().upper()
    with _scan_progress_lock:
        return (
            _scan_progress_state["active"]
            and _scan_progress_state["experiment_id"] == normalized_id
        )


class AutoCaptureTracker:
    def __init__(self, scan_start_time: float):
        self.scan_start_time = scan_start_time
        self.state = "waiting"
        self.stream: list[tuple[float, dict]] = []
        self.baseline_window: list[dict] = []
        self.frozen_baseline: dict | None = None
        self.entry_time: float | None = None
        self.exit_time: float | None = None
        self.last_present_time: float | None = None
        self.present_streak = 0
        self.absent_streak = 0
        self.post_deadline: float | None = None
        self.done = False

    def _current_baseline(self) -> dict | None:
        if self.frozen_baseline is not None:
            return self.frozen_baseline
        if len(self.baseline_window) < AUTO_BASELINE_MIN_PROFILES:
            return None
        return _compute_baseline_profile(self.baseline_window)

    def add_sample(self, timestamp: float, profile_data: dict) -> None:
        if not _profile_has_measurement(profile_data):
            return

        _publish_scan_live_profile(profile_data)

        classification = _classify_probe_vs_baseline(profile_data, self._current_baseline())

        if self.state == "waiting":
            self.stream.append((timestamp, profile_data))
            self.baseline_window.append(profile_data)
            if len(self.baseline_window) > AUTO_BASELINE_WINDOW:
                self.baseline_window.pop(0)

            if classification == "present" and self._current_baseline() is not None:
                self.present_streak += 1
            else:
                self.present_streak = 0

            if self.present_streak >= AUTO_ENTRY_STREAK:
                self.frozen_baseline = self._current_baseline()
                self.entry_time = timestamp
                self.last_present_time = timestamp
                self.state = "in_range"
                self.present_streak = 0
                self.absent_streak = 0
            elif timestamp - self.scan_start_time > AUTO_MAX_WAIT_S:
                raise ScanError(
                    "AUTO-Scan: Probe im Scanbereich nicht erkannt. "
                    f"Innerhalb von {int(AUTO_MAX_WAIT_S)} s keine Abweichung vom Tischprofil."
                )
            return

        if self.state == "in_range":
            self.stream.append((timestamp, profile_data))
            if classification == "present":
                self.last_present_time = timestamp
                self.absent_streak = 0
                return

            if classification == "absent":
                self.absent_streak += 1
            else:
                self.absent_streak = 0

            if self.absent_streak >= AUTO_EXIT_STREAK:
                if self.last_present_time is None:
                    raise ScanError("AUTO-Scan: Probe verließ den Bereich ohne erkennbare Profile.")
                self.exit_time = self.last_present_time
                self.state = "post_buffer"
                self.post_deadline = timestamp + AUTO_POST_BUFFER_S
            return

        self.stream.append((timestamp, profile_data))
        if self.post_deadline is not None and timestamp >= self.post_deadline:
            self.done = True


def _profile_dict_from_arrays(x, z, intensities) -> dict:
    return {
        "x_mm": [float(value) for value in x],
        "z_mm": [float(value) for value in z],
        "intensities": [int(value) for value in intensities],
    }


def _sleep_until_next_profile(last_read_at: float | None, interval_s: float) -> None:
    if last_read_at is None:
        return
    remaining = interval_s - (time.time() - last_read_at)
    if remaining > 0:
        time.sleep(remaining)


def _finalize_auto_capture(
    stream: list[tuple[float, dict]],
    *,
    entry_time: float,
    exit_time: float,
    scan_start_time: float,
) -> tuple[list[dict], dict]:
    window_start = entry_time - AUTO_PRE_BUFFER_S
    window_end = exit_time + AUTO_POST_BUFFER_S
    profiles: list[dict] = []

    for timestamp, profile_data in stream:
        if timestamp < window_start or timestamp > window_end:
            continue
        profiles.append(
            {
                **profile_data,
                "profile_index": len(profiles),
            }
        )

    if not profiles:
        raise ScanError(
            "AUTO-Scan: Keine Profile im Zeitfenster erfasst "
            f"({AUTO_PRE_BUFFER_S} s vor Eintritt bis {AUTO_POST_BUFFER_S} s nach Austritt)."
        )

    scan_window = {
        "entry_time_s": round(entry_time - scan_start_time, 6),
        "exit_time_s": round(exit_time - scan_start_time, 6),
        "window_start_s": round(window_start - scan_start_time, 6),
        "window_end_s": round(window_end - scan_start_time, 6),
        "pre_buffer_s": AUTO_PRE_BUFFER_S,
        "post_buffer_s": AUTO_POST_BUFFER_S,
        "effective_duration_s": round(window_end - window_start, 6),
    }
    return profiles, scan_window


def _validate_auto_capture_tracker(tracker: AutoCaptureTracker) -> None:
    if tracker.state == "waiting":
        raise ScanError("AUTO-Scan: Probe im Scanbereich nicht erkannt.")
    if tracker.state == "in_range":
        raise ScanError(
            "AUTO-Scan: Probe hat den Scanbereich nicht verlassen. "
            "Tisch weiterfahren oder AUTO deaktivieren und SCANDURATION setzen."
        )
    if tracker.entry_time is None or tracker.exit_time is None:
        raise ScanError("AUTO-Scan: Ein- oder Austritt der Probe konnte nicht bestimmt werden.")


def _scanner_standoff_hint(scanner_type_value: int) -> str:
    standoff_mm = SCANNER_STANDOFF_HINTS_MM.get(scanner_type_value)
    if standoff_mm is None:
        return "laut Datenblatt"
    return f"ca. {standoff_mm} mm"


def _raise_if_profiles_invalid(
    profiles: list[dict],
    scanner_type_value: int,
    scan_settings: ScanSettings,
) -> None:
    if not profiles:
        raise ScanError("Während des Scans wurden keine gültigen Profile empfangen.")

    max_intensity = max(
        max(profile["intensities"])
        for profile in profiles
    )
    if max_intensity > 0:
        return

    valid_points = sum(
        1
        for profile in profiles
        for x_value, z_value in zip(profile["x_mm"], profile["z_mm"])
        if abs(x_value) > 1e-6 and abs(z_value) > 1e-6
    )
    if valid_points > 0:
        return

    standoff_hint = _scanner_standoff_hint(scanner_type_value)
    raise ScanError(
        "Keine gültigen Messpunkte empfangen (alle Profile leer). "
        f"Prüfen: (1) Messobjekt im Laserfeld, (2) Scanner-Abstand {standoff_hint}, "
        f"(3) Belichtung EXPOSURE erhöhen (aktuell {scan_settings.exposure_us} µs), "
        "(4) Oberfläche reflektiert Laserlicht."
    )


def _select_resolution(available_resolutions, requested_resolution: int) -> int:
    available = sorted(
        {
            int(value)
            for value in available_resolutions
            if int(value) > 0
        }
    )
    if not available:
        raise ScanError("Keine Scanner-Auflösungen verfügbar.")

    if requested_resolution in available:
        return requested_resolution

    raise ScanError(
        f"RESOLUTION {requested_resolution} ist am Scanner nicht verfügbar. "
        f"Verfügbar: {', '.join(str(value) for value in available)}"
    )


def _capture_profiles(scanner_ip: str | None = None, settings: ScanSettings | None = None) -> dict:
    scan_settings = settings or ScanSettings.defaults()
    import pyllt as llt

    scanner_type = ct.c_int(0)
    available_resolutions = (ct.c_uint * 4)()
    null_ptr_short = ct.POINTER(ct.c_ushort)()
    null_ptr_int = ct.POINTER(ct.c_uint)()

    hllt = llt.create_llt_device(llt.TInterfaceType.INTF_TYPE_ETHERNET)
    if not hllt:
        raise ScanError("scanCONTROL-Gerät konnte nicht erstellt werden.")

    try:
        interface_values = _discover_scanner_interfaces(llt, hllt, scanner_ip=scanner_ip)
        selected_interface = interface_values[0]

        ret = llt.set_device_interface(hllt, selected_interface, 0)
        if ret < 1:
            selected_ip = _interface_value_to_ip(selected_interface)
            raise ScanError(
                f"Verbindung zu {selected_ip} fehlgeschlagen (SetDeviceInterface: {ret}). "
                "IP/Subnetz prüfen oder scanCONTROL Configuration Tools verwenden."
            )

        ret = llt.connect(hllt)
        _raise_on_error(ret, "Verbindung zum scanCONTROL fehlgeschlagen")

        ret = llt.get_resolutions(hllt, available_resolutions, len(available_resolutions))
        _raise_on_error(ret, "Auflösungen konnten nicht gelesen werden")

        resolution = _select_resolution(available_resolutions, scan_settings.resolution)
        ret = llt.set_resolution(hllt, resolution)
        _raise_on_error(ret, "Auflösung konnte nicht gesetzt werden")

        profile_buffer = (ct.c_ubyte * (resolution * 64))()
        x = (ct.c_double * resolution)()
        z = (ct.c_double * resolution)()
        intensities = (ct.c_ushort * resolution)()
        lost_profiles = ct.c_int()

        ret = llt.get_llt_type(hllt, ct.byref(scanner_type))
        _raise_on_error(ret, "Scanner-Typ konnte nicht gelesen werden")

        ret = llt.set_profile_config(hllt, llt.TProfileConfig.PROFILE)
        _raise_on_error(ret, "Profil-Konfiguration konnte nicht gesetzt werden")

        ret = llt.set_feature(hllt, llt.FEATURE_FUNCTION_TRIGGER, llt.TRIG_INTERNAL)
        _raise_on_error(ret, "Trigger konnte nicht gesetzt werden")

        ret = llt.set_feature(hllt, llt.FEATURE_FUNCTION_EXPOSURE_TIME, scan_settings.exposure_us)
        _raise_on_error(ret, "Belichtungszeit konnte nicht gesetzt werden")

        ret = llt.set_feature(hllt, llt.FEATURE_FUNCTION_IDLE_TIME, scan_settings.idle_time_us)
        _raise_on_error(ret, "Idle-Zeit konnte nicht gesetzt werden")

        _ensure_laser_enabled(hllt, llt)

        time.sleep(SETTLE_TIME_S)

        ret = llt.transfer_profiles(hllt, llt.TTransferProfileType.NORMAL_TRANSFER, 1)
        _raise_on_error(ret, "Profilübertragung konnte nicht gestartet werden")

        profiles: list[dict] = []
        warmup_remaining = WARMUP_PROFILES
        collection_deadline = None
        scanner_type_enum = llt.TScannerType(int(scanner_type.value))
        target_profile_count = scan_settings.target_profile_count

        try:
            while collection_deadline is None or time.time() < collection_deadline:
                ret = llt.get_actual_profile(
                    hllt,
                    profile_buffer,
                    len(profile_buffer),
                    llt.TProfileConfig.PROFILE,
                    ct.byref(lost_profiles),
                )
                if ret != len(profile_buffer):
                    if ret == llt.ERROR_PROFTRANS_NO_NEW_PROFILE:
                        time.sleep(
                            (scan_settings.idle_time_us + scan_settings.exposure_us) / 1_000_000
                        )
                        continue
                    raise ScanError(f"Profil konnte nicht gelesen werden: {ret}")

                convert_ret = llt.convert_profile_2_values(
                    hllt,
                    profile_buffer,
                    resolution,
                    llt.TProfileConfig.PROFILE,
                    scanner_type_enum,
                    0,
                    1,
                    null_ptr_short,
                    intensities,
                    null_ptr_short,
                    x,
                    z,
                    null_ptr_int,
                    null_ptr_int,
                )
                if (
                    convert_ret & llt.CONVERT_X == 0
                    or convert_ret & llt.CONVERT_Z == 0
                    or convert_ret & llt.CONVERT_MAXIMUM == 0
                ):
                    raise ScanError(f"Profil konnte nicht konvertiert werden: {convert_ret}")

                profile_data = _profile_dict_from_arrays(x, z, intensities)
                _publish_scan_live_profile(profile_data, resolution)

                if warmup_remaining > 0:
                    warmup_remaining -= 1
                    if warmup_remaining == 0:
                        collection_deadline = time.time() + scan_settings.scan_duration_s
                    continue

                if not _profile_has_valid_points(x, z, intensities, resolution):
                    continue

                profiles.append(
                    {
                        "profile_index": len(profiles),
                        "x_mm": profile_data["x_mm"],
                        "z_mm": profile_data["z_mm"],
                        "intensities": profile_data["intensities"],
                    }
                )
        finally:
            llt.transfer_profiles(hllt, llt.TTransferProfileType.NORMAL_TRANSFER, 0)

        if len(profiles) < target_profile_count:
            raise ScanError(
                f"Nur {len(profiles)} von {target_profile_count} Profilen in "
                f"{scan_settings.scan_duration_s} s erfasst. "
                "Prüfen: EXPOSURE, PROFILEFREQUENCY, SCANDURATION und Messobjekt."
            )

        _raise_if_profiles_invalid(profiles, int(scanner_type.value), scan_settings)

        return {
            "scanner_type": int(scanner_type.value),
            "resolution": resolution,
            "profile_count": len(profiles),
            "profiles": profiles,
            "scan_settings": scan_settings.to_document(),
        }
    finally:
        llt.disconnect(hllt)
        llt.del_device(hllt)


def _capture_profiles_auto(scanner_ip: str | None = None, settings: ScanSettings | None = None) -> dict:
    scan_settings = settings or ScanSettings.defaults()
    import pyllt as llt

    scanner_type = ct.c_int(0)
    available_resolutions = (ct.c_uint * 4)()
    null_ptr_short = ct.POINTER(ct.c_ushort)()
    null_ptr_int = ct.POINTER(ct.c_uint)()

    hllt = llt.create_llt_device(llt.TInterfaceType.INTF_TYPE_ETHERNET)
    if not hllt:
        raise ScanError("scanCONTROL-Gerät konnte nicht erstellt werden.")

    try:
        interface_values = _discover_scanner_interfaces(llt, hllt, scanner_ip=scanner_ip)
        selected_interface = interface_values[0]

        ret = llt.set_device_interface(hllt, selected_interface, 0)
        if ret < 1:
            selected_ip = _interface_value_to_ip(selected_interface)
            raise ScanError(
                f"Verbindung zu {selected_ip} fehlgeschlagen (SetDeviceInterface: {ret}). "
                "IP/Subnetz prüfen oder scanCONTROL Configuration Tools verwenden."
            )

        ret = llt.connect(hllt)
        _raise_on_error(ret, "Verbindung zum scanCONTROL fehlgeschlagen")

        ret = llt.get_resolutions(hllt, available_resolutions, len(available_resolutions))
        _raise_on_error(ret, "Auflösungen konnten nicht gelesen werden")

        resolution = _select_resolution(available_resolutions, scan_settings.resolution)
        ret = llt.set_resolution(hllt, resolution)
        _raise_on_error(ret, "Auflösung konnte nicht gesetzt werden")

        profile_buffer = (ct.c_ubyte * (resolution * 64))()
        x = (ct.c_double * resolution)()
        z = (ct.c_double * resolution)()
        intensities = (ct.c_ushort * resolution)()
        lost_profiles = ct.c_int()

        ret = llt.get_llt_type(hllt, ct.byref(scanner_type))
        _raise_on_error(ret, "Scanner-Typ konnte nicht gelesen werden")

        ret = llt.set_profile_config(hllt, llt.TProfileConfig.PROFILE)
        _raise_on_error(ret, "Profil-Konfiguration konnte nicht gesetzt werden")

        ret = llt.set_feature(hllt, llt.FEATURE_FUNCTION_TRIGGER, llt.TRIG_INTERNAL)
        _raise_on_error(ret, "Trigger konnte nicht gesetzt werden")

        ret = llt.set_feature(hllt, llt.FEATURE_FUNCTION_EXPOSURE_TIME, scan_settings.exposure_us)
        _raise_on_error(ret, "Belichtungszeit konnte nicht gesetzt werden")

        ret = llt.set_feature(hllt, llt.FEATURE_FUNCTION_IDLE_TIME, scan_settings.idle_time_us)
        _raise_on_error(ret, "Idle-Zeit konnte nicht gesetzt werden")

        _ensure_laser_enabled(hllt, llt)
        time.sleep(SETTLE_TIME_S)

        ret = llt.transfer_profiles(hllt, llt.TTransferProfileType.NORMAL_TRANSFER, 1)
        _raise_on_error(ret, "Profilübertragung konnte nicht gestartet werden")

        scanner_type_enum = llt.TScannerType(int(scanner_type.value))
        profile_interval_s = scan_settings.profile_interval_s()
        scan_start_time = time.time()
        tracker = AutoCaptureTracker(scan_start_time)
        last_read_at = None

        try:
            for _ in range(WARMUP_PROFILES):
                ret = llt.get_actual_profile(
                    hllt,
                    profile_buffer,
                    len(profile_buffer),
                    llt.TProfileConfig.PROFILE,
                    ct.byref(lost_profiles),
                )
                if ret == llt.ERROR_PROFTRANS_NO_NEW_PROFILE:
                    time.sleep(profile_interval_s)
                last_read_at = time.time()

            while not tracker.done:
                if time.time() - scan_start_time > AUTO_MAX_TOTAL_S:
                    raise ScanError(
                        f"AUTO-Scan: Gesamtzeit von {int(AUTO_MAX_TOTAL_S)} s überschritten."
                    )

                ret = llt.get_actual_profile(
                    hllt,
                    profile_buffer,
                    len(profile_buffer),
                    llt.TProfileConfig.PROFILE,
                    ct.byref(lost_profiles),
                )
                if ret != len(profile_buffer):
                    if ret == llt.ERROR_PROFTRANS_NO_NEW_PROFILE:
                        _sleep_until_next_profile(last_read_at, profile_interval_s)
                        continue
                    raise ScanError(f"Profil konnte nicht gelesen werden: {ret}")

                convert_ret = llt.convert_profile_2_values(
                    hllt,
                    profile_buffer,
                    resolution,
                    llt.TProfileConfig.PROFILE,
                    scanner_type_enum,
                    0,
                    1,
                    null_ptr_short,
                    intensities,
                    null_ptr_short,
                    x,
                    z,
                    null_ptr_int,
                    null_ptr_int,
                )
                if (
                    convert_ret & llt.CONVERT_X == 0
                    or convert_ret & llt.CONVERT_Z == 0
                    or convert_ret & llt.CONVERT_MAXIMUM == 0
                ):
                    raise ScanError(f"Profil konnte nicht konvertiert werden: {convert_ret}")

                timestamp = time.time()
                last_read_at = timestamp
                profile_data = _profile_dict_from_arrays(x, z, intensities)
                tracker.add_sample(timestamp, profile_data)
        finally:
            llt.transfer_profiles(hllt, llt.TTransferProfileType.NORMAL_TRANSFER, 0)

        _validate_auto_capture_tracker(tracker)

        profiles, scan_window = _finalize_auto_capture(
            tracker.stream,
            entry_time=tracker.entry_time,
            exit_time=tracker.exit_time,
            scan_start_time=scan_start_time,
        )
        _raise_if_profiles_invalid(profiles, int(scanner_type.value), scan_settings)

        return {
            "scanner_type": int(scanner_type.value),
            "resolution": resolution,
            "profile_count": len(profiles),
            "profiles": profiles,
            "scan_settings": scan_settings.to_document(scan_window),
        }
    finally:
        llt.disconnect(hllt)
        llt.del_device(hllt)


def _capture_demo_profiles(experiment_id: str, settings: ScanSettings | None = None) -> dict:
    scan_settings = settings or ScanSettings.defaults()
    if scan_settings.scan_duration_auto:
        return _capture_demo_profiles_auto(experiment_id, scan_settings)

    resolution = scan_settings.resolution
    target_profile_count = scan_settings.target_profile_count
    x = np.linspace(-40.0, 40.0, resolution)
    rng = np.random.default_rng()

    profiles: list[dict] = []
    for profile_index in range(target_profile_count):
        phase = profile_index * 0.08
        z = 120.0 + 8.0 * np.sin(x / 6.0 + phase) + 0.05 * rng.random(resolution)
        intensities = np.clip(400 + 300 * np.cos(x / 10.0 + phase * 0.5), 0, 1200).astype(int)
        profile_data = {
            "profile_index": profile_index,
            "x_mm": x.astype(float).tolist(),
            "z_mm": z.astype(float).tolist(),
            "intensities": intensities.astype(int).tolist(),
        }
        _publish_scan_live_profile(profile_data, resolution)
        profiles.append(profile_data)

    return {
        "scanner_type": 0,
        "resolution": resolution,
        "profile_count": target_profile_count,
        "profiles": profiles,
        "demo_mode": True,
        "experiment_id": experiment_id,
        "scan_settings": scan_settings.to_document(),
    }


def _capture_demo_profiles_auto(experiment_id: str, scan_settings: ScanSettings) -> dict:
    resolution = scan_settings.resolution
    profile_interval_s = scan_settings.profile_interval_s()
    x = np.linspace(-40.0, 40.0, resolution)
    rng = np.random.default_rng()

    scan_start_time = time.time()
    tracker = AutoCaptureTracker(scan_start_time)
    phase = 0.0
    table_z = 120.0 + 0.05 * rng.random(resolution)
    table_intensities = np.clip(450 + 20 * rng.random(resolution), 200, 1200).astype(int)

    while not tracker.done:
        if time.time() - scan_start_time > AUTO_MAX_TOTAL_S:
            raise ScanError(f"AUTO-Scan: Gesamtzeit von {int(AUTO_MAX_TOTAL_S)} s überschritten.")

        elapsed = time.time() - scan_start_time
        timestamp = time.time()
        probe_visible = 1.5 <= elapsed <= 4.5

        if probe_visible:
            phase += 0.08
            z = table_z + 8.0 * np.sin(x / 6.0 + phase)
            intensities = np.clip(table_intensities + 300 * np.cos(x / 10.0 + phase * 0.5), 200, 1200).astype(int)
        else:
            z = table_z.copy()
            intensities = table_intensities.copy()

        profile_data = {
            "profile_index": 0,
            "x_mm": x.astype(float).tolist(),
            "z_mm": z.astype(float).tolist(),
            "intensities": intensities.astype(int).tolist(),
        }
        tracker.add_sample(timestamp, profile_data)
        time.sleep(profile_interval_s)

    _validate_auto_capture_tracker(tracker)

    profiles, scan_window = _finalize_auto_capture(
        tracker.stream,
        entry_time=tracker.entry_time,
        exit_time=tracker.exit_time,
        scan_start_time=scan_start_time,
    )

    return {
        "scanner_type": 0,
        "resolution": resolution,
        "profile_count": len(profiles),
        "profiles": profiles,
        "demo_mode": True,
        "experiment_id": experiment_id,
        "scan_settings": scan_settings.to_document(scan_window),
    }


def _align_scan_profiles_to_probe_origin(profiles: list[dict]) -> dict | None:
    from run_analyze import MIRROR_ORIGIN_EDGE_EXCLUSION_MM, align_profiles_to_probe_origin

    return align_profiles_to_probe_origin(
        profiles,
        exclude_probe_x_below_mm=MIRROR_ORIGIN_EDGE_EXCLUSION_MM,
    )


def _save_scan_results(
    experiment_id: str,
    scan_payload: dict,
    output_dir: Path,
    timestamp: datetime,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    basename = _build_output_basename(experiment_id, timestamp)
    json_path = output_dir / f"{basename}.json"

    profiles = scan_payload["profiles"]
    _reverse_profile_x_direction(profiles)

    probe_origin = _align_scan_profiles_to_probe_origin(profiles)
    if probe_origin is None:
        _normalize_scan_x_mm(profiles)
    else:
        scan_payload["probe_origin"] = probe_origin

    document = {
        "experiment_id": experiment_id,
        "timestamp": timestamp.isoformat(timespec="seconds"),
        "scanner_type": scan_payload["scanner_type"],
        "resolution": scan_payload["resolution"],
        "profile_count": scan_payload["profile_count"],
        "profiles": scan_payload["profiles"],
    }
    if scan_payload.get("probe_origin"):
        document["probe_origin"] = scan_payload["probe_origin"]
    if scan_payload.get("scan_settings"):
        document["scan_settings"] = scan_payload["scan_settings"]
    if scan_payload.get("demo_mode"):
        document["demo_mode"] = True

    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2)

    result = {
        "success": True,
        "experiment_id": experiment_id,
        "json_file": json_path.name,
        "profile_count": scan_payload["profile_count"],
        "resolution": scan_payload["resolution"],
        "demo_mode": bool(scan_payload.get("demo_mode")),
    }
    if scan_payload.get("scan_settings"):
        result["scan_settings"] = scan_payload["scan_settings"]
    return result


def run_scan(
    experiment_id: str,
    output_dir: Path,
    demo: bool = False,
    scanner_ip: str | None = None,
    settings: ScanSettings | None = None,
    scan_speed_mm_s: float | None = None,
) -> dict:
    experiment_id = experiment_id.strip().upper()
    timestamp = datetime.now()

    begin_scan_progress(experiment_id, demo=demo)
    try:
        if demo:
            scan_payload = _capture_demo_profiles(experiment_id, settings=settings)
        else:
            _ensure_pyllt_path()
            if settings and settings.scan_duration_auto:
                scan_payload = _capture_profiles_auto(scanner_ip=scanner_ip, settings=settings)
            else:
                scan_payload = _capture_profiles(scanner_ip=scanner_ip, settings=settings)

        enrich_scan_payload_with_geometry(scan_payload, scan_speed_mm_s)
        return _save_scan_results(experiment_id, scan_payload, output_dir, timestamp)
    finally:
        end_scan_progress()


_demo_live_phase = 0.0


def capture_demo_live_profile(settings: ScanSettings | None = None) -> dict:
    global _demo_live_phase

    scan_settings = settings or ScanSettings.defaults()
    resolution = scan_settings.resolution
    _demo_live_phase += 0.12
    x = np.linspace(-40.0, 40.0, resolution)
    z = 120.0 + 8.0 * np.sin(x / 6.0 + _demo_live_phase)
    intensities = np.clip(400 + 300 * np.cos(x / 10.0 + _demo_live_phase * 0.5), 0, 1200).astype(int)
    return {
        "x_mm": x.astype(float).tolist(),
        "z_mm": z.astype(float).tolist(),
        "intensities": intensities.astype(int).tolist(),
        "resolution": resolution,
    }


class LiveProfilePreview:
    def __init__(self):
        self.hllt = None
        self.llt = None
        self._transfer_active = False
        self._settings_signature = None
        self._scanner_ip = None
        self._resolution = 0
        self._scanner_type_enum = None
        self._profile_buffer = None
        self._x = None
        self._z = None
        self._intensities = None
        self._lost_profiles = None
        self._null_ptr_short = None
        self._null_ptr_int = None

    def close(self) -> None:
        if self.llt and self.hllt:
            try:
                if self._transfer_active:
                    self.llt.transfer_profiles(
                        self.hllt,
                        self.llt.TTransferProfileType.NORMAL_TRANSFER,
                        0,
                    )
            except Exception:
                pass
            self._transfer_active = False

            try:
                self.llt.disconnect(self.hllt)
            except Exception:
                pass

            try:
                self.llt.del_device(self.hllt)
            except Exception:
                pass

        self.hllt = None
        self.llt = None
        self._settings_signature = None
        self._scanner_ip = None

    def capture(self, scanner_ip: str | None, settings: ScanSettings) -> dict:
        with _live_preview_lock:
            signature = (
                scanner_ip or "",
                settings.resolution,
                settings.exposure_us,
                settings.idle_time_us,
                settings.profile_frequency,
            )
            try:
                if not self.hllt:
                    self._connect(scanner_ip, settings, signature)
                elif self._settings_signature != signature:
                    self._apply_settings(scanner_ip, settings, signature)

                return self._read_profile(settings)
            except ScanError as exc:
                if self._is_connection_error(exc):
                    self.close()
                raise

    @staticmethod
    def _is_connection_error(exc: ScanError) -> bool:
        message = str(exc)
        return (
            "Verbindung zum scanCONTROL fehlgeschlagen" in message
            or "SetDeviceInterface" in message
            or "-303" in message
            or "-302" in message
        )

    def _apply_settings(
        self,
        scanner_ip: str | None,
        settings: ScanSettings,
        signature: tuple,
    ) -> None:
        if (scanner_ip or "") != (self._scanner_ip or ""):
            self.close()
            self._connect(scanner_ip, settings, signature)
            return

        if self._transfer_active:
            self.llt.transfer_profiles(
                self.hllt,
                self.llt.TTransferProfileType.NORMAL_TRANSFER,
                0,
            )
            self._transfer_active = False

        if settings.resolution != self._settings_signature[1]:
            available_resolutions = (ct.c_uint * 4)()
            ret = self.llt.get_resolutions(self.hllt, available_resolutions, len(available_resolutions))
            _raise_on_error(ret, "Auflösungen konnten nicht gelesen werden")

            resolution = _select_resolution(available_resolutions, settings.resolution)
            ret = self.llt.set_resolution(self.hllt, resolution)
            _raise_on_error(ret, "Auflösung konnte nicht gesetzt werden")

            self._resolution = resolution
            self._profile_buffer = (ct.c_ubyte * (resolution * 64))()
            self._x = (ct.c_double * resolution)()
            self._z = (ct.c_double * resolution)()
            self._intensities = (ct.c_ushort * resolution)()

        ret = self.llt.set_feature(
            self.hllt,
            self.llt.FEATURE_FUNCTION_EXPOSURE_TIME,
            settings.exposure_us,
        )
        _raise_on_error(ret, "Belichtungszeit konnte nicht gesetzt werden")

        ret = self.llt.set_feature(
            self.hllt,
            self.llt.FEATURE_FUNCTION_IDLE_TIME,
            settings.idle_time_us,
        )
        _raise_on_error(ret, "Idle-Zeit konnte nicht gesetzt werden")

        time.sleep(SETTLE_TIME_S)

        ret = self.llt.transfer_profiles(
            self.hllt,
            self.llt.TTransferProfileType.NORMAL_TRANSFER,
            1,
        )
        _raise_on_error(ret, "Profilübertragung konnte nicht gestartet werden")

        self._transfer_active = True
        self._settings_signature = signature
        self._scanner_ip = scanner_ip

    def _connect(self, scanner_ip: str | None, settings: ScanSettings, signature: tuple) -> None:
        _ensure_pyllt_path()
        import pyllt as llt

        if self.hllt:
            self.close()

        self.llt = llt
        scanner_type = ct.c_int(0)
        available_resolutions = (ct.c_uint * 4)()
        self._null_ptr_short = ct.POINTER(ct.c_ushort)()
        self._null_ptr_int = ct.POINTER(ct.c_uint)()

        hllt = llt.create_llt_device(llt.TInterfaceType.INTF_TYPE_ETHERNET)
        if not hllt:
            raise ScanError("scanCONTROL-Gerät konnte nicht erstellt werden.")

        try:
            interface_values = _discover_scanner_interfaces(llt, hllt, scanner_ip=scanner_ip)
            selected_interface = interface_values[0]

            ret = llt.set_device_interface(hllt, selected_interface, 0)
            if ret < 1:
                selected_ip = _interface_value_to_ip(selected_interface)
                raise ScanError(
                    f"Verbindung zu {selected_ip} fehlgeschlagen (SetDeviceInterface: {ret})."
                )

            ret = llt.connect(hllt)
            if ret < 1 and ret == llt.ERROR_CONNECT_LLT_NUMBER_ALREADY_USED:
                llt.del_device(hllt)
                hllt = llt.create_llt_device(llt.TInterfaceType.INTF_TYPE_ETHERNET)
                if not hllt:
                    raise ScanError("scanCONTROL-Gerät konnte nicht erstellt werden.")
                ret = llt.set_device_interface(hllt, selected_interface, 0)
                if ret < 1:
                    selected_ip = _interface_value_to_ip(selected_interface)
                    raise ScanError(
                        f"Verbindung zu {selected_ip} fehlgeschlagen (SetDeviceInterface: {ret})."
                    )
                ret = llt.connect(hllt)

            _raise_on_error(ret, "Verbindung zum scanCONTROL fehlgeschlagen")

            ret = llt.get_resolutions(hllt, available_resolutions, len(available_resolutions))
            _raise_on_error(ret, "Auflösungen konnten nicht gelesen werden")

            resolution = _select_resolution(available_resolutions, settings.resolution)
            ret = llt.set_resolution(hllt, resolution)
            _raise_on_error(ret, "Auflösung konnte nicht gesetzt werden")

            ret = llt.get_llt_type(hllt, ct.byref(scanner_type))
            _raise_on_error(ret, "Scanner-Typ konnte nicht gelesen werden")

            ret = llt.set_profile_config(hllt, llt.TProfileConfig.PROFILE)
            _raise_on_error(ret, "Profil-Konfiguration konnte nicht gesetzt werden")

            ret = llt.set_feature(hllt, llt.FEATURE_FUNCTION_TRIGGER, llt.TRIG_INTERNAL)
            _raise_on_error(ret, "Trigger konnte nicht gesetzt werden")

            ret = llt.set_feature(hllt, llt.FEATURE_FUNCTION_EXPOSURE_TIME, settings.exposure_us)
            _raise_on_error(ret, "Belichtungszeit konnte nicht gesetzt werden")

            ret = llt.set_feature(hllt, llt.FEATURE_FUNCTION_IDLE_TIME, settings.idle_time_us)
            _raise_on_error(ret, "Idle-Zeit konnte nicht gesetzt werden")

            _ensure_laser_enabled(hllt, llt)
            time.sleep(SETTLE_TIME_S)

            ret = llt.transfer_profiles(hllt, llt.TTransferProfileType.NORMAL_TRANSFER, 1)
            _raise_on_error(ret, "Profilübertragung konnte nicht gestartet werden")

            self.hllt = hllt
            self._resolution = resolution
            self._scanner_type_enum = llt.TScannerType(int(scanner_type.value))
            self._profile_buffer = (ct.c_ubyte * (resolution * 64))()
            self._x = (ct.c_double * resolution)()
            self._z = (ct.c_double * resolution)()
            self._intensities = (ct.c_ushort * resolution)()
            self._lost_profiles = ct.c_int()
            self._transfer_active = True
            self._settings_signature = signature
            self._scanner_ip = scanner_ip
        except Exception:
            try:
                llt.disconnect(hllt)
            except Exception:
                pass
            try:
                llt.del_device(hllt)
            except Exception:
                pass
            self.hllt = None
            self._transfer_active = False
            raise

    def _read_profile(self, settings: ScanSettings) -> dict:
        deadline = time.time() + 2.0
        while time.time() < deadline:
            ret = self.llt.get_actual_profile(
                self.hllt,
                self._profile_buffer,
                len(self._profile_buffer),
                self.llt.TProfileConfig.PROFILE,
                ct.byref(self._lost_profiles),
            )
            if ret != len(self._profile_buffer):
                if ret == self.llt.ERROR_PROFTRANS_NO_NEW_PROFILE:
                    time.sleep(
                        (settings.idle_time_us + settings.exposure_us) / 1_000_000
                    )
                    continue
                raise ScanError(f"Profil konnte nicht gelesen werden: {ret}")

            convert_ret = self.llt.convert_profile_2_values(
                self.hllt,
                self._profile_buffer,
                self._resolution,
                self.llt.TProfileConfig.PROFILE,
                self._scanner_type_enum,
                0,
                1,
                self._null_ptr_short,
                self._intensities,
                self._null_ptr_short,
                self._x,
                self._z,
                self._null_ptr_int,
                self._null_ptr_int,
            )
            if (
                convert_ret & self.llt.CONVERT_X == 0
                or convert_ret & self.llt.CONVERT_Z == 0
                or convert_ret & self.llt.CONVERT_MAXIMUM == 0
            ):
                raise ScanError(f"Profil konnte nicht konvertiert werden: {convert_ret}")

            return {
                "x_mm": [float(value) for value in self._x],
                "z_mm": [float(value) for value in self._z],
                "intensities": [int(value) for value in self._intensities],
                "resolution": self._resolution,
            }

        raise ScanError("Kein Live-Profil innerhalb von 2 s empfangen.")


_live_preview_lock = threading.RLock()
_live_preview: LiveProfilePreview | None = None


def get_live_profile_preview() -> LiveProfilePreview:
    global _live_preview

    with _live_preview_lock:
        if _live_preview is None:
            _live_preview = LiveProfilePreview()
        return _live_preview


def close_live_profile_preview() -> None:
    global _live_preview

    with _live_preview_lock:
        if _live_preview is not None:
            _live_preview.close()
            _live_preview = None


def capture_live_profile(scanner_ip: str | None, settings: ScanSettings) -> dict:
    preview = get_live_profile_preview()
    return preview.capture(scanner_ip, settings)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="scanCONTROL Scan ausführen")
    parser.add_argument("--experiment-id", required=True, help="3-stellige Versuchs-ID")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Zielordner für Scan-Dateien",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Demo-Scan ohne angeschlossenen scanCONTROL",
    )
    parser.add_argument(
        "--scanner-ip",
        default=os.environ.get("SCANNER_IP", "").strip() or None,
        help="IP des scanCONTROL (überspringt SDK-Suche; auch per SCANNER_IP)",
    )
    parser.add_argument("--resolution", type=int, default=None, help="Profilauflösung")
    parser.add_argument(
        "--profile-frequency",
        type=float,
        default=None,
        help="Profile pro Sekunde (Hz)",
    )
    parser.add_argument("--exposure-us", type=int, default=None, help="Belichtungszeit in µs")
    parser.add_argument("--scan-duration-s", type=float, default=None, help="Scan-Dauer in s")
    parser.add_argument(
        "--scan-duration-auto",
        action="store_true",
        help="SCANDURATION ignorieren; Probe automatisch erkennen",
    )
    return parser.parse_args()


def _build_scan_settings(args: argparse.Namespace) -> ScanSettings | None:
    setting_args = (
        args.resolution,
        args.profile_frequency,
        args.exposure_us,
        args.scan_duration_s,
    )
    if all(value is None for value in setting_args) and not args.scan_duration_auto:
        return None

    missing = []
    if args.resolution is None:
        missing.append("resolution")
    if args.profile_frequency is None:
        missing.append("profile-frequency")
    if args.exposure_us is None:
        missing.append("exposure-us")
    if args.scan_duration_s is None and not args.scan_duration_auto:
        missing.append("scan-duration-s")
    if missing:
        raise ScanError(
            "Unvollständige Scan-Einstellungen. Fehlend: " + ", ".join(missing)
        )

    return ScanSettings.from_profile_frequency(
        resolution=args.resolution,
        profile_frequency=args.profile_frequency,
        exposure_us=args.exposure_us,
        scan_duration_s=args.scan_duration_s if args.scan_duration_s is not None else 1.0,
        scan_duration_auto=args.scan_duration_auto,
    )


def main() -> int:
    args = parse_args()
    experiment_id = args.experiment_id.strip().upper()

    if len(experiment_id) != 3 or not experiment_id.isalpha():
        print(json.dumps({"success": False, "error": "ID muss aus 3 Buchstaben bestehen."}))
        return 1

    try:
        settings = _build_scan_settings(args)
        result = run_scan(
            experiment_id,
            Path(args.output_dir),
            demo=args.demo,
            scanner_ip=args.scanner_ip,
            settings=settings,
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except ScanError as exc:
        print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    except Exception as exc:
        print(json.dumps({"success": False, "error": f"Unerwarteter Fehler: {exc}"}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
