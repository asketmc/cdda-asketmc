#!/usr/bin/env python3
"""Regression contract for lab-security floor-marking update mapgens."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DRONES = ROOT / "data/json/monsters/lab_security_drones.json"
CORRIDOR_UPDATES = {
    "lab_security_corridor_c",
    "lab_security_corridor_d",
    "lab_security_corridor_e",
    "lab_security_corridor_f",
}


class LabSecurityMapgenTest(unittest.TestCase):
    def test_corridor_floor_markers_preserve_existing_map_data(self) -> None:
        entries = json.loads(DRONES.read_text(encoding="utf-8"))
        updates = {
            entry[ "update_mapgen_id" ]: entry[ "object" ]
            for entry in entries
            if entry.get( "type" ) == "mapgen"
            and entry.get( "update_mapgen_id" ) in CORRIDOR_UPDATES
        }

        self.assertEqual( set( updates ), CORRIDOR_UPDATES )
        for update_id, update in updates.items():
            with self.subTest( update_id=update_id ):
                self.assertEqual(
                    update.get("flags"), ["ALLOW_TERRAIN_UNDER_OTHER_DATA"]
                )
                self.assertEqual(len(update.get("place_terrain", [])), 4)
                self.assertTrue(
                    all(
                        placement["ter"] == "t_thconc_r"
                        for placement in update["place_terrain"]
                    )
                )


if __name__ == "__main__":
    unittest.main()
