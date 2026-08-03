#!/usr/bin/env python3
"""
Convert pattern G-code files to SVG previews (path_images layout).

Usage:
    python gcode_to_svg.py spiral_outside_in.gcode.txt
    python gcode_to_svg.py *.gcode.txt
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

OUTER_SIZE = 80.0
SVG_MARGIN = 5.0

PATTERN_CATALOG = {
    "spiral_outside_in": {
        "path_id": "SO",
        "title": "Outside-In Spiral",
        "description": "Clockwise spiral from the outer 50×50 mm boundary inward.",
    },
    "spiral_inside_out": {
        "path_id": "SI",
        "title": "Inside-Out Spiral",
        "description": "Reverse of the outside-in spiral, traced from the centre outward.",
    },
    "meander_vertical": {
        "path_id": "ME",
        "title": "Vertical Meander",
        "description": "Serpentine columns stepping left-to-right, alternating down/up strokes.",
    },
    "meander_bordered": {
        "path_id": "PO",
        "title": "Bordered Meander (48×48 mm)",
        "description": "Open perimeter with 4 mm gap, then vertical serpentine fill in 48×48 mm.",
    },
    "hatch_diagonal": {
        "path_id": "LI",
        "title": "Bordered 45° Diagonal Hatch",
        "description": "Open 50×50 mm perimeter, then 45° hatch strokes 4 mm inside the border.",
    },
}

_COORD = re.compile(r"([XYZ])([-+]?(?:\d+(?:\.\d*)?|\.\d+))")
_TITLE_SIZE = re.compile(r"\((\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)", re.I)
_OUTER = re.compile(r"outer\s+square\s*:\s*(\d+(?:\.\d+)?)", re.I)
_PATTERN = re.compile(r"pattern\s+area\s*:\s*(\d+(?:\.\d+)?)", re.I)
_SPACING = re.compile(r"spacing\s*:\s*(\d+(?:\.\d+)?)", re.I)


def lookup_pattern_info(stem: str) -> dict | None:
    normalized = stem.lower().replace(".gcode", "")
    return PATTERN_CATALOG.get(normalized)


def pattern_stem_from_path(gcode_path: Path) -> str:
    name = gcode_path.name
    if name.endswith(".gcode.txt"):
        return name[: -len(".gcode.txt")]
    if name.endswith(".gcode"):
        return name[: -len(".gcode")]
    return gcode_path.stem


def svg_output_path(gcode_path: Path) -> Path:
    stem = pattern_stem_from_path(gcode_path)
    info = lookup_pattern_info(stem)
    if info and info.get("path_id"):
        return gcode_path.parent / f"{info['path_id']}.svg"
    name = gcode_path.name
    if name.endswith(".gcode.txt"):
        return gcode_path.with_name(name[: -len(".gcode.txt")] + ".svg")
    if name.endswith(".gcode"):
        return gcode_path.with_name(name[: -len(".gcode")] + ".svg")
    return gcode_path.with_suffix(".svg")


def _gcode_to_svg_xy(x: float, y: float, outer_size: float) -> tuple[float, float]:
    """G-code: origin bottom-left, Y up. SVG view: X mirrored, Y flipped."""
    return outer_size - x, outer_size - y


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


def _append_point(points: list[tuple[float, float]], x: float, y: float) -> None:
    if points and points[-1] == (x, y):
        return
    points.append((x, y))


def _parse_header_comment(comment: str, state: dict) -> None:
    if comment.startswith("="):
        return

    if not state["title"] and comment:
        lowered = comment.lower()
        if (
            "outer square" not in lowered
            and "pattern area" not in lowered
            and "spacing" not in lowered
            and "corners" not in lowered
            and "origin" not in lowered
            and not lowered.startswith("z=")
        ):
            state["title"] = comment
            return

    if match := _OUTER.search(comment):
        state["outer_size"] = float(match.group(1))
    if match := _PATTERN.search(comment):
        state["pattern_size"] = float(match.group(1))
    if match := _SPACING.search(comment):
        state["spacing"] = float(match.group(1))
    if match := _TITLE_SIZE.search(comment):
        state["boundary_size"] = float(match.group(1))


def parse_gcode_file(path: Path) -> dict:
    state = {
        "title": path.stem.replace("_", " "),
        "outer_size": OUTER_SIZE,
        "pattern_size": 50.0,
        "spacing": 4.0,
        "boundary_size": None,
    }

    points: list[tuple[float, float]] = []
    drawing = False
    pending_start: tuple[float, float] | None = None
    current_x: float | None = None
    current_y: float | None = None

    with path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            comment = ""
            if ";" in raw_line:
                comment = raw_line.split(";", 1)[1].strip()
                if comment:
                    _parse_header_comment(comment, state)
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
                        points.append(pending_start)
                        pending_start = None
                    drawing = True
                elif z >= 4.999:
                    drawing = False

            if cmd == "G1" and z is not None and z <= 0.001:
                drawing = True

            if cmd in {"G0", "G1"} and current_x is not None and current_y is not None:
                svg_x, svg_y = _gcode_to_svg_xy(current_x, current_y, state["outer_size"])
                if drawing:
                    _append_point(points, svg_x, svg_y)
                elif cmd == "G0" and not drawing and z is None:
                    pending_start = (svg_x, svg_y)

    boundary_size = state["boundary_size"] if state["boundary_size"] is not None else state["pattern_size"]

    if not points:
        raise ValueError(f"No drawing points found in {path}")

    return {
        "points": points,
        "title": state["title"],
        "outer_size": state["outer_size"],
        "boundary_size": boundary_size,
        "spacing": state["spacing"],
    }


def _append_coordinate_axes(lines: list[str], outer_size: float = OUTER_SIZE, axis_length: float = 10.0) -> None:
    ox, oy = outer_size, outer_size
    x_end = (ox - axis_length, oy)
    y_end = (ox, oy - axis_length)
    x_label = (ox - axis_length - 0.5, oy + 2.2)
    y_label = (ox + 1.0, oy - axis_length - 0.5)
    origin_label = (ox + 1.0, oy + 2.4)

    lines.append(
        f'  <line x1="{ox:.2f}" y1="{oy:.2f}" x2="0" y2="{oy:.2f}"'
        f' stroke="#64748b" stroke-width="0.25" stroke-dasharray="1,1"/>'
    )
    lines.append(
        f'  <line x1="{ox:.2f}" y1="{oy:.2f}" x2="{ox:.2f}" y2="0"'
        f' stroke="#64748b" stroke-width="0.25" stroke-dasharray="1,1"/>'
    )
    lines.append(f'  <circle cx="{ox:.2f}" cy="{oy:.2f}" r="0.75" fill="#0f172a"/>')
    lines.append(
        f'  <text x="{origin_label[0]:.2f}" y="{origin_label[1]:.2f}"'
        f' font-size="2" font-family="sans-serif" font-weight="bold" fill="#0f172a">O</text>'
    )
    lines.append(
        f'  <line x1="{ox:.2f}" y1="{oy:.2f}" x2="{x_end[0]:.2f}" y2="{x_end[1]:.2f}"'
        f' stroke="#dc2626" stroke-width="0.45" marker-end="url(#axis-arrow)"/>'
    )
    lines.append(
        f'  <text x="{x_label[0]:.2f}" y="{x_label[1]:.2f}" font-size="2.2"'
        f' font-family="sans-serif" font-weight="bold" fill="#dc2626">X</text>'
    )
    lines.append(
        f'  <line x1="{ox:.2f}" y1="{oy:.2f}" x2="{y_end[0]:.2f}" y2="{y_end[1]:.2f}"'
        f' stroke="#16a34a" stroke-width="0.45" marker-end="url(#axis-arrow)"/>'
    )
    lines.append(
        f'  <text x="{y_label[0]:.2f}" y="{y_label[1]:.2f}" font-size="2.2"'
        f' font-family="sans-serif" font-weight="bold" fill="#16a34a">Y</text>'
    )


def _append_svg_captions(
    lines: list[str],
    *,
    title: str,
    boundary_size: float,
    point_count: int,
    spacing: float,
    path_id: str | None = None,
) -> None:
    edge_mm = (OUTER_SIZE - boundary_size) / 2.0
    heading = f"80 x 80 mm - {title}"
    if path_id:
        heading += f" ({path_id})"

    lines.append(
        f'  <text x="{OUTER_SIZE / 2:.1f}" y="5" text-anchor="middle"'
        f' font-size="3.2" font-family="sans-serif" fill="#333">{heading}</text>'
    )

    lines.append(
        f'  <text x="{OUTER_SIZE / 2:.1f}" y="{OUTER_SIZE - 2:.1f}" text-anchor="middle"'
        f' font-size="2.8" font-family="sans-serif" fill="#555">'
        f"{boundary_size:.0f} x {boundary_size:.0f} mm | {edge_mm:.0f} mm edge"
        f" | {spacing:.0f} mm spacing | {point_count} corners</text>"
    )


def write_svg(
    points: list[tuple[float, float]],
    filepath: str | Path,
    *,
    title: str = "",
    boundary_size: float,
    spacing: float,
    pattern_stem: str | None = None,
) -> None:
    info = lookup_pattern_info(pattern_stem) if pattern_stem else None
    if info:
        title = info.get("title") or title
        path_id = info.get("path_id")
    else:
        path_id = None

    bsz = boundary_size
    boff = (OUTER_SIZE - bsz) / 2.0
    margin = SVG_MARGIN
    view_extent = OUTER_SIZE + 2 * margin
    scale = 5
    width = height = view_extent * scale

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"'
        f' viewBox="{-margin} {-margin} {view_extent} {view_extent}">',
        "  <defs>",
        '    <marker id="axis-arrow" markerWidth="4" markerHeight="4" refX="3.2" refY="2"'
        ' orient="auto" markerUnits="strokeWidth">',
        '      <path d="M0,0 L4,2 L0,4 Z" fill="context-stroke"/>',
        "    </marker>",
        "  </defs>",
        f'  <rect x="{-margin}" y="{-margin}" width="{view_extent}" height="{view_extent}" fill="white"/>',
        f'  <rect width="{OUTER_SIZE}" height="{OUTER_SIZE}" fill="white"/>',
        f'  <rect x="{boff}" y="{boff}" width="{bsz}" height="{bsz}"'
        f' fill="none" stroke="#bbb" stroke-width="0.2" stroke-dasharray="1.5,1.5"/>',
    ]

    _append_coordinate_axes(lines)

    path_data = f"M {points[0][0]:.2f},{points[0][1]:.2f}"
    for x, y in points[1:]:
        path_data += f" L {x:.2f},{y:.2f}"
    lines.append(
        f'  <path d="{path_data}" fill="none" stroke="#2563eb"'
        f' stroke-width="0.35" stroke-linejoin="round"/>'
    )

    sx, sy = points[0]
    lines.append(f'  <circle cx="{sx}" cy="{sy}" r="0.9" fill="#16a34a"/>')
    lines.append(
        f'  <text x="{sx + 1.2}" y="{sy - 1}" font-size="2.2"'
        f' font-family="sans-serif" font-weight="bold" fill="#16a34a">START</text>'
    )
    ex, ey = points[-1]
    lines.append(f'  <circle cx="{ex}" cy="{ey}" r="0.9" fill="#ea580c"/>')
    lines.append(
        f'  <text x="{ex + 1.2}" y="{ey + 2.2}" font-size="2.2"'
        f' font-family="sans-serif" font-weight="bold" fill="#ea580c">END</text>'
    )

    for index, (x, y) in enumerate(points, 1):
        lines.append(f'  <circle cx="{x}" cy="{y}" r="0.55" fill="#dc2626"/>')
        lines.append(
            f'  <text x="{x + 1}" y="{y - 0.8}" font-size="2"'
            f' font-family="monospace" fill="#555">{index}</text>'
        )

    _append_svg_captions(
        lines,
        title=title,
        boundary_size=bsz,
        point_count=len(points),
        spacing=spacing,
        path_id=path_id,
    )
    lines.append("</svg>")

    Path(filepath).write_text("\n".join(lines) + "\n", encoding="utf-8")


def gcode_to_svg(gcode_path: Path, svg_path: Path | None = None) -> tuple[Path, dict]:
    payload = parse_gcode_file(gcode_path)
    if svg_path is None:
        svg_path = svg_output_path(gcode_path)

    if payload["outer_size"] != OUTER_SIZE:
        raise ValueError(
            f"{gcode_path}: outer size {payload['outer_size']} mm is not supported "
            f"(expected {OUTER_SIZE} mm)."
        )

    write_svg(
        payload["points"],
        svg_path,
        title=payload["title"],
        boundary_size=payload["boundary_size"],
        spacing=payload["spacing"],
        pattern_stem=pattern_stem_from_path(gcode_path),
    )
    return svg_path, payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convert pattern G-code files to SVG previews.")
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="G-code file(s), e.g. spiral_outside_in.gcode.txt",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output SVG path (only valid for a single input file)",
    )
    args = parser.parse_args(argv)

    if args.output is not None and len(args.inputs) != 1:
        parser.error("--output requires exactly one input file.")

    errors = 0
    for input_path in args.inputs:
        try:
            svg_path, payload = gcode_to_svg(input_path, args.output)
            print(f"{input_path.name} -> {svg_path.name} ({len(payload['points'])} corners)")
        except (OSError, ValueError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            errors += 1

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
