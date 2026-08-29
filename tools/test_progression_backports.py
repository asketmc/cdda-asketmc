#!/usr/bin/env python3

"""Focused contracts for the fork's selected progression restorations."""

from __future__ import annotations

import json
import pathlib
import unittest
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_json(relative_path: str) -> Any:
    with (ROOT / relative_path).open(encoding="utf-8") as source:
        return json.load(source)


def entity(objects: list[dict[str, Any]], entity_type: str, entity_id: str) -> dict[str, Any]:
    matches = [
        obj
        for obj in objects
        if obj.get("type") == entity_type and obj.get("id") == entity_id
    ]
    if len(matches) != 1:
        raise AssertionError(
            f"expected one {entity_type} {entity_id!r}, found {len(matches)}"
        )
    return matches[0]


def main_mapgens(objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        obj
        for obj in objects
        if obj.get("type") == "mapgen" and "om_terrain" in obj
    ]


class EnergyAndExplorationBackportTests(unittest.TestCase):
    def test_solar_panel_keeps_irradiance_model_with_1_8x_output(self) -> None:
        parts = load_json("data/json/vehicleparts/vehicle_parts.json")
        base = entity(parts, "vehicle_part", "solar_panel")
        advanced = entity(parts, "vehicle_part", "solar_panel_v2")

        self.assertEqual(90, base["epower"])
        self.assertEqual({"epower": 2.0}, advanced["proportional"])

        source = (ROOT / "src/vehicle.cpp").read_text(encoding="utf-8")
        self.assertIn("incident_sun_irradiance", source)
        self.assertNotIn("epower = 50", source)

    def test_rare_asrg_returns_to_thematic_irradiator(self) -> None:
        irradiator = load_json("data/json/mapgen/irradiator_1.json")
        mapgens = [
            obj
            for obj in main_mapgens(irradiator)
            if "/" in obj["object"].get("furniture", {})
        ]
        self.assertEqual(1, len(mapgens))
        furniture = mapgens[0]["object"]["furniture"]
        self.assertEqual(["f_compact_ASRG_containment"], furniture["/"])

        conventional_sites = {
            "data/json/mapgen/outpost.json",
            "data/json/mapgen/river_shipwreck.json",
        }
        for path in conventional_sites:
            self.assertIn(
                "f_active_backup_generator",
                (ROOT / path).read_text(encoding="utf-8"),
                path,
            )

    def test_classic_special_frequency_is_targeted_and_save_safe(self) -> None:
        specials = load_json("data/json/overmap/overmap_special/specials.json")

        lmoe = entity(specials, "overmap_special", "LMOE Shelter")
        self.assertEqual(["land"], lmoe["locations"])
        self.assertEqual([20, -1], lmoe["city_distance"])
        self.assertEqual([1, 3], lmoe["occurrences"])
        self.assertIn("CLASSIC", lmoe["flags"])

        expected = {
            "Lab": [65, 100],
            "Central Lab": [60, 100],
            "Ice Lab": [25, 100],
        }
        for special_id, occurrences in expected.items():
            special = entity(specials, "overmap_special", special_id)
            self.assertEqual(occurrences, special["occurrences"])
            self.assertIn("UNIQUE", special["flags"])
            self.assertIn("LAB", special["flags"])

    def test_each_ordinary_lmoe_layout_has_one_guaranteed_cache(self) -> None:
        lmoe = main_mapgens(load_json("data/json/mapgen/lmoe.json"))
        ordinary = [obj for obj in lmoe if obj["om_terrain"] == ["lmoe_under_empty"]]
        self.assertEqual(3, len(ordinary))

        explicit = ordinary[:2]
        for mapgen in explicit:
            caches = mapgen["object"]["place_items"]
            self.assertEqual(
                1,
                sum(entry.get("item") == "lmoe_guns" and entry.get("chance") == 100
                    for entry in caches),
            )

        nested = load_json("data/json/mapgen/nested/lmoe_nested.json")
        storage_matches = [
            obj
            for obj in nested
            if obj.get("type") == "mapgen"
            and obj.get("nested_mapgen_id") == "lmoe3_storage_11x11"
        ]
        self.assertEqual(1, len(storage_matches))
        storage = storage_matches[0]
        self.assertEqual(
            [{"item": "lmoe_guns", "x": 0, "y": 0, "chance": 100}],
            storage["object"]["place_items"],
        )

    def test_each_classic_lab_finale_has_a_guaranteed_reward(self) -> None:
        finales = load_json("data/json/mapgen/lab/lab_floorplans_finale1level.json")
        main = main_mapgens(finales)
        self.assertEqual(5, len(main))

        autodoc = main[0]["object"]
        guaranteed_groups = {
            entry.get("group")
            for entry in autodoc["place_loot"]
            if entry.get("chance", 100) == 100
        }
        self.assertIn("bionics_common", guaranteed_groups)

        nanofab = main[1]["object"]["mapping"]
        self.assertEqual("standard_template_construct", nanofab["r"]["item"]["item"])

        portal = main[2]["object"]["mapping"]["R"]["item"]
        self.assertEqual(
            {"dimensional_anchor", "phase_immersion_suit"},
            {entry["item"] for entry in portal},
        )

        mutagen = main[3]["object"]
        science_ids = [
            entry
            for entry in mutagen["place_loot"]
            if entry.get("item") == "id_science"
        ]
        self.assertEqual(100, science_ids[0]["chance"])
        self.assertTrue(mutagen["place_nested"])

        turret = main[4]["object"]
        science_ids = [
            entry
            for entry in turret["place_loot"]
            if entry.get("item") == "id_science"
        ]
        self.assertEqual(100, science_ids[0]["chance"])
        self.assertEqual("lab_finale_4x4", turret["place_nested"][0]["chunks"][0])


class MilitaryEncounterBackportTests(unittest.TestCase):
    def test_military_map_extras_are_rare_but_discoverable(self) -> None:
        regions = load_json("data/json/regional_map_settings.json")
        default = entity(regions, "region_settings", "default")
        extras = default["map_extras"]

        self.assertEqual(6, extras["field"]["chance"])
        self.assertEqual(12, extras["field"]["extras"]["mx_military"])
        self.assertEqual(75, extras["road"]["chance"])
        self.assertEqual(125, extras["road"]["extras"]["mx_military"])

    def test_outposts_use_damaged_partially_loaded_rifle_turrets(self) -> None:
        outposts = main_mapgens(load_json("data/json/mapgen/outpost.json"))
        ground = [
            obj
            for obj in outposts
            if any("outpost" in str(omt) and "roof" not in str(omt)
                   for omt in obj["om_terrain"])
        ]
        self.assertEqual(2, len(ground))

        armed_count = 0
        for mapgen in ground:
            spawns = mapgen["object"]["place_monster"]
            armed = [entry for entry in spawns if entry["monster"] == "mon_turret_rifle"]
            lights = [entry for entry in spawns if entry["monster"] == "mon_turret_searchlight"]
            self.assertEqual(2, len(armed))
            self.assertEqual(2, len(lights))
            for entry in armed:
                self.assertEqual(40, entry["chance"])
                data = entry["spawn_data"]
                self.assertEqual([30, 70], data["hp_percent"])
                self.assertEqual("556", data["ammo"][0]["ammo_id"])
                self.assertEqual([80, 240], data["ammo"][0]["qty"])
            armed_count += len(armed)
        self.assertEqual(4, armed_count)

    def test_roadblocks_select_three_damaged_turret_tiers(self) -> None:
        source = (ROOT / "src/map_extras.cpp").read_text(encoding="utf-8")
        for monster_id in ("mon_turret_rifle", "mon_crows_m240", "mon_turret_bmg"):
            self.assertIn(monster_id, source)
        self.assertIn("data.hp_percent = jmapgen_int( 30, 70 )", source)
        self.assertIn("jmapgen_int( 80, 240 )", source)
        self.assertIn("jmapgen_int( 50, 150 )", source)
        self.assertIn("jmapgen_int( 20, 60 )", source)

    def test_spawn_damage_contract_is_validated_and_runtime_tested(self) -> None:
        parser = (ROOT / "src/mapgen.cpp").read_text(encoding="utf-8")
        self.assertIn('jmapgen_int( sd, "hp_percent", 100, 100 )', parser)
        self.assertIn("data.hp_percent.val < 1", parser)
        self.assertIn("data.hp_percent.valmax > 100", parser)

        runtime_test = (ROOT / "tests/mapgen_spawn_data_test.cpp").read_text(
            encoding="utf-8"
        )
        self.assertIn("turret->get_hp_max() / 2", runtime_test)
        self.assertIn("turret->ammo.at( itype_556 ) == 80", runtime_test)


if __name__ == "__main__":
    unittest.main()
