#!/usr/bin/env python3
"""Focused contracts for the fork's selected progression restorations."""

from __future__ import annotations

import json
import pathlib
import unittest
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]

def load_json(path: str) -> Any:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def only(objects: list[dict[str, Any]], predicate, label: str) -> dict[str, Any]:
    matches = [obj for obj in objects if predicate(obj)]
    if len(matches) != 1:
        raise AssertionError(f"expected one {label}, found {len(matches)}")
    return matches[0]

def entity(objects: list[dict[str, Any]], kind: str, entity_id: str) -> dict[str, Any]:
    matches = lambda obj: obj.get("type") == kind and obj.get("id") == entity_id
    return only(objects, matches, f"{kind} {entity_id!r}")

def mapgens(objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [obj for obj in objects if obj.get("type") == "mapgen" and "om_terrain" in obj]


def uses_chunk(mapgen: dict[str, Any], chunk: str) -> bool:
    return any(chunk in entry.get("chunks", []) for entry in mapgen["object"].get("place_nested", []))

class EnergyAndExplorationBackportTests(unittest.TestCase):
    def test_solar_panel_keeps_irradiance_model_with_1_8x_output(self) -> None:
        parts = load_json("data/json/vehicleparts/vehicle_parts.json")
        self.assertEqual(90, entity(parts, "vehicle_part", "solar_panel")["epower"])
        self.assertEqual({"epower": 2.0},
                         entity(parts, "vehicle_part", "solar_panel_v2")["proportional"])

    def test_rare_asrg_returns_to_thematic_irradiator(self) -> None:
        irradiator = mapgens(load_json("data/json/mapgen/irradiator_1.json"))
        powered = only(irradiator, lambda x: "i" in x["object"].get("furniture", {}), "irradiator")["object"]
        self.assertEqual(["f_active_backup_generator"], powered["furniture"]["/"])
        self.assertEqual(2, sum(row.count("/") for row in powered["rows"]))
        self.assertEqual(1, sum(row.count("i") for row in powered["rows"]))
        self.assertEqual(["f_compact_ASRG_containment"], powered["furniture"]["i"])
        for glyph in ("/", "i"):
            self.assertEqual({"field": "fd_shock_vent"}, powered["fields"][glyph])
        for path in ("data/json/mapgen/outpost.json", "data/json/mapgen/river_shipwreck.json"):
            self.assertIn("f_active_backup_generator", (ROOT / path).read_text(encoding="utf-8"), path)

    def test_classic_special_frequency_is_targeted_and_save_safe(self) -> None:
        specials = load_json("data/json/overmap/overmap_special/specials.json")
        lmoe = entity(specials, "overmap_special", "LMOE Shelter")
        self.assertEqual((["land"], [20, -1], [1, 3]),
                         (lmoe["locations"], lmoe["city_distance"], lmoe["occurrences"]))
        self.assertIn("CLASSIC", lmoe["flags"])
        expected = {"Lab": [65, 100], "Central Lab": [60, 100], "Ice Lab": [25, 100]}
        for special_id, occurrences in expected.items():
            special = entity(specials, "overmap_special", special_id)
            self.assertEqual(occurrences, special["occurrences"])
            self.assertTrue({"UNIQUE", "LAB"} <= set(special["flags"]))

    def test_each_ordinary_lmoe_layout_has_one_guaranteed_cache(self) -> None:
        lmoe = mapgens(load_json("data/json/mapgen/lmoe.json"))
        ordinary = [obj for obj in lmoe if obj["om_terrain"] == ["lmoe_under_empty"]]
        self.assertEqual(3, len(ordinary))
        self.assertEqual([1] * 3, [sum(row.count("!") for row in layout["object"]["rows"]) for layout in ordinary])
        expected = [[{"furn": "f_utility_shelf", "x": x, "y": y}] for x, y in ((3, 4), (12, 9), (11, 11))]
        self.assertEqual(expected, [layout["object"]["place_furniture"] for layout in ordinary])
        self.assertTrue(all("place_items" not in layout["object"] for layout in ordinary))
        items = entity(load_json("data/json/mapgen_palettes/lmoe.json"), "palette", "empty_bunker_items")["items"]
        self.assertEqual(("lmoe_guns", 100), (items["!"]["item"], items["!"]["chance"]))
        self.assertNotIn("!", entity(load_json("data/mods/No_Hope/palettes.json"), "palette", "empty_bunker_items")["items"])
        storage = only(load_json("data/json/mapgen/nested/lmoe_nested.json"), lambda x: x.get("nested_mapgen_id") == "lmoe3_storage_11x11", "storage")
        self.assertNotIn("place_items", storage["object"])
        consumers = [obj for obj in lmoe if uses_chunk(obj, "lmoe3_storage_11x11")]
        occupied = only(consumers, lambda x: x["om_terrain"] == ["lmoe_zombie_under_empty"], "occupied")
        whately = only(mapgens(load_json("data/mods/Aftershock/maps/mapgen/whately_lmoe.json")),
                       lambda x: uses_chunk(x, "lmoe3_storage_11x11"), "Whately")
        for consumer in (occupied, whately):
            self.assertFalse(any("!" in row for row in consumer["object"]["rows"]))
    def test_each_classic_lab_finale_has_a_guaranteed_reward(self) -> None:
        finales = mapgens(load_json("data/json/mapgen/lab/lab_floorplans_finale1level.json"))
        self.assertEqual(5, len(finales))
        guaranteed = [entry.get("group") for entry in finales[0]["object"]["place_loot"]
                      if entry.get("chance", 100) == 100]
        self.assertIn("bionics_common", guaranteed)
        self.assertEqual("standard_template_construct", finales[1]["object"]["mapping"]["r"]["item"]["item"])
        portal = finales[2]["object"]["mapping"]["R"]["item"]
        self.assertEqual({"dimensional_anchor", "phase_immersion_suit"}, {entry["item"] for entry in portal})
        for finale in finales[3:]:
            ids = [entry for entry in finale["object"]["place_loot"] if entry.get("item") == "id_science"]
            self.assertEqual(100, ids[0]["chance"])
            self.assertTrue(finale["object"]["place_nested"])
        self.assertEqual("lab_finale_4x4", finales[4]["object"]["place_nested"][0]["chunks"][0])


class MilitaryEncounterBackportTests(unittest.TestCase):
    def test_military_map_extras_are_rare_but_discoverable(self) -> None:
        regions = load_json("data/json/regional_map_settings.json")
        extras = entity(regions, "region_settings", "default")["map_extras"]
        actual = (extras["field"]["chance"], extras["field"]["extras"]["mx_military"],
                  extras["road"]["chance"], extras["road"]["extras"]["mx_military"])
        self.assertEqual((6, 12, 75, 125), actual)
    def test_outposts_use_damaged_partially_loaded_rifle_turrets(self) -> None:
        ground = [obj for obj in mapgens(load_json("data/json/mapgen/outpost.json"))
                  if any("outpost" in str(omt) and "roof" not in str(omt) for omt in obj["om_terrain"])]
        self.assertEqual(2, len(ground))
        for layout in ground:
            spawns = layout["object"]["place_monster"]
            armed = [entry for entry in spawns if entry["monster"] == "mon_turret_rifle"]
            lights = [entry for entry in spawns if entry["monster"] == "mon_turret_searchlight"]
            self.assertEqual((2, 4), (len(armed), len(lights)))
            self.assertEqual({(1, 1), (22, 22), (1, 22), (22, 1)},
                             {(entry["x"], entry["y"]) for entry in lights})
            self.assertEqual({(3, 1), (3, 22)}, {(entry["x"], entry["y"]) for entry in armed})
            expected = (40, {"ammo_qty": [80, 240], "hp_percent": [30, 70]})
            self.assertEqual([expected] * 2, [(entry["chance"], entry["spawn_data"]) for entry in armed])
    def test_generic_guns_turret_ammunition_remains_compatible(self) -> None:
        overrides = load_json("data/mods/Generic_Guns/robots/active_bots.json")
        by_id = {obj["id"]: obj for obj in overrides}
        def inherited(monster_id: str, member: str) -> Any:
            current, seen = by_id[monster_id], set()
            while member not in current:
                parent = current["copy-from"]
                self.assertNotIn(parent, seen)
                seen.add(parent)
                current = by_id[parent]
            return current[member]
        for monster_id in ("mon_turret_rifle", "mon_crows_m240", "mon_turret_bmg"):
            starting = inherited(monster_id, "starting_ammo")
            attacks = inherited(monster_id, "special_attacks")
            ammo = {attack["ammo_type"] for attack in attacks if attack.get("type") == "gun"}
            self.assertEqual(set(starting), ammo, monster_id)


if __name__ == "__main__": unittest.main()
