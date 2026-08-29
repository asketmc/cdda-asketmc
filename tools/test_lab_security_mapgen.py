#!/usr/bin/env python3
"""Regression contract for lab-security floor-marking update mapgens."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DRONES = ROOT / "data/json/monsters/lab_security_drones.json"
CORRIDOR_UPDATES = {
    "lab_security_corridor_c": {(19, 8), (19, 10), (4, 8), (4, 10)},
    "lab_security_corridor_d": {(19, 17), (19, 19), (4, 17), (4, 19)},
    "lab_security_corridor_e": {(17, 4), (17, 6), (6, 4), (6, 6)},
    "lab_security_corridor_f": {(17, 13), (17, 15), (6, 13), (6, 15)},
}


class LabSecurityMapgenTest(unittest.TestCase):
    def test_corridor_floor_markers_preserve_existing_map_data(self) -> None:
        entries = json.loads(DRONES.read_text(encoding="utf-8"))
        updates = [
            entry
            for entry in entries
            if entry.get( "type" ) == "mapgen"
            and entry.get( "update_mapgen_id" ) in CORRIDOR_UPDATES
        ]

        self.assertEqual(len(updates), len(CORRIDOR_UPDATES))
        self.assertEqual(
            {entry["update_mapgen_id"] for entry in updates}, set(CORRIDOR_UPDATES)
        )
        for entry in updates:
            update_id = entry["update_mapgen_id"]
            update = entry["object"]
            with self.subTest( update_id=update_id ):
                self.assertEqual(
                    update.get("flags"), ["ALLOW_TERRAIN_UNDER_OTHER_DATA"]
                )
                terrain = update.get("place_terrain", [])
                self.assertEqual(len(terrain), 4)
                self.assertTrue(
                    all(
                        placement["ter"] == "t_thconc_r"
                        for placement in terrain
                    )
                )
                self.assertEqual(
                    {(placement["x"], placement["y"]) for placement in terrain},
                    CORRIDOR_UPDATES[update_id],
                )


if __name__ == "__main__":
    unittest.main()
