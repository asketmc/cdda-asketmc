#!/usr/bin/env python3
"""Regression contract for lab-security floor-marking update mapgens."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DRONES = ROOT / "data/json/monsters/lab_security_drones.json"
CENTRAL_HALLWAY = ROOT / "data/json/mapgen/lab/lab_modular/lab_central_hallway.json"
CORRIDOR_UPDATES = {
    "lab_security_corridor_c": {(19, 8), (19, 10), (4, 8), (4, 10)},
    "lab_security_corridor_d": {(19, 17), (19, 19), (4, 17), (4, 19)},
    "lab_security_corridor_e": {(17, 4), (17, 6), (6, 4), (6, 6)},
    "lab_security_corridor_f": {(17, 13), (17, 15), (6, 13), (6, 15)},
}
# Each update is fired by the security alarm effects against one level -6 map.
CORRIDOR_OM_TERRAINS = {
    "lab_security_corridor_c": "underground_lab_central_-6W",
    "lab_security_corridor_d": "underground_lab_central_-6E",
    "lab_security_corridor_e": "underground_lab_central_-6W",
    "lab_security_corridor_f": "underground_lab_central_-6E",
}


def load_json(path: Path) -> list:
    return json.loads(path.read_text(encoding="utf-8"))


def corridor_tiles() -> dict:
    """Map each corridor update id to its list of (x, y) placements."""
    return {
        update_id: [(p["x"], p["y"]) for p in update["place_terrain"]]
        for update_id, update in corridor_updates().items()
    }


def corridor_updates() -> dict:
    return {
        entry["update_mapgen_id"]: entry["object"]
        for entry in load_json(DRONES)
        if entry.get("type") == "mapgen"
        and entry.get("update_mapgen_id") in CORRIDOR_UPDATES
    }


def find_mapgen_update_calls(node: object) -> list:
    """Collect every {"mapgen_update": ..., "om_terrain": ...} effect object."""
    found = []
    if isinstance(node, dict):
        if "mapgen_update" in node:
            found.append((node["mapgen_update"], node.get("om_terrain")))
        for value in node.values():
            found.extend(find_mapgen_update_calls(value))
    elif isinstance(node, list):
        for value in node:
            found.extend(find_mapgen_update_calls(value))
    return found


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

    def test_corridor_updates_only_place_terrain_without_overlap(self) -> None:
        updates = corridor_updates()
        self.assertEqual(set(updates), set(CORRIDOR_UPDATES))
        for update_id, update in updates.items():
            with self.subTest(update_id=update_id):
                # Anything beyond the flag and terrain list (remove_all,
                # place_items, furniture, traps, ...) could discard or add
                # map data and defeat the preservation guarantee.
                self.assertEqual(set(update), {"flags", "place_terrain"})
                for placement in update["place_terrain"]:
                    self.assertEqual(set(placement), {"ter", "x", "y"})
                    self.assertIsInstance(placement["x"], int)
                    self.assertIsInstance(placement["y"], int)
        # Updates that hit the same map must not stack markers on one tile.
        all_tiles = corridor_tiles()
        for om_terrain in set(CORRIDOR_OM_TERRAINS.values()):
            tiles = [
                tile
                for update_id, tiles_for_update in all_tiles.items()
                if CORRIDOR_OM_TERRAINS[update_id] == om_terrain
                for tile in tiles_for_update
            ]
            with self.subTest(om_terrain=om_terrain):
                self.assertEqual(len(tiles), len(set(tiles)))

    def test_corridor_updates_are_fired_against_matching_level_map(self) -> None:
        calls = find_mapgen_update_calls(load_json(DRONES))
        for update_id, om_terrain in CORRIDOR_OM_TERRAINS.items():
            with self.subTest(update_id=update_id):
                self.assertEqual(
                    [call for call in calls if call[0] == update_id],
                    [(update_id, om_terrain)],
                )

    def test_corridor_markers_land_on_secubot_closet_walls(self) -> None:
        maps = {}
        for entry in load_json(CENTRAL_HALLWAY):
            rows = entry.get("object", {}).get("rows")
            if entry.get("type") == "mapgen" and rows:
                for om_terrain in entry.get("om_terrain", []):
                    if isinstance(om_terrain, str):
                        maps[om_terrain] = rows
        for update_id, tiles in corridor_tiles().items():
            om_terrain = CORRIDOR_OM_TERRAINS[update_id]
            self.assertIn(om_terrain, maps)
            rows = maps[om_terrain]
            for x, y in tiles:
                with self.subTest(update_id=update_id, x=x, y=y):
                    self.assertTrue(0 <= y < len(rows))
                    self.assertTrue(0 <= x < len(rows[y]))
                    # The marker opens a closet doorway: a wall tile that
                    # borders a '!' secubot spawn cell on one side.
                    self.assertEqual(rows[y][x], "|")
                    neighbours = rows[y][max(x - 1, 0) : x + 2]
                    self.assertIn("!", neighbours)


if __name__ == "__main__":
    unittest.main()
