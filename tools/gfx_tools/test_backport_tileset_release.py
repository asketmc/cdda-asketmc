#!/usr/bin/env python3

import json
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).resolve().parent ) )

from backport_tileset_release import (
    adapt_release_rotations_for_0g,
    build_compatibility_sheets,
    install_release,
)


def config(image: str, tiles: list[dict]) -> dict:
    return {
        "tile_info": [{"width": 32, "height": 32, "zlevel_height": 0}],
        "tiles-new": [{"file": image, "tiles": tiles}],
    }


def png(width: int, height: int) -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(
            ">I", zlib.crc32(kind + payload) & 0xFFFFFFFF
        )

    rows = b"".join(b"\0" + b"\0\0\0\0" * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


class TilesetReleaseBackportTest(unittest.TestCase):
    def test_current_directional_sprites_are_adapted_to_0g_handedness(self) -> None:
        current = config("new.png", [{
            "id": "road",
            "fg": [0, 1, 2, 3],
            "bg": [{"weight": 1, "sprite": [4, 5, 6, 7]}],
            "additional_tiles": [{"id": "corner", "fg": [8, 9, 10, 11]}],
        }])

        self.assertEqual(adapt_release_rotations_for_0g(current), 3)
        tile = current["tiles-new"][0]["tiles"][0]
        self.assertEqual(tile["fg"], [0, 3, 2, 1])
        self.assertEqual(tile["bg"][0]["sprite"], [4, 7, 6, 5])
        self.assertEqual(tile["additional_tiles"][0]["fg"], [8, 11, 10, 9])

    def test_compatibility_layer_keeps_only_removed_ids(self) -> None:
        legacy = config("old.png", [{"id": ["shared", "old_only"], "fg": 0}])
        current = config("new.png", [{"id": "shared", "fg": 0}])

        sheets, images, retained = build_compatibility_sheets(
            legacy, current, "compat_", [1], 1
        )

        self.assertEqual(images, {"old.png"})
        self.assertEqual(retained, {"old_only"})
        self.assertEqual(sheets[0]["file"], "compat_old.png")
        self.assertEqual(sheets[0]["tiles"][0]["id"], ["old_only"])
        self.assertEqual(sheets[0]["tiles"][0]["fg"], 1)

    def test_cross_sheet_sprite_dependencies_are_retained_and_rebased(self) -> None:
        legacy = {
            "tile_info": [{"width": 32, "height": 32}],
            "tiles-new": [
                {"file": "old_a.png", "tiles": [{"id": "old_only", "fg": 1}]},
                {"file": "old_b.png", "tiles": [{"id": "shared", "fg": 1}]},
            ],
        }
        current = config("new.png", [{"id": "shared", "fg": 0}])

        sheets, images, retained = build_compatibility_sheets(
            legacy, current, "compat_", [1, 1], 1
        )

        self.assertEqual(images, {"old_a.png", "old_b.png"})
        self.assertEqual(retained, {"old_only"})
        self.assertEqual([sheet["file"] for sheet in sheets], [
            "compat_old_a.png", "compat_old_b.png"
        ])
        self.assertEqual(sheets[0]["tiles"][0]["fg"], 2)
        self.assertEqual(sheets[1]["tiles"], [])

    def test_nested_sprite_variants_are_rebased(self) -> None:
        legacy = config("old.png", [{
            "id": "old_only",
            "fg": [{"weight": 1, "sprite": [0, 1]}],
            "additional_tiles": [{"id": "open", "bg": 1}],
        }])
        current = config("new.png", [])

        sheets, _, _ = build_compatibility_sheets(
            legacy, current, "compat_", [2], 5
        )

        tile = sheets[0]["tiles"][0]
        self.assertEqual(tile["fg"][0]["sprite"], [5, 6])
        self.assertEqual(tile["additional_tiles"][0]["bg"], 6)

    def test_install_copies_release_and_writes_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "target"
            release = root / "release"
            target.mkdir()
            release.mkdir()
            (target / "old.png").write_bytes(png(32, 32))
            (target / "tile_config.json").write_text(
                json.dumps(config("old.png", [{"id": "old_only", "fg": 0}]))
            )
            (release / "new.png").write_bytes(png(128, 32))
            (release / "tile_config.json").write_text(
                json.dumps(config("new.png", [{
                    "id": "new_only",
                    "fg": [0, 1, 2, 3],
                }]))
            )

            manifest = install_release(release, target, "test-tag", "abc123")
            installed = json.loads((target / "tile_config.json").read_text())

            self.assertEqual((target / "new.png").read_bytes(), png(128, 32))
            self.assertEqual((target / "compat_0g_old.png").read_bytes(), png(32, 32))
            self.assertEqual(installed["tile_info"][0]["zlevel_height"], 0)
            self.assertEqual(installed["tiles-new"][0]["tiles"][0]["fg"], [0, 3, 2, 1])
            self.assertEqual(installed["tiles-new"][1]["tiles"][0]["fg"], 4)
            self.assertEqual(manifest["legacy_ids_retained"], 1)
            self.assertEqual(manifest["legacy_images"], ["compat_0g_old.png"])
            self.assertEqual(manifest["rotation_arrays_adapted"], 1)


if __name__ == "__main__":
    unittest.main()
