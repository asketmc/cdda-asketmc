#!/usr/bin/env python3

import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_ultica_hires import (
    ATLAS_NAME,
    DEFAULT_ASSET_DIR,
    DEFAULT_REVIEW_DIR,
    DEFAULT_TILESET_DIR,
    extract_sources,
    finalize_generated,
    load_json,
    make_review_images,
    patched_config,
    pixel_sha256,
    validate,
    without_overlay,
)


class UlticaHiResTest(unittest.TestCase):
    def test_runtime_overlay_passes_full_validation(self) -> None:
        report = validate(DEFAULT_TILESET_DIR, DEFAULT_ASSET_DIR)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["enhanced_sprites"], 9)
        self.assertEqual(report["support_sprites"], 15)
        self.assertEqual(report["logical_tile_size"], [32, 32])
        self.assertEqual(report["pixelscale"], 0.5)

    def test_configuration_rebuild_is_idempotent(self) -> None:
        current = load_json(DEFAULT_TILESET_DIR / "tile_config.json")
        manifest = load_json(DEFAULT_ASSET_DIR / "manifest.json")
        self.assertEqual(
            patched_config(current, DEFAULT_TILESET_DIR, manifest), current
        )
        self.assertEqual(
            sum(
                sheet.get("file") == ATLAS_NAME
                for sheet in current.get("tiles-new", [])
            ),
            1,
        )
        self.assertNotEqual(without_overlay(current), current)

    def test_reviewed_assets_match_manifest(self) -> None:
        manifest = load_json(DEFAULT_ASSET_DIR / "manifest.json")
        self.assertEqual(len(manifest["enhanced"]), 9)
        self.assertEqual(
            [entry["slot"] for entry in manifest["enhanced"]], list(range(9))
        )
        for entry in manifest["enhanced"]:
            path = DEFAULT_ASSET_DIR / entry["reviewed_file"]
            self.assertTrue(path.is_file(), path)
            with Image.open(path) as image:
                self.assertEqual(image.size, (64, 64))

    def test_review_images_are_committed(self) -> None:
        for name in ("comparison.png", "scene-comparison.png"):
            path = DEFAULT_REVIEW_DIR / name
            self.assertTrue(path.is_file(), path)
            with Image.open(path) as image:
                self.assertGreaterEqual(image.width, 1500)
                self.assertGreaterEqual(image.height, 500)

    def test_backport_manifest_links_reproducibility_manifest(self) -> None:
        backport = json.loads(
            (DEFAULT_TILESET_DIR / "BACKPORT_MANIFEST.json").read_text(
                encoding="utf-8"
            )
        )
        overlay = backport["hires_overlay"]
        self.assertEqual(overlay["atlas"], ATLAS_NAME)
        self.assertEqual(overlay["enhanced_sprites"], 9)
        self.assertEqual(overlay["support_sprites"], 15)
        self.assertEqual(
            overlay["manifest"], "tools/gfx_tools/ultica_hires/manifest.json"
        )

    def test_reproducibility_pipeline_produces_expected_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            extracted = root / "extracted"
            candidates = root / "candidates"
            review = root / "review"

            extract_report = extract_sources(
                DEFAULT_TILESET_DIR, DEFAULT_ASSET_DIR, extracted
            )
            finalize_report = finalize_generated(
                DEFAULT_ASSET_DIR,
                extracted / "source32",
                extracted / "source1024",
                candidates,
            )
            review_report = make_review_images(
                DEFAULT_TILESET_DIR, DEFAULT_ASSET_DIR, review
            )

            self.assertEqual(extract_report["sprites"], 9)
            self.assertEqual(finalize_report["sprites"], 9)
            self.assertEqual(review_report["images"], 2)
            self.assertEqual(len(list(candidates.glob("*.png"))), 9)
            self.assertEqual(len(list(review.glob("*.png"))), 2)
            manifest = load_json(DEFAULT_ASSET_DIR / "manifest.json")
            expected_hashes = manifest["validation_fixture"][
                "candidate_pixel_sha256"
            ]
            actual_hashes = {}
            for path in sorted(candidates.glob("*.png")):
                with Image.open(path) as candidate:
                    actual_hashes[path.stem] = pixel_sha256(candidate)
            self.assertEqual(actual_hashes, expected_hashes)
            for name in ("comparison.png", "scene-comparison.png"):
                with Image.open(review / name) as generated:
                    with Image.open(DEFAULT_REVIEW_DIR / name) as committed:
                        self.assertEqual(generated.size, committed.size)


if __name__ == "__main__":
    unittest.main()
