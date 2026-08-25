#!/usr/bin/env python3
"""Focused source-data checks for the selected H6 anti-grind backports."""

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_json(relative_path):
    with (ROOT / relative_path).open(encoding="utf-8") as source:
        return json.load(source)


class SafeStartDataTest(unittest.TestCase):
    def test_cabin_variant_has_corpse_instead_of_zombie(self):
        cabin = next(
            entry for entry in load_json("data/json/mapgen/cabin.json")
            if entry.get("om_terrain") == ["cabin"] and entry.get("weight") == 500
        )
        obj = cabin["object"]
        self.assertNotIn("place_monsters", obj)
        self.assertEqual(
            obj["place_item"],
            [{"item": "corpse_generic_human", "x": 7, "y": 4, "chance": 100}],
        )

    def test_farm_variant_has_corpse_instead_of_zombies(self):
        farm = next(
            entry for entry in load_json("data/json/mapgen/farm.json")
            if entry.get("om_terrain") == [["farm_2"]]
            and entry.get("weight") == 500
            and "//" not in entry
        )
        obj = farm["object"]
        self.assertNotIn("place_monster", obj)
        self.assertEqual(
            obj["place_item"],
            [{
                "item": "corpse_generic_human",
                "x": [2, 22],
                "y": [2, 22],
                "chance": 100,
            }],
        )

    def test_isolationist_excludes_exposed_station(self):
        scenario = next(
            entry for entry in load_json("data/json/scenarios.json")
            if entry.get("type") == "scenario" and entry.get("id") == "isolationist"
        )
        self.assertNotIn("sloc_freshwater_research_station", scenario["allowed_locs"])
        self.assertIn("sloc_cabin_lake", scenario["allowed_locs"])


if __name__ == "__main__":
    unittest.main()
