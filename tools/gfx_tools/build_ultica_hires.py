#!/usr/bin/env python3
"""Build and validate the private Ultica HiRes common-terrain overlay.

The reviewed 64x64 sprites are the canonical inputs.  This tool locates their
32x32 source sprites by tile ID, builds a small 64x64 atlas, and appends an
override sheet with pixelscale 0.5 to the existing 0.G-compatible tileset.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import random
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageStat


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TILESET_DIR = REPO_ROOT / "gfx" / "UltimateCataclysm"
DEFAULT_ASSET_DIR = Path(__file__).resolve().parent / "ultica_hires"
DEFAULT_REVIEW_DIR = REPO_ROOT / "data" / "screenshots" / "ultica_hires"
ATLAS_NAME = "hires_pilot.png"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(f"{path.stem}.tmp{path.suffix}")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def atomic_save_png(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.stem}.tmp{path.suffix}")
    image.save(temporary)
    temporary.replace(path)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pixel_sha256(image: Image.Image) -> str:
    return hashlib.sha256(image.convert("RGBA").tobytes()).hexdigest()


def open_image(path: Path, mode: str = "RGBA") -> Image.Image:
    with Image.open(path) as image:
        return image.convert(mode)


def load_manifest(asset_dir: Path) -> dict[str, Any]:
    return load_json(asset_dir / "manifest.json")


def tile_ids(tile: dict[str, Any]) -> list[str]:
    value = tile.get("id", [])
    return [value] if isinstance(value, str) else list(value)


def without_overlay(config: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(config)
    result["tiles-new"] = [
        sheet
        for sheet in result.get("tiles-new", [])
        if sheet.get("file") != ATLAS_NAME
    ]
    return result


def find_tile(config: dict[str, Any], tile_id: str) -> dict[str, Any]:
    matches = [
        tile
        for sheet in config.get("tiles-new", [])
        if sheet.get("file") != ATLAS_NAME
        for tile in sheet.get("tiles", [])
        if tile_id in tile_ids(tile)
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected one definition for {tile_id}, found {len(matches)}")
    return matches[0]


def find_additional(tile: dict[str, Any], additional_id: str) -> dict[str, Any]:
    matches = [
        entry
        for entry in tile.get("additional_tiles", [])
        if entry.get("id") == additional_id
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected one {additional_id} entry for {tile.get('id')}, "
            f"found {len(matches)}"
        )
    return matches[0]


def layer_indices(layer: Any) -> list[int]:
    if layer is None or layer == "":
        return []
    if isinstance(layer, int):
        return [layer]
    if isinstance(layer, list):
        result: list[int] = []
        for entry in layer:
            result.extend(layer_indices(entry))
        return result
    if isinstance(layer, dict) and "sprite" in layer:
        return layer_indices(layer["sprite"])
    raise TypeError(f"Unsupported sprite layer: {layer!r}")


def replace_layer_indices(layer: Any, replacements: Iterable[int]) -> Any:
    values = iter(replacements)

    def replace(value: Any) -> Any:
        if isinstance(value, int):
            try:
                return next(values)
            except StopIteration as error:
                raise ValueError("Too few replacement sprite indexes") from error
        if isinstance(value, list):
            return [replace(entry) for entry in value]
        if isinstance(value, dict) and "sprite" in value:
            result = copy.deepcopy(value)
            result["sprite"] = replace(result["sprite"])
            return result
        raise TypeError(f"Unsupported sprite layer: {value!r}")

    result = replace(layer)
    try:
        next(values)
    except StopIteration:
        return result
    raise ValueError("Too many replacement sprite indexes")


def sheet_geometry(
    config: dict[str, Any], tileset_dir: Path
) -> list[tuple[int, int, dict[str, Any], Image.Image]]:
    info = config["tile_info"][0]
    default_width = int(info["width"])
    default_height = int(info["height"])
    offset = 0
    result: list[tuple[int, int, dict[str, Any], Image.Image]] = []
    for sheet in config.get("tiles-new", []):
        if sheet.get("file") == ATLAS_NAME:
            continue
        image_path = tileset_dir / sheet["file"]
        if not image_path.is_file():
            raise FileNotFoundError(f"Missing tilesheet: {image_path}")
        image = open_image(image_path)
        width = int(sheet.get("sprite_width", default_width))
        height = int(sheet.get("sprite_height", default_height))
        if image.width % width or image.height % height:
            raise ValueError(f"Invalid sheet geometry for {image_path}")
        count = (image.width // width) * (image.height // height)
        result.append((offset, offset + count, sheet, image))
        offset += count
    return result


def atlas_offset(config: dict[str, Any], tileset_dir: Path) -> int:
    geometry = sheet_geometry(config, tileset_dir)
    return geometry[-1][1] if geometry else 0


def crop_sprite(
    config: dict[str, Any], tileset_dir: Path, sprite_index: int
) -> Image.Image:
    info = config["tile_info"][0]
    for start, end, sheet, image in sheet_geometry(config, tileset_dir):
        if not start <= sprite_index < end:
            continue
        width = int(sheet.get("sprite_width", info["width"]))
        height = int(sheet.get("sprite_height", info["height"]))
        columns = image.width // width
        local = sprite_index - start
        x = (local % columns) * width
        y = (local // columns) * height
        return image.crop((x, y, x + width, y + height))
    raise ValueError(f"Sprite index {sprite_index} is outside the main tilesheets")


def enhanced_specs(manifest: dict[str, Any], tile_id: str) -> list[dict[str, Any]]:
    return sorted(
        [entry for entry in manifest["enhanced"] if entry["tile_id"] == tile_id],
        key=lambda entry: entry["slot"],
    )


def source_index_map(
    config: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, int]:
    grass_id = manifest["tile_ids"]["grass"]
    pavement_id = manifest["tile_ids"]["pavement"]
    marker_id = manifest["tile_ids"]["marker"]
    grass = find_tile(config, grass_id)
    pavement = find_tile(config, pavement_id)
    marker = find_tile(config, marker_id)

    grass_indices = layer_indices(grass.get("fg"))
    pavement_indices = layer_indices(find_additional(pavement, "center").get("fg"))
    marker_indices = layer_indices(marker.get("fg"))
    groups = [
        (enhanced_specs(manifest, grass_id), grass_indices),
        (enhanced_specs(manifest, pavement_id), pavement_indices),
        (enhanced_specs(manifest, marker_id), marker_indices),
    ]
    result: dict[str, int] = {}
    for specs, indices in groups:
        if len(specs) != len(indices):
            raise ValueError(
                "Manifest/source variant count mismatch: "
                f"{len(specs)} != {len(indices)}"
            )
        result.update({spec["name"]: index for spec, index in zip(specs, indices)})
    return result


def support_indices(config: dict[str, Any], manifest: dict[str, Any]) -> list[int]:
    pavement = find_tile(config, manifest["tile_ids"]["pavement"])
    result: list[int] = []
    for role in manifest["support"]["additional_tile_order"]:
        result.extend(layer_indices(find_additional(pavement, role).get("fg")))
    expected = int(manifest["support"]["count"])
    if len(result) != expected:
        raise ValueError(f"Expected {expected} support sprites, found {len(result)}")
    return result


def validate_reviewed_assets(
    manifest: dict[str, Any], asset_dir: Path
) -> list[dict[str, Any]]:
    specs = sorted(manifest["enhanced"], key=lambda entry: entry["slot"])
    expected_slots = list(range(len(specs)))
    actual_slots = [int(entry["slot"]) for entry in specs]
    if actual_slots != expected_slots:
        raise ValueError(f"Enhanced slots must be contiguous: {actual_slots}")
    for spec in specs:
        path = asset_dir / spec["reviewed_file"]
        if not path.is_file():
            raise FileNotFoundError(f"Missing reviewed sprite: {path}")
        image = open_image(path)
        if image.size != tuple(manifest["reviewed_sprite_size"]):
            raise ValueError(f"Unexpected dimensions for {path}: {image.size}")
        digest = file_sha256(path)
        if digest != spec["reviewed_sha256"]:
            raise ValueError(f"Reviewed sprite hash mismatch for {path}")
    return specs


def validate_source_assets(
    config: dict[str, Any],
    tileset_dir: Path,
    manifest: dict[str, Any],
) -> dict[str, int]:
    indexes = source_index_map(config, manifest)
    for spec in manifest["enhanced"]:
        image = crop_sprite(config, tileset_dir, indexes[spec["name"]])
        if image.size != tuple(manifest["source_sprite_size"]):
            raise ValueError(f"Unexpected source size for {spec['name']}: {image.size}")
        if pixel_sha256(image) != spec["source_pixel_sha256"]:
            raise ValueError(
                f"Source pixels changed for {spec['name']}; regenerate and review it"
            )
    return indexes


def build_atlas(
    config: dict[str, Any],
    tileset_dir: Path,
    manifest: dict[str, Any],
    asset_dir: Path,
) -> Image.Image:
    specs = validate_reviewed_assets(manifest, asset_dir)
    validate_source_assets(config, tileset_dir, manifest)
    support = support_indices(config, manifest)
    atlas = manifest["atlas"]
    sprite_width, sprite_height = manifest["reviewed_sprite_size"]
    columns = int(atlas["columns"])
    sprite_count = int(atlas["sprite_count"])
    rows = math.ceil(sprite_count / columns)
    output = Image.new(
        "RGBA", (columns * sprite_width, rows * sprite_height), (0, 0, 0, 0)
    )
    for spec in specs:
        image = open_image(asset_dir / spec["reviewed_file"])
        slot = int(spec["slot"])
        output.alpha_composite(
            image,
            ((slot % columns) * sprite_width, (slot // columns) * sprite_height),
        )
    first_support_slot = len(specs)
    for position, source_index in enumerate(support, start=first_support_slot):
        image = crop_sprite(config, tileset_dir, source_index).resize(
            (sprite_width, sprite_height), Image.Resampling.NEAREST
        )
        output.alpha_composite(
            image,
            (
                (position % columns) * sprite_width,
                (position // columns) * sprite_height,
            ),
        )
    if first_support_slot + len(support) != sprite_count:
        raise ValueError(
            "Manifest atlas count does not match enhanced plus support sprites"
        )
    return output


def make_overlay_part(
    config: dict[str, Any], manifest: dict[str, Any], offset: int
) -> dict[str, Any]:
    grass_id = manifest["tile_ids"]["grass"]
    pavement_id = manifest["tile_ids"]["pavement"]
    marker_id = manifest["tile_ids"]["marker"]
    grass_specs = enhanced_specs(manifest, grass_id)
    pavement_specs = enhanced_specs(manifest, pavement_id)
    marker_specs = enhanced_specs(manifest, marker_id)
    hi = lambda slot: offset + int(slot)

    grass = copy.deepcopy(find_tile(config, grass_id))
    grass["fg"] = replace_layer_indices(
        grass["fg"], [hi(spec["slot"]) for spec in grass_specs]
    )

    pavement = copy.deepcopy(find_tile(config, pavement_id))
    pavement["fg"] = replace_layer_indices(
        pavement["fg"], [hi(pavement_specs[0]["slot"])]
    )
    center = find_additional(pavement, "center")
    center["fg"] = replace_layer_indices(
        center["fg"], [hi(spec["slot"]) for spec in pavement_specs]
    )
    corner = find_additional(pavement, "corner")
    corner["bg"] = hi(grass_specs[0]["slot"])
    support_slot = len(manifest["enhanced"])
    for role in manifest["support"]["additional_tile_order"]:
        additional = find_additional(pavement, role)
        count = len(layer_indices(additional["fg"]))
        replacements = list(range(offset + support_slot, offset + support_slot + count))
        additional["fg"] = replace_layer_indices(additional["fg"], replacements)
        support_slot += count

    marker = copy.deepcopy(find_tile(config, marker_id))
    marker["fg"] = replace_layer_indices(
        marker["fg"], [hi(marker_specs[0]["slot"])]
    )
    atlas = manifest["atlas"]
    return {
        "file": atlas["file"],
        "//": f"range {offset} to {offset + int(atlas['sprite_count']) - 1}",
        "sprite_width": manifest["reviewed_sprite_size"][0],
        "sprite_height": manifest["reviewed_sprite_size"][1],
        "pixelscale": manifest["pixelscale"],
        "tiles": [grass, pavement, marker],
    }


def patched_config(
    config: dict[str, Any], tileset_dir: Path, manifest: dict[str, Any]
) -> dict[str, Any]:
    result = without_overlay(config)
    offset = atlas_offset(result, tileset_dir)
    # The compatibility sheets contain absolute sprite references.  Appending
    # this optional overlay keeps every pre-existing atlas offset unchanged.
    result["tiles-new"].append(make_overlay_part(result, manifest, offset))
    return result


def update_backport_manifest(
    tileset_dir: Path, manifest: dict[str, Any]
) -> None:
    path = tileset_dir / "BACKPORT_MANIFEST.json"
    backport = load_json(path)
    backport["hires_overlay"] = {
        "atlas": manifest["atlas"]["file"],
        "enhanced_sprites": len(manifest["enhanced"]),
        "support_sprites": manifest["support"]["count"],
        "source_sprite_size": manifest["source_sprite_size"],
        "reviewed_sprite_size": manifest["reviewed_sprite_size"],
        "pixelscale": manifest["pixelscale"],
        "manifest": "tools/gfx_tools/ultica_hires/manifest.json",
        "tested_game_build": manifest["tested_game_build"],
    }
    atomic_write_json(path, backport)


def build(tileset_dir: Path, asset_dir: Path) -> dict[str, Any]:
    manifest = load_manifest(asset_dir)
    config_path = tileset_dir / "tile_config.json"
    current = load_json(config_path)
    base = without_overlay(current)
    atlas = build_atlas(base, tileset_dir, manifest, asset_dir)
    atomic_save_png(atlas, tileset_dir / manifest["atlas"]["file"])
    atomic_write_json(config_path, patched_config(base, tileset_dir, manifest))
    update_backport_manifest(tileset_dir, manifest)
    return validate(tileset_dir, asset_dir)


def all_tile_sprite_indices(tile: dict[str, Any]) -> list[int]:
    result = layer_indices(tile.get("fg")) + layer_indices(tile.get("bg"))
    for additional in tile.get("additional_tiles", []):
        result.extend(layer_indices(additional.get("fg")))
        result.extend(layer_indices(additional.get("bg")))
    return result


def images_equal(first: Image.Image, second: Image.Image) -> bool:
    if first.size != second.size:
        return False
    return ImageChops.difference(
        first.convert("RGBA"), second.convert("RGBA")
    ).getbbox() is None


def validate(tileset_dir: Path, asset_dir: Path) -> dict[str, Any]:
    manifest = load_manifest(asset_dir)
    config = load_json(tileset_dir / "tile_config.json")
    base = without_overlay(config)
    validate_reviewed_assets(manifest, asset_dir)
    validate_source_assets(base, tileset_dir, manifest)
    parts = [
        sheet
        for sheet in config.get("tiles-new", [])
        if sheet.get("file") == manifest["atlas"]["file"]
    ]
    if len(parts) != 1:
        raise ValueError(f"Expected one HiRes sheet, found {len(parts)}")
    offset = atlas_offset(base, tileset_dir)
    expected_part = make_overlay_part(base, manifest, offset)
    if parts[0] != expected_part:
        raise ValueError("HiRes tile configuration differs from generated output")
    if config != patched_config(config, tileset_dir, manifest):
        raise ValueError("HiRes tile configuration is not idempotent")

    atlas_path = tileset_dir / manifest["atlas"]["file"]
    atlas = open_image(atlas_path)
    sprite_width, sprite_height = manifest["reviewed_sprite_size"]
    columns = int(manifest["atlas"]["columns"])
    expected_size = (
        columns * sprite_width,
        math.ceil(int(manifest["atlas"]["sprite_count"]) / columns)
        * sprite_height,
    )
    if atlas.size != expected_size:
        raise ValueError(f"Unexpected HiRes atlas size: {atlas.size}")
    specs = sorted(manifest["enhanced"], key=lambda entry: entry["slot"])
    for spec in specs:
        slot = int(spec["slot"])
        actual = atlas.crop(
            (
                (slot % columns) * sprite_width,
                (slot // columns) * sprite_height,
                (slot % columns + 1) * sprite_width,
                (slot // columns + 1) * sprite_height,
            )
        )
        expected = open_image(asset_dir / spec["reviewed_file"])
        if not images_equal(actual, expected):
            raise ValueError(f"Atlas slot {slot} differs from {spec['reviewed_file']}")
    for slot, source_index in enumerate(
        support_indices(base, manifest), start=len(specs)
    ):
        actual = atlas.crop(
            (
                (slot % columns) * sprite_width,
                (slot // columns) * sprite_height,
                (slot % columns + 1) * sprite_width,
                (slot // columns + 1) * sprite_height,
            )
        )
        expected = crop_sprite(base, tileset_dir, source_index).resize(
            (sprite_width, sprite_height), Image.Resampling.NEAREST
        )
        if not images_equal(actual, expected):
            raise ValueError(f"Support atlas slot {slot} is not an exact 2x copy")

    sprite_indexes = [
        index for tile in parts[0]["tiles"] for index in all_tile_sprite_indices(tile)
    ]
    lower = offset
    upper = offset + int(manifest["atlas"]["sprite_count"])
    if not sprite_indexes or not all(
        lower <= index < upper for index in sprite_indexes
    ):
        raise ValueError("HiRes tile definitions reference sprites outside their atlas")

    backport = load_json(tileset_dir / "BACKPORT_MANIFEST.json")
    overlay = backport.get("hires_overlay", {})
    if overlay.get("atlas") != manifest["atlas"]["file"]:
        raise ValueError("BACKPORT_MANIFEST does not identify the HiRes atlas")
    return {
        "status": "pass",
        "atlas": manifest["atlas"]["file"],
        "atlas_sha256": file_sha256(atlas_path),
        "atlas_offset": offset,
        "enhanced_sprites": len(specs),
        "support_sprites": len(support_indices(base, manifest)),
        "logical_tile_size": [
            config["tile_info"][0]["width"],
            config["tile_info"][0]["height"],
        ],
        "pixelscale": parts[0]["pixelscale"],
    }


def extract_sources(
    tileset_dir: Path, asset_dir: Path, output_dir: Path
) -> dict[str, Any]:
    manifest = load_manifest(asset_dir)
    config = without_overlay(load_json(tileset_dir / "tile_config.json"))
    indexes = source_index_map(config, manifest)
    source32 = output_dir / "source32"
    source1024 = output_dir / "source1024"
    source32.mkdir(parents=True, exist_ok=True)
    source1024.mkdir(parents=True, exist_ok=True)
    records = []
    for spec in sorted(manifest["enhanced"], key=lambda entry: entry["slot"]):
        image = crop_sprite(config, tileset_dir, indexes[spec["name"]]).convert("RGBA")
        atomic_save_png(image, source32 / f"{spec['name']}.png")
        atomic_save_png(
            image.resize((1024, 1024), Image.Resampling.NEAREST),
            source1024 / f"{spec['name']}.png",
        )
        records.append(
            {
                "name": spec["name"],
                "source_index": indexes[spec["name"]],
                "source_pixel_sha256": pixel_sha256(image),
            }
        )
    atomic_write_json(output_dir / "source_manifest.json", {"sprites": records})
    return {"status": "pass", "sprites": len(records), "output": str(output_dir)}


def center_square(image: Image.Image) -> Image.Image:
    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    return image.crop((left, top, left + side, top + side))


def match_statistics(image: Image.Image, reference: Image.Image) -> Image.Image:
    source = image.convert("RGB")
    target = reference.convert("RGB")
    source_stats = ImageStat.Stat(source)
    target_stats = ImageStat.Stat(target)
    adjusted = []
    for channel, source_mean, source_std, target_mean, target_std in zip(
        source.split(),
        source_stats.mean,
        source_stats.stddev,
        target_stats.mean,
        target_stats.stddev,
    ):
        desired_std = max(1.0, target_std * 0.9)
        gain = min(4.0, desired_std / max(0.5, source_std))
        adjusted.append(
            channel.point(
                lambda value, mean=source_mean, wanted=target_mean, scale=gain: max(
                    0, min(255, round((value - mean) * scale + wanted))
                )
            )
        )
    return Image.merge("RGB", adjusted)


def enforce_periodic_edges(image: Image.Image) -> Image.Image:
    source = np.asarray(image.convert("RGB"), dtype=np.float64)
    height, width, channels = source.shape
    boundary = np.zeros_like(source)
    horizontal_jump = source[-1, :, :] - source[0, :, :]
    boundary[0, :, :] = horizontal_jump
    boundary[-1, :, :] = -horizontal_jump
    vertical_jump = source[:, -1, :] - source[:, 0, :]
    boundary[:, 0, :] += vertical_jump
    boundary[:, -1, :] -= vertical_jump
    yy = np.arange(height, dtype=np.float64)[:, None]
    xx = np.arange(width, dtype=np.float64)[None, :]
    denominator = (
        2.0 * np.cos(2.0 * np.pi * xx / width)
        + 2.0 * np.cos(2.0 * np.pi * yy / height)
        - 4.0
    )
    denominator[0, 0] = 1.0
    smooth = np.empty_like(source)
    for channel in range(channels):
        spectrum = np.fft.fft2(boundary[:, :, channel]) / denominator
        spectrum[0, 0] = 0.0
        smooth[:, :, channel] = np.fft.ifft2(spectrum).real
    return Image.fromarray(np.rint(np.clip(source - smooth, 0, 255)).astype(np.uint8))


def marker_mask(source: Image.Image) -> Image.Image:
    rgb = source.convert("RGB")
    data = np.asarray(rgb, dtype=np.int16)
    selected = (
        (data[:, :, 0] > 100)
        & (data[:, :, 1] > 100)
        & (data[:, :, 0] - data[:, :, 2] > 20)
        & (data[:, :, 1] - data[:, :, 2] > 20)
    )
    mask = Image.fromarray((selected * 255).astype(np.uint8))
    return mask.resize((64, 64), Image.Resampling.NEAREST)


def best_periodic_crop(image: Image.Image, output_size: int = 64) -> Image.Image:
    search = center_square(image.convert("RGB")).resize(
        (256, 256), Image.Resampling.LANCZOS
    )
    data = np.asarray(search, dtype=np.int16)
    margin = 12
    strip = 10
    best_score = math.inf
    best_xy = (margin, margin)
    for y in range(margin, 256 - output_size - margin + 1, 2):
        for x in range(margin, 256 - output_size - margin + 1, 2):
            window = data[y : y + output_size, x : x + output_size]
            edge_error = np.abs(window[:, :strip] - window[:, -strip:]).mean()
            edge_error += np.abs(window[:strip, :] - window[-strip:, :]).mean()
            score = float(edge_error - window.std(axis=(0, 1)).mean() * 0.08)
            if score < best_score:
                best_score = score
                best_xy = (x, y)
    x, y = best_xy
    return search.crop((x, y, x + output_size, y + output_size))


def combine_source_detail(
    generated: Image.Image, source: Image.Image, strength: float
) -> Image.Image:
    generated_rgb = generated.convert("RGB")
    low_frequency = generated_rgb.filter(ImageFilter.GaussianBlur(radius=4.0))
    generated_data = np.asarray(generated_rgb, dtype=np.float32)
    low_data = np.asarray(low_frequency, dtype=np.float32)
    base = source.convert("RGB").resize((64, 64), Image.Resampling.BICUBIC)
    base_data = np.asarray(base, dtype=np.float32)
    return Image.fromarray(
        np.clip(base_data + (generated_data - low_data) * strength, 0, 255).astype(
            np.uint8
        )
    )


def finalize_generated(
    asset_dir: Path, source_dir: Path, raw_dir: Path, output_dir: Path
) -> dict[str, Any]:
    manifest = load_manifest(asset_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    finals: dict[str, Image.Image] = {}
    for spec in sorted(manifest["enhanced"], key=lambda entry: entry["slot"]):
        name = spec["name"]
        raw_path = raw_dir / f"{name}.png"
        source_path = source_dir / f"{name}.png"
        if not raw_path.is_file() or not source_path.is_file():
            raise FileNotFoundError(f"Missing raw/source pair for {name}")
        source = open_image(source_path)
        reduced = best_periodic_crop(open_image(raw_path))
        strength = 1.35 if spec["family"] == "grass" else 1.15
        reduced = combine_source_detail(reduced, source, strength)
        reduced = match_statistics(
            reduced,
            source.resize((64, 64), Image.Resampling.NEAREST).convert("RGB"),
        )
        reduced = enforce_periodic_edges(reduced)
        finals[name] = reduced

    marker_name = enhanced_specs(manifest, manifest["tile_ids"]["marker"])[0]["name"]
    pavement_name = enhanced_specs(
        manifest, manifest["tile_ids"]["pavement"]
    )[0]["name"]
    marker_source = open_image(source_dir / f"{marker_name}.png")
    marker_source_64 = marker_source.resize(
        (64, 64), Image.Resampling.NEAREST
    ).convert("RGB")
    finals[marker_name] = Image.composite(
        marker_source_64, finals[pavement_name].copy(), marker_mask(marker_source)
    )
    for name, image in finals.items():
        atomic_save_png(image, output_dir / f"{name}.png")
    return {
        "status": "pass",
        "sprites": len(finals),
        "output": str(output_dir),
        "note": "Review outputs manually before replacing canonical reviewed assets.",
    }


def review_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in (
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ):
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def source_images(
    tileset_dir: Path, asset_dir: Path
) -> tuple[dict[str, Any], dict[str, Image.Image]]:
    manifest = load_manifest(asset_dir)
    config = without_overlay(load_json(tileset_dir / "tile_config.json"))
    indexes = source_index_map(config, manifest)
    return manifest, {
        name: crop_sprite(config, tileset_dir, index).convert("RGBA")
        for name, index in indexes.items()
    }


def make_review_images(
    tileset_dir: Path, asset_dir: Path, output_dir: Path
) -> dict[str, Any]:
    manifest, sources = source_images(tileset_dir, asset_dir)
    specs = sorted(manifest["enhanced"], key=lambda entry: entry["slot"])
    finals = {
        spec["name"]: open_image(asset_dir / spec["reviewed_file"], "RGB")
        for spec in specs
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    comparison = Image.new("RGB", (1560, 1120), (19, 21, 24))
    draw = ImageDraw.Draw(comparison)
    draw.text(
        (30, 18),
        "Ultica HiRes pilot - original 32x32 vs reviewed 64x64",
        fill="white",
        font=review_font(34),
    )
    for position, spec in enumerate(specs):
        row, column = divmod(position, 3)
        x = 30 + column * 510
        y = 78 + row * 340
        draw.rounded_rectangle(
            (x, y, x + 480, y + 312),
            12,
            fill=(31, 34, 39),
            outline=(70, 75, 84),
            width=2,
        )
        draw.text(
            (x + 18, y + 12),
            spec["name"],
            fill=(235, 238, 242),
            font=review_font(20),
        )
        original = sources[spec["name"]].convert("RGB").resize(
            (192, 192), Image.Resampling.NEAREST
        )
        enhanced = finals[spec["name"]].resize((192, 192), Image.Resampling.NEAREST)
        comparison.paste(original, (x + 18, y + 58))
        comparison.paste(enhanced, (x + 264, y + 58))
        draw.text(
            (x + 18, y + 264),
            "Original 32",
            fill=(190, 194, 201),
            font=review_font(17),
        )
        draw.text(
            (x + 264, y + 264),
            "Pilot 64",
            fill=(190, 194, 201),
            font=review_font(17),
        )
    atomic_save_png(comparison, output_dir / "comparison.png")

    random.seed(20260824)
    scene = Image.new("RGB", (1600, 590), (18, 20, 23))
    scene_draw = ImageDraw.Draw(scene)
    scene_draw.text(
        (20, 12),
        "Original 32x32 enlarged to 64",
        fill="white",
        font=review_font(24),
    )
    scene_draw.text(
        (812, 12),
        "Reviewed 64x64 pilot",
        fill="white",
        font=review_font(24),
    )
    grass = [spec["name"] for spec in specs if spec["family"] == "grass"]
    pavement = [spec["name"] for spec in specs if spec["family"] == "pavement"]
    marker = [spec["name"] for spec in specs if spec["family"] == "marker"][0]
    choices: list[list[str]] = []
    for y in range(8):
        row = []
        for x in range(12):
            if y < 3:
                row.append(random.choice(grass))
            elif y == 6 and x % 3 != 0:
                row.append(marker)
            else:
                row.append(random.choice(pavement))
        choices.append(row)
    for mode, origin_x in (("original", 20), ("pilot", 812)):
        for y, row in enumerate(choices):
            for x, name in enumerate(row):
                image = sources[name].convert("RGB").resize(
                    (64, 64), Image.Resampling.NEAREST
                ) if mode == "original" else finals[name]
                scene.paste(image, (origin_x + x * 64, 56 + y * 64))
    atomic_save_png(scene, output_dir / "scene-comparison.png")
    return {"status": "pass", "images": 2, "output": str(output_dir)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tileset-dir", type=Path, default=DEFAULT_TILESET_DIR)
    parser.add_argument("--asset-dir", type=Path, default=DEFAULT_ASSET_DIR)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("build")
    subparsers.add_parser("validate")
    extract_parser = subparsers.add_parser("extract")
    extract_parser.add_argument("--output-dir", type=Path, required=True)
    finalize_parser = subparsers.add_parser("finalize")
    finalize_parser.add_argument("--source-dir", type=Path, required=True)
    finalize_parser.add_argument("--raw-dir", type=Path, required=True)
    finalize_parser.add_argument("--output-dir", type=Path, required=True)
    review_parser = subparsers.add_parser("review")
    review_parser.add_argument("--output-dir", type=Path, default=DEFAULT_REVIEW_DIR)
    args = parser.parse_args()

    if args.command == "build":
        result = build(args.tileset_dir, args.asset_dir)
    elif args.command == "validate":
        result = validate(args.tileset_dir, args.asset_dir)
    elif args.command == "extract":
        result = extract_sources(args.tileset_dir, args.asset_dir, args.output_dir)
    elif args.command == "finalize":
        result = finalize_generated(
            args.asset_dir, args.source_dir, args.raw_dir, args.output_dir
        )
    else:
        result = make_review_images(args.tileset_dir, args.asset_dir, args.output_dir)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
