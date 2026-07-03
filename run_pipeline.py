#!/usr/bin/env python3
"""Unified reproducibility entrypoint for the CAD -> osmAG pipeline."""

from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml


REPO_ROOT = Path(__file__).resolve().parent


BUILTIN_DEFAULTS: Dict[str, Any] = {
    "map_preprocessing": {
        "clean_input": False,
        "resolution": 0.044,
        "door_width": 1.0,
        "corridor_width": 1.5,
        "noise_percent": 1.5,
        "remove_furniture": True,
    },
    "root_node": {
        "latitude": 31.17947960435,
        "longitude": 121.59139728509,
        "pixel_x": 3804.0,
        "pixel_y": 2801.0,
    },
    "png_dimensions": {
        "width": None,
        "height": None,
        "resolution": 0.044,
    },
    "polygon_processing": {
        "simplify": {
            "enabled": True,
            "tolerance": 1.2,
        },
        "spike_removal": {
            "enabled": True,
            "angle_threshold": 15.0,
            "distance_threshold": 0.30,
        },
        "small_room_filter": {
            "enabled": True,
            "min_area": 10.0,
        },
        "small_room_merge": {
            "enabled": False,
            "min_area": 10.0,
            "max_merge_distance": 3.0,
        },
    },
    "coordinate_conversion": {
        "padding_ratio": 0.03,
    },
    "area_graph": {
        "alpha": {
            "mode": "dynamic",
            "fixed_value": None,
            "width_offset": 0.1,
            "outside_removal_alpha": 3600,
        },
        "furniture_removal": {
            "max_polygon_length": 80,
        },
        "vori_config": {
            "first_dead_end_removal_distance": 100000,
            "second_dead_end_removal_distance": -100000,
            "third_dead_end_removal_distance_meters": 0.25,
            "fourth_dead_end_removal_distance": 8,
            "topo_graph_angle_calc_end_distance": 10,
            "topo_graph_angle_calc_start_distance": 3,
            "topo_graph_angle_calc_step_size": 0.1,
            "topo_graph_distance_to_join_vertices": 4,
            "topo_graph_mark_as_feature_edge_length": 20,
            "voronoi_minimum_distance_to_obstacle_meters": 0.25,
        },
    },
    "level": "1",
    "height_per_level": 3.2,
}


def deep_merge(base: Dict[str, Any], overlay: Dict[str, Any] | None) -> Dict[str, Any]:
    result = copy.deepcopy(base)
    if not overlay:
        return result

    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def read_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config root must be a mapping: {path}")
    return data


def write_yaml(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False, allow_unicode=True)


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def resolve_path(path_value: str | os.PathLike[str]) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def parse_scalar(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "yes", "on"}:
        return True
    if lowered in {"false", "no", "off"}:
        return False
    if lowered in {"null", "none"}:
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def set_nested(config: Dict[str, Any], dotted_key: str, value: Any) -> None:
    node = config
    parts = dotted_key.split(".")
    for part in parts[:-1]:
        node = node.setdefault(part, {})
        if not isinstance(node, dict):
            raise ValueError(f"Cannot set nested key through non-mapping: {dotted_key}")
    node[parts[-1]] = value


def import_preprocessing_modules() -> Any:
    core_path = REPO_ROOT / "cad2osm" / "script" / "core_process"
    sys.path.insert(0, str(core_path))
    from dxf2svg import dxf_to_svg
    from svg2png import save_occupancy_grid, svg_to_occupancy_grid

    return dxf_to_svg, svg_to_occupancy_grid, save_occupancy_grid


def run_command(command: List[str], cwd: Path) -> None:
    print(f"$ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=str(cwd), check=True)


def latest_file(pattern: str, directory: Path) -> Path | None:
    matches = list(directory.glob(pattern))
    if not matches:
        return None
    return max(matches, key=lambda item: item.stat().st_mtime)


def build_effective_config(config: Dict[str, Any], case_name: str, args: argparse.Namespace) -> Dict[str, Any]:
    cases = config.get("cases", {})
    if case_name not in cases:
        known = ", ".join(sorted(cases.keys()))
        raise KeyError(f"Unknown case '{case_name}'. Known cases: {known}")

    case_config = cases[case_name] or {}
    profile_name = case_config.get("profile", "default")
    profile_config = (config.get("profiles", {}) or {}).get(profile_name, {})

    effective = deep_merge(BUILTIN_DEFAULTS, config.get("global", {}))
    effective = deep_merge(effective, profile_config)
    effective = deep_merge(effective, case_config.get("overrides", {}))

    cli_overrides = {
        "map_preprocessing.resolution": args.resolution,
        "root_node.latitude": args.root_lat,
        "root_node.longitude": args.root_lon,
        "root_node.pixel_x": args.root_pixel_x,
        "root_node.pixel_y": args.root_pixel_y,
        "polygon_processing.small_room_filter.min_area": args.min_room_area,
    }
    for key, value in cli_overrides.items():
        if value is not None:
            set_nested(effective, key, value)

    for raw_override in args.set or []:
        if "=" not in raw_override:
            raise ValueError(f"--set expects key=value, got: {raw_override}")
        key, value = raw_override.split("=", 1)
        set_nested(effective, key, parse_scalar(value))

    effective["png_dimensions"]["resolution"] = effective["map_preprocessing"]["resolution"]
    return effective


def create_manifest(
    args: argparse.Namespace,
    config_path: Path,
    case_name: str,
    case_config: Dict[str, Any],
    effective_config_path: Path,
    manifest_path: Path,
    paths: Dict[str, Path],
    commands: List[Dict[str, Any]],
    outputs: Dict[str, str | None],
) -> Dict[str, Any]:
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "case": case_name,
        "dry_run": args.dry_run,
        "with_text": args.with_text,
        "config": str(config_path.relative_to(REPO_ROOT)),
        "effective_config": str(effective_config_path.relative_to(REPO_ROOT)),
        "manifest": str(manifest_path.relative_to(REPO_ROOT)),
        "input": {
            "dxf": str(paths["dxf"].relative_to(REPO_ROOT)),
            "profile": case_config.get("profile", "default"),
        },
        "outputs": outputs,
        "commands": commands,
    }


def run_case(args: argparse.Namespace) -> None:
    config_path = resolve_path(args.config)
    config = read_yaml(config_path)

    if args.list_cases:
        for case_name in sorted((config.get("cases") or {}).keys()):
            print(case_name)
        return

    if not args.case:
        raise SystemExit("--case is required unless --list-cases is used")

    cases = config.get("cases", {})
    case_config = cases[args.case]
    effective = build_effective_config(config, args.case, args)

    pipeline_config = config.get("pipeline", {}) or {}
    preprocessing_config = config.get("preprocessing", {}) or {}
    output_root = resolve_path(args.output_root or pipeline_config.get("output_root", "runs/web-cad"))
    case_output_dir = output_root / args.case
    preprocess_dir = case_output_dir / "preprocess"
    area_graph_dir = case_output_dir / "area_graph"
    text_dir = case_output_dir / "text"
    effective_config_path = case_output_dir / "effective_config.yaml"
    manifest_path = case_output_dir / "run_manifest.json"

    dxf_path = resolve_path(case_config["dxf"])
    svg_path = preprocess_dir / f"{args.case}.svg"
    png_path = preprocess_dir / f"{args.case}.png"
    bounds_path = preprocess_dir / f"{args.case}.bounds.json"
    executable = resolve_path(args.area_graph_executable or pipeline_config.get("area_graph_executable", "area_graph_segment/build/bin/area_graph_segmentation"))

    commands: List[Dict[str, Any]] = []
    outputs: Dict[str, str | None] = {
        "svg": str(svg_path.relative_to(REPO_ROOT)),
        "bounds": str(bounds_path.relative_to(REPO_ROOT)),
        "png": str(png_path.relative_to(REPO_ROOT)),
        "area_graph_dir": str(area_graph_dir.relative_to(REPO_ROOT)),
        "osm": None,
        "room_graph": None,
        "texted_osm": None,
    }

    if not dxf_path.is_file():
        raise FileNotFoundError(f"Input DXF does not exist: {dxf_path}")
    if not args.dry_run and not executable.is_file():
        raise FileNotFoundError(f"area_graph_segmentation executable does not exist: {executable}")

    preprocess_dir.mkdir(parents=True, exist_ok=True)
    area_graph_dir.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        write_yaml(effective_config_path, effective)
        area_graph_command = [
            str(executable),
            str(png_path),
            "--config",
            str(effective_config_path),
            "--output-dir",
            str(area_graph_dir),
            "--dump-effective-config",
        ]
        commands.extend([
            {
                "stage": "dxf_to_svg",
                "command": f"dxf_to_svg({dxf_path}, {svg_path})",
                "executed": False,
            },
            {
                "stage": "svg_to_png",
                "command": f"svg_to_occupancy_grid({svg_path}, {png_path})",
                "executed": False,
            },
            {
                "stage": "area_graph",
                "command": " ".join(area_graph_command),
                "executed": False,
            },
        ])
        if args.with_text or pipeline_config.get("text_enabled", False):
            text_output = text_dir / f"{args.case}_texted.osm"
            commands.append({
                "stage": "text",
                "command": f"text_extractor.py --mode full --dxf {dxf_path} --bounds {bounds_path} --osm <area_graph_osm> --output {text_output}",
                "executed": False,
            })
        manifest = create_manifest(args, config_path, args.case, case_config, effective_config_path, manifest_path, {
            "dxf": dxf_path,
        }, commands, outputs)
        write_json(manifest_path, manifest)
        print(f"Dry run complete. Effective config: {effective_config_path}", flush=True)
        print(f"Manifest: {manifest_path}", flush=True)
        for command in commands:
            print(f"[{command['stage']}] {command['command']}", flush=True)
        return

    dxf_to_svg, svg_to_occupancy_grid, save_occupancy_grid = import_preprocessing_modules()

    target_size = int(preprocessing_config.get("target_size", 4000))
    line_thickness = int(preprocessing_config.get("line_thickness", 1))
    enable_wall_filling = bool(preprocessing_config.get("enable_wall_filling", False))
    wall_gap_size = preprocessing_config.get("wall_gap_size", "medium")
    wall_min_area = int(preprocessing_config.get("wall_min_area", 100))

    print(f"Converting DXF to SVG: {dxf_path}", flush=True)
    success, message = dxf_to_svg(str(dxf_path), str(svg_path), target_size=target_size, config=effective)
    commands.append({
        "stage": "dxf_to_svg",
        "command": f"dxf_to_svg({dxf_path}, {svg_path}, target_size={target_size})",
        "executed": True,
        "success": success,
        "message": message,
    })
    if not success:
        raise RuntimeError(message)

    print(f"Converting SVG to PNG: {svg_path}", flush=True)
    grid = svg_to_occupancy_grid(
        str(svg_path),
        output_size=(target_size, target_size),
        line_thickness=line_thickness,
        enable_wall_filling=enable_wall_filling,
        gap_size=wall_gap_size,
        min_area=wall_min_area,
    )
    save_occupancy_grid(grid, str(png_path))
    commands.append({
        "stage": "svg_to_png",
        "command": f"svg_to_occupancy_grid({svg_path}, {png_path})",
        "executed": True,
        "success": True,
    })

    try:
        from PIL import Image

        with Image.open(png_path) as image:
            effective["png_dimensions"]["width"] = image.width
            effective["png_dimensions"]["height"] = image.height
    except Exception as exc:
        print(f"Warning: failed to read PNG dimensions: {exc}", flush=True)

    write_yaml(effective_config_path, effective)

    area_graph_command = [
        str(executable),
        str(png_path),
        "--config",
        str(effective_config_path),
        "--output-dir",
        str(area_graph_dir),
        "--dump-effective-config",
    ]
    run_command(area_graph_command, REPO_ROOT)
    commands.append({
        "stage": "area_graph",
        "command": " ".join(area_graph_command),
        "executed": True,
        "success": True,
    })

    osm_output = latest_file("*_osmAG.osm", area_graph_dir)
    room_graph_output = latest_file("*_roomGraph.png", area_graph_dir)
    outputs["osm"] = str(osm_output.relative_to(REPO_ROOT)) if osm_output else None
    outputs["room_graph"] = str(room_graph_output.relative_to(REPO_ROOT)) if room_graph_output else None

    if args.with_text or pipeline_config.get("text_enabled", False):
        if not osm_output:
            raise RuntimeError("Cannot run text stage because no osmAG output was found")
        text_dir.mkdir(parents=True, exist_ok=True)
        text_output = text_dir / f"{args.case}_texted.osm"
        text_command = [
            sys.executable,
            str(REPO_ROOT / "cad2osm" / "script" / "text_extract_module" / "text_extractor.py"),
            "--mode",
            "full",
            "--dxf",
            str(dxf_path),
            "--bounds",
            str(bounds_path),
            "--osm",
            str(osm_output),
            "--output",
            str(text_output),
            "--config",
            str(effective_config_path),
        ]
        if args.visualize_text:
            text_command.append("--visualize")
        run_command(text_command, REPO_ROOT)
        commands.append({
            "stage": "text",
            "command": " ".join(text_command),
            "executed": True,
            "success": True,
        })
        outputs["texted_osm"] = str(text_output.relative_to(REPO_ROOT))

    manifest = create_manifest(args, config_path, args.case, case_config, effective_config_path, manifest_path, {
        "dxf": dxf_path,
    }, commands, outputs)
    write_json(manifest_path, manifest)
    print(f"Pipeline complete. Manifest: {manifest_path}", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the reproducible CAD -> osmAG pipeline")
    parser.add_argument("--config", default="config/repro_web_cad.yaml", help="Pipeline YAML config")
    parser.add_argument("--case", help="Case name from the config")
    parser.add_argument("--list-cases", action="store_true", help="List configured cases and exit")
    parser.add_argument("--dry-run", action="store_true", help="Write effective config/manifest and print planned commands")
    parser.add_argument("--with-text", action="store_true", help="Run optional text naming stage")
    parser.add_argument("--visualize-text", action="store_true", help="Generate text matching visualization when --with-text is used")
    parser.add_argument("--output-root", help="Override pipeline.output_root")
    parser.add_argument("--area-graph-executable", help="Override path to area_graph_segmentation")
    parser.add_argument("--resolution", type=float, help="Override map_preprocessing.resolution")
    parser.add_argument("--root-lat", type=float, help="Override root_node.latitude")
    parser.add_argument("--root-lon", type=float, help="Override root_node.longitude")
    parser.add_argument("--root-pixel-x", type=float, help="Override root_node.pixel_x")
    parser.add_argument("--root-pixel-y", type=float, help="Override root_node.pixel_y")
    parser.add_argument("--min-room-area", type=float, help="Override polygon_processing.small_room_filter.min_area")
    parser.add_argument("--set", action="append", help="Generic effective config override, e.g. --set area_graph.alpha.fixed_value=3600")
    return parser.parse_args()


def main() -> int:
    try:
        run_case(parse_args())
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
