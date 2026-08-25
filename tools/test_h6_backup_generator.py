#!/usr/bin/env python3
"""Focused data regression checks for the H6 backup-generator backport."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load_json(relative_path: str) -> list[dict[str, Any]]:
    with (ROOT / relative_path).open(encoding="utf-8") as source:
        data = json.load(source)
    if not isinstance(data, list):
        raise AssertionError(f"{relative_path} is not a top-level JSON array")
    return data


def find_by_id(relative_path: str, identity: str, value: str) -> dict[str, Any]:
    matches = [entry for entry in load_json(relative_path) if entry.get(identity) == value]
    if len(matches) != 1:
        raise AssertionError(
            f"expected one {identity}={value!r} in {relative_path}, found {len(matches)}"
        )
    return matches[0]


class BackupGeneratorBackportTest(unittest.TestCase):
    def test_portable_item_and_grid_appliance(self) -> None:
        portable = find_by_id("data/json/items/appliances.json", "id", "active_backup_generator")
        self.assertEqual(portable["weight"], "200 kg")
        self.assertEqual(portable["volume"], "200 L")
        self.assertEqual(portable["pocket_data"][0]["max_contains_volume"], "10 L")
        allowed_fuels = portable["pocket_data"][0]["item_restriction"]
        self.assertEqual(
            allowed_fuels,
            ["diesel", "biodiesel", "lamp_oil", "motor_oil", "jp8"],
        )
        self.assertNotIn("water", allowed_fuels)
        self.assertNotIn("gasoline", allowed_fuels)
        self.assertIn("NO_RELOAD", portable["flags"])

        appliance = find_by_id(
            "data/json/furniture_and_terrain/appliances.json",
            "id",
            "ap_active_backup_generator",
        )
        self.assertEqual(appliance["item"], "active_backup_generator")
        self.assertEqual(appliance["symbol"], "0")
        self.assertEqual(appliance["broken_symbol"], "#")
        self.assertEqual(appliance["epower"], 7300)
        self.assertEqual(appliance["fuel_type"], "diesel")
        self.assertTrue(
            {"ENGINE", "REACTOR", "FLUIDTANK", "APPLIANCE"}.issubset(appliance["flags"])
        )

    def test_placement_and_existing_furniture_conversion(self) -> None:
        group = find_by_id(
            "data/json/construction_group.json", "id", "place_active_backup_generator"
        )
        self.assertEqual(group["name"], "Place backup generator")

        construction = find_by_id(
            "data/json/construction.json", "id", "app_active_backup_generator"
        )
        self.assertEqual(construction["group"], "place_active_backup_generator")
        self.assertEqual(construction["components"], [[["active_backup_generator", 1]]])
        self.assertEqual(construction["post_special"], "done_appliance")

        furniture = find_by_id(
            "data/json/furniture_and_terrain/furniture-industrial.json",
            "id",
            "f_active_backup_generator",
        )
        self.assertEqual(
            furniture["examine_action"],
            {
                "type": "appliance_convert",
                "furn_set": "f_null",
                "item": "active_backup_generator",
            },
        )
        self.assertNotIn("EASY_DECONSTRUCT", furniture["flags"])
        self.assertEqual(
            furniture["deconstruct"]["items"],
            [
                {"item": "scrap", "count": [5, 15]},
                {"item": "sheet_metal", "count": [4, 6]},
                {
                    "item": "jp8",
                    "charges": [1000, 10000],
                    "container-item": "jerrycan_big",
                },
                {"item": "i4_diesel"},
                {"item": "bearing", "charges": [5, 40]},
            ],
        )

    def test_craft_and_uncraft_are_symmetric(self) -> None:
        expected_components = [
            [["generator_7500w", 1]],
            [["i4_diesel", 1]],
            [["frame", 1]],
            [["jerrycan_big", 1]],
        ]
        recipe = find_by_id(
            "data/json/recipes/recipe_appliance.json", "result", "active_backup_generator"
        )
        self.assertEqual(recipe["components"], expected_components)
        self.assertEqual(recipe["using"], [["vehicle_wrench_2", 1]])
        self.assertTrue(recipe["reversible"])

        uncraft = find_by_id(
            "data/json/recipes/recipe_deconstruction.json",
            "result",
            "active_backup_generator",
        )
        self.assertEqual(uncraft["components"], expected_components)
        self.assertEqual(uncraft["qualities"], [{"id": "WRENCH", "level": 2}])


if __name__ == "__main__":
    unittest.main()
