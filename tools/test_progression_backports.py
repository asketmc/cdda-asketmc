#!/usr/bin/env python3

"""Focused contracts for the fork's selected progression restorations."""

from __future__ import annotations

import json
import pathlib
import unittest
from typing import Any, Callable


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_json(relative_path: str) -> Any:
    with (ROOT / relative_path).open(encoding="utf-8") as source:
        return json.load(source)


def only(
    objects: list[dict[str, Any]],
    predicate: Callable[[dict[str, Any]], bool],
    label: str,
) -> dict[str, Any]:
    matches = [obj for obj in objects if predicate(obj)]
    if len(matches) != 1:
        raise AssertionError(f"expected one {label}, found {len(matches)}")
    return matches[0]


def entity(
    objects: list[dict[str, Any]], entity_type: str, entity_id: str
) -> dict[str, Any]:
    return only(
        objects,
        lambda obj: obj.get("type") == entity_type
        and obj.get("id") == entity_id,
        f"{entity_type} {entity_id!r}",
    )


def main_mapgens(objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        obj
        for obj in objects
        if obj.get("type") == "mapgen" and "om_terrain" in obj
    ]


def uses_chunk(mapgen: dict[str, Any], chunk: str) -> bool:
    return any(
        chunk in entry.get("chunks", [])
        for entry in mapgen["object"].get("place_nested", [])
    )


class EnergyAndExplorationBackportTests(unittest.TestCase):
    def test_solar_panel_keeps_irradiance_model_with_1_8x_output(self) -> None:
        parts = load_json("data/json/vehicleparts/vehicle_parts.json")
        self.assertEqual(90, entity(parts, "vehicle_part", "solar_panel")["epower"])
        self.assertEqual(
            {"epower": 2.0},
            entity(parts, "vehicle_part", "solar_panel_v2")["proportional"],
        )

    def test_rare_asrg_returns_to_thematic_irradiator(self) -> None:
        irradiator = main_mapgens(
            load_json("data/json/mapgen/irradiator_1.json")
        )
        powered = only(
            irradiator,
            lambda obj: "/" in obj["object"].get("furniture", {}),
            "powered irradiator mapgen",
        )
        self.assertEqual(
            ["f_compact_ASRG_containment"],
            powered["object"]["furniture"]["/"],
        )
        for path in (
            "data/json/mapgen/outpost.json",
            "data/json/mapgen/river_shipwreck.json",
        ):
            self.assertIn(
                "f_active_backup_generator",
                (ROOT / path).read_text(encoding="utf-8"),
                path,
            )

    def test_classic_special_frequency_is_targeted_and_save_safe(self) -> None:
        specials = load_json("data/json/overmap/overmap_special/specials.json")
        lmoe = entity(specials, "overmap_special", "LMOE Shelter")
        self.assertEqual(
            (["land"], [20, -1], [1, 3]),
            (lmoe["locations"], lmoe["city_distance"], lmoe["occurrences"]),
        )
        self.assertIn("CLASSIC", lmoe["flags"])
        for special_id, occurrences in {
            "Lab": [65, 100],
            "Central Lab": [60, 100],
            "Ice Lab": [25, 100],
        }.items():
            special = entity(specials, "overmap_special", special_id)
            self.assertEqual(occurrences, special["occurrences"])
            self.assertTrue({"UNIQUE", "LAB"} <= set(special["flags"]))

    def test_each_ordinary_lmoe_layout_has_one_guaranteed_cache(self) -> None:
        lmoe = main_mapgens(load_json("data/json/mapgen/lmoe.json"))
        ordinary = [
            obj for obj in lmoe if obj["om_terrain"] == ["lmoe_under_empty"]
        ]
        self.assertEqual(3, len(ordinary))
        for mapgen in ordinary:
            caches = [
                entry
                for entry in mapgen["object"].get("place_items", [])
                if entry.get("item") == "lmoe_guns"
            ]
            self.assertEqual([100], [entry.get("chance") for entry in caches])

        nested = load_json("data/json/mapgen/nested/lmoe_nested.json")
        storage = only(
            nested,
            lambda obj: obj.get("nested_mapgen_id")
            == "lmoe3_storage_11x11",
            "shared LMOE storage mapgen",
        )
        self.assertNotIn("place_items", storage["object"])

        occupied = only(
            [obj for obj in lmoe if uses_chunk(obj, "lmoe3_storage_11x11")],
            lambda obj: obj["om_terrain"] == ["lmoe_zombie_under_empty"],
            "occupied shared-storage LMOE",
        )
        whately = only(
            main_mapgens(
                load_json("data/mods/Aftershock/maps/mapgen/whately_lmoe.json")
            ),
            lambda obj: uses_chunk(obj, "lmoe3_storage_11x11"),
            "Whately shared-storage LMOE",
        )
        for consumer in (occupied, whately):
            rewards = consumer["object"].get("place_items", [])
            self.assertFalse(any(x.get("item") == "lmoe_guns" for x in rewards))

    def test_each_classic_lab_finale_has_a_guaranteed_reward(self) -> None:
        finales = main_mapgens(
            load_json("data/json/mapgen/lab/lab_floorplans_finale1level.json")
        )
        self.assertEqual(5, len(finales))
        guaranteed = [
            entry.get("group")
            for entry in finales[0]["object"]["place_loot"]
            if entry.get("chance", 100) == 100
        ]
        self.assertIn("bionics_common", guaranteed)
        self.assertEqual(
            "standard_template_construct",
            finales[1]["object"]["mapping"]["r"]["item"]["item"],
        )
        portal = finales[2]["object"]["mapping"]["R"]["item"]
        self.assertEqual(
            {"dimensional_anchor", "phase_immersion_suit"},
            {entry["item"] for entry in portal},
        )
        for finale in finales[3:]:
            ids = [
                entry
                for entry in finale["object"]["place_loot"]
                if entry.get("item") == "id_science"
            ]
            self.assertEqual(100, ids[0]["chance"])
            self.assertTrue(finale["object"]["place_nested"])
        self.assertEqual(
            "lab_finale_4x4",
            finales[4]["object"]["place_nested"][0]["chunks"][0],
        )


class MilitaryEncounterBackportTests(unittest.TestCase):
    def test_military_map_extras_are_rare_but_discoverable(self) -> None:
        regions = load_json("data/json/regional_map_settings.json")
        extras = entity(regions, "region_settings", "default")["map_extras"]
        self.assertEqual(
            (6, 12, 75, 125),
            (
                extras["field"]["chance"],
                extras["field"]["extras"]["mx_military"],
                extras["road"]["chance"],
                extras["road"]["extras"]["mx_military"],
            ),
        )

    def test_outposts_use_damaged_partially_loaded_rifle_turrets(self) -> None:
        ground = [
            obj
            for obj in main_mapgens(load_json("data/json/mapgen/outpost.json"))
            if any(
                "outpost" in str(omt) and "roof" not in str(omt)
                for omt in obj["om_terrain"]
            )
        ]
        self.assertEqual(2, len(ground))
        for mapgen in ground:
            spawns = mapgen["object"]["place_monster"]
            armed = [x for x in spawns if x["monster"] == "mon_turret_rifle"]
            lights = [
                x for x in spawns if x["monster"] == "mon_turret_searchlight"
            ]
            self.assertEqual((2, 2), (len(armed), len(lights)))
            for entry in armed:
                self.assertEqual(40, entry["chance"])
                self.assertEqual(
                    {"ammo_qty": [80, 240], "hp_percent": [30, 70]},
                    entry["spawn_data"],
                )

    def test_generic_guns_turret_ammunition_remains_compatible(self) -> None:
        overrides = load_json("data/mods/Generic_Guns/robots/active_bots.json")
        by_id = {obj["id"]: obj for obj in overrides}

        def inherited(monster_id: str, member: str) -> Any:
            current = by_id[monster_id]
            seen: set[str] = set()
            while member not in current:
                parent = current["copy-from"]
                self.assertNotIn(parent, seen)
                seen.add(parent)
                current = by_id[parent]
            return current[member]

        for monster_id in (
            "mon_turret_rifle",
            "mon_crows_m240",
            "mon_turret_bmg",
        ):
            starting = inherited(monster_id, "starting_ammo")
            attacks = inherited(monster_id, "special_attacks")
            attack_ammo = {
                attack["ammo_type"]
                for attack in attacks
                if attack.get("type") == "gun"
            }
            self.assertEqual(set(starting), attack_ammo, monster_id)

if __name__ == "__main__":
    unittest.main()
