#!/usr/bin/env python3
"""Install a composed tileset release without dropping legacy tile IDs.

The upstream tileset project follows current experimental item and overmap IDs.
An older game therefore needs the current release plus a small compatibility
layer containing sprites for IDs that only exist in the older data set.
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import struct
from pathlib import Path
from typing import Any, Callable


def _tile_ids(tile: dict[str, Any]) -> list[str]:
    value = tile.get("id", [])
    if isinstance(value, str):
        return [value]
    return [entry for entry in value if isinstance(entry, str)]


def _all_ids(config: dict[str, Any]) -> set[str]:
    return {
        tile_id
        for sheet in config.get("tiles-new", [])
        for tile in sheet.get("tiles", [])
        for tile_id in _tile_ids(tile)
    }


def _adapt_rotation_value_for_0g(value: Any) -> tuple[Any, int]:
    """Convert current N/W/S/E sprite arrays to the 0.G N/E/S/W contract."""
    if isinstance(value, list):
        if len(value) == 4 and all(isinstance(entry, int) and not isinstance(entry, bool)
                                   for entry in value):
            return [value[0], value[3], value[2], value[1]], 1
        adapted: list[Any] = []
        count = 0
        for entry in value:
            if isinstance(entry, dict) and "sprite" in entry:
                mapped = copy.deepcopy(entry)
                mapped["sprite"], changed = _adapt_rotation_value_for_0g(mapped["sprite"])
                adapted.append(mapped)
                count += changed
            else:
                adapted.append(entry)
        return adapted, count
    return value, 0


def adapt_release_rotations_for_0g(config: dict[str, Any]) -> int:
    """Adapt every directional sprite layer in a current tileset release."""
    count = 0
    for sheet in config.get("tiles-new", []):
        for tile in sheet.get("tiles", []):
            drawables = [tile, *tile.get("additional_tiles", [])]
            for drawable in drawables:
                for layer in ("fg", "bg"):
                    if layer in drawable:
                        drawable[layer], changed = _adapt_rotation_value_for_0g(
                            drawable[layer]
                        )
                        count += changed
    return count


def _png_dimensions(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError(f"Invalid PNG header: {path}")
    return struct.unpack(">II", header[16:24])


def _sheet_sprite_counts(config: dict[str, Any], image_dir: Path) -> list[int]:
    tile_info = config.get("tile_info", [{}])[0]
    default_width = tile_info.get("width")
    default_height = tile_info.get("height")
    counts: list[int] = []
    for sheet in config.get("tiles-new", []):
        sprite_width = sheet.get("sprite_width", default_width)
        sprite_height = sheet.get("sprite_height", default_height)
        if not isinstance(sprite_width, int) or not isinstance(sprite_height, int):
            raise ValueError(f"Missing sprite dimensions for {sheet.get('file', '<unknown>')}")
        image_width, image_height = _png_dimensions(image_dir / sheet["file"])
        if image_width % sprite_width or image_height % sprite_height:
            raise ValueError(f"Sprite sheet dimensions are not evenly divisible: {sheet['file']}")
        counts.append((image_width // sprite_width) * (image_height // sprite_height))
    return counts


def _sprite_value_indices(value: Any) -> list[int]:
    if isinstance(value, bool):
        return []
    if isinstance(value, int):
        return [value]
    if isinstance(value, list):
        return [index for entry in value for index in _sprite_value_indices(entry)]
    if isinstance(value, dict):
        return _sprite_value_indices(value.get("sprite")) if "sprite" in value else []
    return []


def _tile_sprite_indices(value: Any) -> list[int]:
    if isinstance(value, list):
        return [index for entry in value for index in _tile_sprite_indices(entry)]
    if not isinstance(value, dict):
        return []
    result: list[int] = []
    for key, member in value.items():
        if key in {"fg", "bg"}:
            result.extend(_sprite_value_indices(member))
        elif key == "additional_tiles":
            result.extend(_tile_sprite_indices(member))
    return result


def _map_sprite_value(value: Any, mapper: Callable[[int], int]) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return mapper(value)
    if isinstance(value, list):
        return [_map_sprite_value(entry, mapper) for entry in value]
    if isinstance(value, dict):
        mapped = copy.deepcopy(value)
        if "sprite" in mapped:
            mapped["sprite"] = _map_sprite_value(mapped["sprite"], mapper)
        return mapped
    return value


def _map_tile_sprites(value: Any, mapper: Callable[[int], int]) -> None:
    if isinstance(value, list):
        for entry in value:
            _map_tile_sprites(entry, mapper)
        return
    if not isinstance(value, dict):
        return
    for key, member in value.items():
        if key in {"fg", "bg"}:
            value[key] = _map_sprite_value(member, mapper)
        elif key == "additional_tiles":
            _map_tile_sprites(member, mapper)


def build_compatibility_sheets(
    legacy: dict[str, Any],
    current: dict[str, Any],
    prefix: str,
    legacy_sheet_counts: list[int],
    current_sprite_count: int,
) -> tuple[list[dict[str, Any]], set[str], set[str]]:
    """Return rebased legacy sheets, their image names, and retained IDs."""
    legacy_sheets = legacy.get("tiles-new", [])
    if len(legacy_sheet_counts) != len(legacy_sheets):
        raise ValueError("Legacy sprite counts do not match the configured sheets")

    missing = _all_ids(legacy) - _all_ids(current)
    filtered_by_sheet: dict[int, list[dict[str, Any]]] = {}
    retained: set[str] = set()
    for sheet_index, source_sheet in enumerate(legacy_sheets):
        filtered_tiles: list[dict[str, Any]] = []
        for source_tile in source_sheet.get("tiles", []):
            keep = [tile_id for tile_id in _tile_ids(source_tile) if tile_id in missing]
            if not keep:
                continue
            tile = copy.deepcopy(source_tile)
            tile["id"] = keep[0] if isinstance(source_tile.get("id"), str) else keep
            filtered_tiles.append(tile)
            retained.update(keep)
        if filtered_tiles:
            filtered_by_sheet[sheet_index] = filtered_tiles

    legacy_starts: list[int] = []
    legacy_total = 0
    for count in legacy_sheet_counts:
        legacy_starts.append(legacy_total)
        legacy_total += count

    def source_sheet_for(index: int) -> int:
        for sheet_index, (start, count) in enumerate(zip(legacy_starts, legacy_sheet_counts)):
            if start <= index < start + count:
                return sheet_index
        raise ValueError(f"Sprite index {index} is outside the legacy tileset")

    required_sheets = set(filtered_by_sheet)
    for tiles in filtered_by_sheet.values():
        for tile in tiles:
            required_sheets.update(source_sheet_for(index) for index in _tile_sprite_indices(tile))

    new_starts: dict[int, int] = {}
    next_sprite = current_sprite_count
    for sheet_index in sorted(required_sheets):
        new_starts[sheet_index] = next_sprite
        next_sprite += legacy_sheet_counts[sheet_index]

    def map_sprite(index: int) -> int:
        sheet_index = source_sheet_for(index)
        if sheet_index not in new_starts:
            raise ValueError(f"Legacy sprite dependency sheet {sheet_index} was not retained")
        return new_starts[sheet_index] + index - legacy_starts[sheet_index]

    sheets: list[dict[str, Any]] = []
    images: set[str] = set()
    for sheet_index in sorted(required_sheets):
        source_sheet = legacy_sheets[sheet_index]
        filtered_tiles = filtered_by_sheet.get(sheet_index, [])
        for tile in filtered_tiles:
            _map_tile_sprites(tile, map_sprite)
        sheet = copy.deepcopy(source_sheet)
        source_image = sheet["file"]
        sheet["file"] = f"{prefix}{source_image}"
        sheet["tiles"] = filtered_tiles
        sheets.append(sheet)
        images.add(source_image)

    return sheets, images, retained


def install_release(
    release_dir: Path,
    target_dir: Path,
    release_tag: str,
    release_commit: str,
    compat_prefix: str = "compat_0g_",
) -> dict[str, Any]:
    legacy_config = json.loads((target_dir / "tile_config.json").read_text(encoding="utf-8"))
    current_config = json.loads((release_dir / "tile_config.json").read_text(encoding="utf-8"))
    rotation_arrays_adapted = adapt_release_rotations_for_0g(current_config)
    legacy_sheet_counts = _sheet_sprite_counts(legacy_config, target_dir)
    current_sheet_counts = _sheet_sprite_counts(current_config, release_dir)
    sheets, images, retained = build_compatibility_sheets(
        legacy_config,
        current_config,
        compat_prefix,
        legacy_sheet_counts,
        sum(current_sheet_counts),
    )

    legacy_images = {name: (target_dir / name).read_bytes() for name in images}
    for source in release_dir.iterdir():
        if source.is_file() and source.name != "tile_config.json":
            shutil.copy2(source, target_dir / source.name)
    for name, payload in legacy_images.items():
        (target_dir / f"{compat_prefix}{name}").write_bytes(payload)

    current_config.setdefault("tiles-new", []).extend(sheets)
    (target_dir / "tile_config.json").write_text(
        json.dumps(current_config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    manifest = {
        "release_tag": release_tag,
        "release_commit": release_commit,
        "release_source": "https://github.com/I-am-Erk/CDDA-Tilesets",
        "upstream_ids": len(_all_ids(current_config)) - len(retained),
        "legacy_ids_retained": len(retained),
        "legacy_images": sorted(f"{compat_prefix}{name}" for name in images),
        "rotation_arrays_adapted": rotation_arrays_adapted,
    }
    (target_dir / "BACKPORT_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("release_dir", type=Path)
    parser.add_argument("target_dir", type=Path)
    parser.add_argument("--release-tag", required=True)
    parser.add_argument("--release-commit", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            install_release(
                args.release_dir,
                args.target_dir,
                args.release_tag,
                args.release_commit,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
