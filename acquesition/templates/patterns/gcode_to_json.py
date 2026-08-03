#!/usr/bin/env python3
"""
Extract G-code draw paths as minimal JSON vector polylines.

Output is only the paths: a list of polylines, each a list of [x, y] points
in G-code coordinates (mm, origin bottom-left, Y up). No metadata.

Files are written as PATH_ID.json next to the G-code (SO, SI, ME, PO, LI).

Usage:
    python gcode_to_json.py
    python gcode_to_json.py spiral_outside_in.gcode.txt
    python gcode_to_json.py *.gcode.txt
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from gcode_to_svg import lookup_pattern_info, pattern_stem_from_path

_COORD = re.compile(r"([XYZ])([-+]?(?:\d+(?:\.\d*)?|\.\d+))")


def _parse_move(line_body: str) -> tuple[float | None, float | None, float | None]:
    x = y = z = None
    for axis, value in _COORD.findall(line_body):
        if axis == "X":
            x = float(value)
        elif axis == "Y":
            y = float(value)
        elif axis == "Z":
            z = float(value)
    return x, y, z


def _append_point(points: list[list[float]], x: float, y: float) -> None:
    point = [round(x, 6), round(y, 6)]
    if points and points[-1] == point:
        return
    points.append(point)


def extract_paths(gcode_path: Path) -> list[list[list[float]]]:
    """Return draw polylines as [[[x, y], ...], ...]."""
    paths: list[list[list[float]]] = []
    current_path: list[list[float]] = []
    drawing = False
    pending_start: tuple[float, float] | None = None
    current_x: float | None = None
    current_y: float | None = None

    with gcode_path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.split(";", 1)[0].strip()
            if not line:
                continue

            cmd = line.split()[0].upper()
            x, y, z = _parse_move(line)

            if x is not None:
                current_x = x
            if y is not None:
                current_y = y

            if z is not None:
                if z <= 0.001:
                    if pending_start is not None:
                        current_path = []
                        _append_point(current_path, pending_start[0], pending_start[1])
                        pending_start = None
                    drawing = True
                elif z >= 4.999:
                    if len(current_path) >= 2:
                        paths.append(current_path)
                    current_path = []
                    drawing = False

            if cmd == "G1" and z is not None and z <= 0.001:
                drawing = True

            if cmd in {"G0", "G1"} and current_x is not None and current_y is not None:
                if drawing:
                    if not current_path and pending_start is not None:
                        _append_point(current_path, pending_start[0], pending_start[1])
                        pending_start = None
                    _append_point(current_path, current_x, current_y)
                elif cmd == "G0" and not drawing and z is None:
                    pending_start = (current_x, current_y)

    if len(current_path) >= 2:
        paths.append(current_path)

    if not paths:
        raise ValueError(f"No draw paths found in {gcode_path}")

    return paths


def json_output_path(gcode_path: Path) -> Path:
    stem = pattern_stem_from_path(gcode_path)
    info = lookup_pattern_info(stem)
    if not info or not info.get("path_id"):
        raise ValueError(f"No PATH ID mapping for pattern stem '{stem}' ({gcode_path.name})")
    return gcode_path.parent / f"{info['path_id']}.json"


def gcode_to_json(gcode_path: Path, json_path: Path | None = None) -> Path:
    paths = extract_paths(gcode_path)
    output = json_path or json_output_path(gcode_path)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(paths, handle, separators=(",", ":"))
        handle.write("\n")
    return output


def _expand_inputs(values: list[str], directory: Path) -> list[Path]:
    if not values:
        return sorted(directory.glob("*.gcode.txt"))

    paths: list[Path] = []
    for value in values:
        candidate = Path(value)
        if candidate.exists():
            paths.append(candidate.resolve())
            continue
        matches = sorted(directory.glob(value))
        if not matches:
            raise FileNotFoundError(f"No G-code match for: {value}")
        paths.extend(path.resolve() for path in matches)
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convert pattern G-code files to PATH_ID.json vector paths.")
    parser.add_argument(
        "inputs",
        nargs="*",
        help="G-code files or globs (default: all *.gcode.txt in this folder)",
    )
    args = parser.parse_args(argv)

    directory = Path(__file__).resolve().parent
    try:
        gcode_paths = _expand_inputs(args.inputs, directory)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    if not gcode_paths:
        print("No G-code files found.", file=sys.stderr)
        return 1

    errors = 0
    for gcode_path in gcode_paths:
        try:
            output = gcode_to_json(gcode_path)
            print(f"{gcode_path.name} -> {output.name}")
        except Exception as exc:
            errors += 1
            print(f"{gcode_path.name}: {exc}", file=sys.stderr)

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
