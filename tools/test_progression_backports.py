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


def all_dicts(value: Any) -> list[dict[str, Any]]:
    """Return every dictionary nested below a loaded JSON value."""
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        found.append(value)
        for child in value.values():
            found.extend(all_dicts(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(all_dicts(child))
    return found


def weighted_entries(group: dict[str, Any]) -> dict[str, int]:
    """Normalize simple item/group entries to their distribution weights."""
    entries = group.get("items", group.get("entries", []))
    result: dict[str, int] = {}
    for entry in entries:
        if isinstance(entry, list):
            result[entry[0]] = entry[1]
        elif "item" in entry:
            result[entry["item"]] = entry.get("prob", 100)
        elif "group" in entry:
            result[f"group:{entry['group']}"] = entry.get("prob", 100)
    return result


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
        no_hope = entity(load_json("data/mods/No_Hope/palettes.json"), "palette", "empty_bunker_items")["items"]
        self.assertEqual(items["u"], items["!"][:-1])
        self.assertEqual({"item": "lmoe_guns", "chance": 100}, items["!"][-1])
        self.assertEqual(no_hope["u"], no_hope["!"])
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
class CbmScavengingAndUtilityBackportTests(unittest.TestCase):
    def test_railgun_is_active_alongside_throwing_assist(self) -> None:
        bionics = load_json("data/json/bionics.json")
        railgun = entity(bionics, "bionic", "bio_railgun")
        self.assertEqual("10 kJ", railgun["trigger_cost"])
        self.assertIn("BIONIC_TOGGLED", railgun["flags"])

        items = load_json("data/json/items/bionics.json")
        railgun_item = entity(items, "BIONIC_ITEM", "bio_railgun")
        self.assertEqual("AID_bio_railgun", railgun_item["installation_data"])
        self.assertIn("10 kJ", railgun_item["description"])

        software = load_json("data/json/items/software.json")
        entity(software, "GENERIC", "AID_bio_railgun")

        obsolete = load_json("data/json/obsolete.json")
        obsolete_railgun = [obj for obj in obsolete if obj.get("id") == "bio_railgun"]
        self.assertEqual([], obsolete_railgun)
        self.assertFalse(any(obj.get("id") == "AID_bio_railgun" for obj in obsolete))

        throwing_assist = entity(bionics, "bionic", "bio_pitch_perfect")
        throwing_assist_item = entity(items, "BIONIC_ITEM", "bio_pitch_perfect")
        self.assertEqual("Throwing Assist", throwing_assist["name"]["str"])
        self.assertEqual("Throwing Assist CBM", throwing_assist_item["name"]["str"])

    def test_railgun_has_power_safe_runtime_hooks_and_salvage_routes(self) -> None:
        character_source = (ROOT / "src/character.cpp").read_text(encoding="utf-8")
        ranged_source = (ROOT / "src/ranged.cpp").read_text(encoding="utf-8")
        self.assertIn("ret *= 2", character_source)
        self.assertIn("get_power_level() >= bio_railgun->power_trigger", character_source)
        chain_materials = ("budget_steel_chain", "ch_steel_chain", "hc_steel_chain",
                           "lc_steel_chain", "mc_steel_chain", "qt_steel_chain")
        ferric_marker = "static const std::set<material_id> ferric = {"
        self.assertIn(ferric_marker, character_source)
        ferric_initializer = character_source.split(ferric_marker, 1)[1].split("};", 1)[0]
        for material in ("lc_steel", *chain_materials):
            self.assertIn(f"material_{material}", ferric_initializer)
        self.assertIn("!mech_assisted", character_source)
        self.assertEqual(2, ranged_source.count("railgun_eligible_throw( thrown )"))
        self.assertNotIn("case_hardened_steel", ranged_source)
        self.assertIn('proj_effects.insert( "LIGHTNING" )', ranged_source)
        self.assertIn("mod_power_level( -trigger_cost )", ranged_source)

        groups = load_json("data/json/itemgroups/bionics.json")
        self.assertNotIn("bio_railgun", weighted_entries(entity(groups, "item_group", "bionics")))
        self.assertEqual(5, weighted_entries(entity(groups, "item_group", "bionics_mil"))["bio_railgun"])
        self.assertEqual(10, weighted_entries(entity(groups, "item_group", "bionics_op2_off"))["bio_railgun"])

        harvest = load_json("data/json/itemgroups/Monsters_Animals_Lairs/harvest_cbm.json")
        ranged_harvest = entity(
            harvest, "item_group", "Zomborg_CBM_harvest_ranged_weapons"
        )
        self.assertEqual(3, weighted_entries(ranged_harvest)["bio_railgun"])

        exodii = load_json("data/json/npcs/exodii/exodii_merchant_itemlist.json")
        tier_three = entity(exodii, "item_group", "EXODII_CBM_Store_Tier3")
        self.assertEqual(5, weighted_entries(tier_three)["bio_railgun"])

        electronics = load_json("data/json/itemgroups/electronics.json")
        programs = entity(electronics, "item_group", "autodoc_installation_programs")
        self.assertIn("AID_bio_railgun", weighted_entries(programs))

        runtime_test = (ROOT / "tests/throwing_test.cpp").read_text(encoding="utf-8")
        self.assertIn("railgun requires and consumes its trigger power", runtime_test)
        self.assertIn('"lc_cavalry_sabre"', runtime_test)
        self.assertIn('"lc_chainmail_hands"', runtime_test)
        self.assertIn("powered mech throw assist suppresses Railgun consistently", runtime_test)
        self.assertIn('proj.proj_effects.count( "LIGHTNING" ) == 1', runtime_test)
        self.assertIn("thrower.get_power_level() == 0_kJ", runtime_test)

    def test_integrated_multitool_restores_classic_work_qualities(self) -> None:
        expected = {
            "HAMMER": 3,
            "HAMMER_FINE": 1,
            "SAW_W": 1,
            "SAW_M": 2,
            "SAW_M_FINE": 1,
            "WRENCH": 2,
            "WRENCH_FINE": 1,
            "WHEEL_FAST": 1,
            "SCREW": 1,
            "SCREW_FINE": 1,
            "CUT": 2,
            "PRY": 1,
            "PRYING_NAIL": 1,
            "DRILL": 3,
        }
        sources = (
            ("data/json/items/fake.json", "toolset"),
            ("data/json/items/tool/workshop.json", "toolset_extended"),
        )
        for path, item_id in sources:
            tool = entity(load_json(path), "TOOL", item_id)
            qualities = dict(tool["qualities"])
            for quality, level in expected.items():
                self.assertEqual(level, qualities[quality], f"{item_id}: {quality}")
            string_actions = {action for action in tool["use_action"] if isinstance(action, str)}
            self.assertGreaterEqual(string_actions, {"HAMMER", "CROWBAR"})

    def test_ordinary_and_exodii_corpse_salvage_remains_dirty_and_skill_scaled(self) -> None:
        harvests = load_json("data/json/harvest_dissect.json")
        ids = (
            "dissect_mon_zombie_scientist",
            "dissect_mon_zombie_technician",
            "dissect_bionics_mil",
            "dissect_mon_zombie_bio_op",
            "dissect_mon_zombie_bio_op2",
            "dissect_mon_zomborg",
        )
        for harvest_id in ids:
            harvest = entity(harvests, "harvest", harvest_id)
            bionic_entries = [
                entry
                for entry in harvest["entries"]
                if entry["type"] in {"bionic", "bionic_group"}
            ]
            self.assertGreater(len(bionic_entries), 0, harvest_id)
            for entry in bionic_entries:
                self.assertEqual(
                    {"FILTHY", "NO_STERILE", "NO_PACKED"},
                    set(entry["flags"]),
                    harvest_id,
                )
                self.assertEqual(["fault_bionic_salvaged"], entry["faults"])
                self.assertEqual([0, 2], entry["base_num"])
                self.assertEqual([0.1, 0.6], entry["scale_num"])
                self.assertEqual(5, entry["max"])

    def test_thematic_location_groups_restore_low_rate_cbm_scavenging(self) -> None:
        locations = load_json("data/json/itemgroups/Locations_MapExtras/locations.json")
        hospital = weighted_entries(entity(locations, "item_group", "hospital_medical_items"))
        self.assertEqual(5, hospital["group:bionics_common"])

        mine = weighted_entries(entity(locations, "item_group", "mine_equipment"))
        self.assertEqual(
            {
                "bio_tools": 3,
                "bio_flashlight": 3,
                "bio_lighter": 3,
                "bio_magnet": 3,
                "bio_resonator": 2,
                "bio_hydraulics": 2,
                "bio_weight": 2,
            },
            {item_id: mine[item_id] for item_id in (
                "bio_tools", "bio_flashlight", "bio_lighter", "bio_magnet",
                "bio_resonator", "bio_hydraulics", "bio_weight"
            )},
        )

        robofac = load_json("data/json/itemgroups/Locations_MapExtras/robofac_trade.json")
        trade = weighted_entries(entity(robofac, "item_group", "robofac_basic_trade"))
        self.assertEqual(25, trade["group:bionics_common"])

        science = load_json("data/json/itemgroups/science_and_tech.json")
        tech = weighted_entries(entity(science, "item_group", "science"))
        expected = {
            "bio_purifier": 4,
            "bio_sunglasses": 4,
            "bio_eye_optic": 4,
            "bio_climate": 4,
            "bio_heatsink": 4,
            "bio_blood_filter": 4,
            "bio_watch": 4,
            "bio_leukocyte": 3,
            "bio_faraday": 2,
            "bio_remote": 3,
            "bio_soporific": 2,
            "bio_surgical_razor": 2,
            "bio_syringe": 3,
        }
        self.assertEqual(expected, {item_id: tech[item_id] for item_id in expected})

    def test_selected_mapgens_restore_sparse_thematic_cbm_caches(self) -> None:
        cases = (
            ("data/json/mapgen/basement/basement_bionic.json", "group", None, 7, 9),
            ("data/json/mapgen/bunker.json", "group", 35, 16, 4),
            ("data/json/mapgen/military/mil_base/mil_base_z0.json", "group", 25, 26, 15),
            ("data/json/mapgen/mortuary.json", "item", 15, 8, 19),
            ("data/json/mapgen/police_station.json", "item", 5, None, None),
            ("data/json/mapgen/prison/prison.json", "item", 10, None, None),
        )
        for path, kind, chance, x, y in cases:
            group_id = "bionics_mil" if "bunker" in path or "mil_base" in path else "bionics_common"
            matches = [entry for entry in all_dicts(load_json(path)) if entry.get(kind) == group_id]
            self.assertEqual(1, len(matches), path)
            entry = matches[0]
            self.assertEqual(chance, entry.get("chance"), path)
            if x is not None:
                self.assertEqual(x, entry["x"], path)
            if y is not None:
                self.assertEqual(y, entry["y"], path)

        electronics = [
            entry
            for entry in all_dicts(load_json("data/json/mapgen/s_electronics.json"))
            if entry.get("item") == "bionics_common"
        ]
        self.assertEqual(2, len(electronics))
        self.assertEqual({15}, {entry["chance"] for entry in electronics})
        self.assertEqual({8}, {entry["y"] for entry in electronics})
        self.assertFalse(any("repeat" in entry for entry in electronics))


class ManualInstallationAndExodiiBackportTests(unittest.TestCase):
    def test_manual_installation_is_disabled_in_core_and_enabled_only_by_mod(self) -> None:
        core_options = load_json("data/core/game_balance.json")
        manual_core = only(
            core_options,
            lambda obj: obj.get("type") == "EXTERNAL_OPTION"
            and obj.get("name") == "MANUAL_BIONIC_INSTALLATION",
            "core manual-install option",
        )
        self.assertEqual(("bool", False), (manual_core["stype"], manual_core["value"]))

        modinfo = entity(
            load_json("data/mods/ManualBionicInstall/modinfo.json"),
            "MOD_INFO",
            "manualbionicinstall",
        )
        self.assertEqual(["dda"], modinfo["dependencies"])
        mod_options = load_json("data/mods/ManualBionicInstall/game_balance.json")
        manual_mod = only(
            mod_options,
            lambda obj: obj.get("type") == "EXTERNAL_OPTION"
            and obj.get("name") == "MANUAL_BIONIC_INSTALLATION",
            "mod manual-install option",
        )
        self.assertEqual(("bool", True), (manual_mod["stype"], manual_mod["value"]))

    def test_generic_manual_procedure_requires_tools_and_sterile_consumables(self) -> None:
        requirements = load_json("data/json/requirements/toolsets.json")
        procedure = entity(requirements, "requirement", "manual_cbm_installation")
        self.assertEqual(
            [{"id": "CUT_FINE", "level": 1}, {"id": "SCREW_FINE", "level": 1}],
            procedure["qualities"],
        )
        self.assertEqual(
            [["soldering_iron", 50], ["toolset", 50], ["small_repairkit", 50],
             ["large_repairkit", 50]],
            procedure["tools"][0],
        )
        self.assertEqual(
            [
                [["solder_wire", 20]],
                [["disinfectant", 10], ["disinfectant_makeshift", 20]],
                [["bandages", 2], ["bandages_makeshift_bleached", 4],
                 ["bandages_makeshift_boiled", 4]],
            ],
            procedure["components"],
        )

    def test_manual_runtime_keeps_skill_sterility_pain_and_failure_boundaries(self) -> None:
        bionics_source = (ROOT / "src/bionics.cpp").read_text(encoding="utf-8")
        actor_source = (ROOT / "src/iuse_actor.cpp").read_text(encoding="utf-8")
        self.assertIn("manual_install_electronics = 8", bionics_source)
        self.assertIn("manual_install_firstaid = 6", bionics_source)
        self.assertIn("manual_install_mechanics = 4", bionics_source)
        self.assertIn("manual_install_max_success = 95", bionics_source)
        self.assertEqual(2, bionics_source.count("&installer == this"))
        self.assertNotIn("installer.is_avatar()", bionics_source)
        self.assertIn("requirement_manual_bionic_installation", bionics_source)
        self.assertIn("if( difficulty <= 0 )", bionics_source)
        self.assertIn("p.mod_pain( 10 + it.type->bionic->difficulty * 3 )", actor_source)
        self.assertIn("This CBM has no manual installation procedure", actor_source)
        self.assertIn("flag_FILTHY", actor_source)
        self.assertIn("flag_NO_STERILE", actor_source)
        self.assertIn("consume_anesth_requirement", actor_source)

        runtime_test = (ROOT / "tests/bionics_test.cpp").read_text(encoding="utf-8")
        self.assertIn("manual CBM installation is an opt-in expert route", runtime_test)
        self.assertIn('override_option manual_install( "MANUAL_BIONIC_INSTALLATION"', runtime_test)
        self.assertIn("electronics below 8", runtime_test)
        self.assertIn("health care below 6", runtime_test)
        self.assertIn("mechanics below 4", runtime_test)
        self.assertIn("install_action->can_call", runtime_test)
        self.assertIn("does not bypass implant sterility", runtime_test)
        self.assertIn("uncapped > 95", runtime_test)
        self.assertIn("zero-difficulty implants without a procedure are rejected safely", runtime_test)
        self.assertIn("surgery-start pain cannot cancel the operation it just started", runtime_test)
        self.assertIn("activity.is_interruptible()", runtime_test)

    def test_exodii_stock_is_faster_but_remains_trust_gated(self) -> None:
        definitions = load_json("data/json/npcs/exodii/exodii_merchant_definitions.json")
        merchant = entity(definitions, "npc_class", "NC_EXODII_TYPE_1_Merchant")
        self.assertEqual("3 days", merchant["restock_interval"])
        groups = merchant["shopkeeper_item_group"]
        self.assertEqual(
            {
                "EXODII_basic_trade": None,
                "EXODII_CBM_Store_tier1_extra": 1,
                "EXODII_CBM_Store_Tier2": 8,
                "EXODII_CBM_Store_Tier3": 16,
                "EXODII_Store_Salvage_Tech": 16,
                "EXODII_CBM_Store_Tier4": 30,
            },
            {entry["group"]: entry.get("trust") for entry in groups},
        )
        self.assertTrue(all(entry.get("rigid") is True for entry in groups))
        self.assertTrue(all("strict" not in entry for entry in groups))

        talk = load_json("data/json/npcs/exodii/exodii_merchant_talk.json")
        timers = [
            obj
            for obj in all_dicts(talk)
            if obj.get("u_add_effect") == "u_exodii_interaction_timer_long"
        ]
        self.assertEqual(["3 days"], [timer["duration"] for timer in timers])

    def test_exodii_discount_has_a_focused_runtime_gate(self) -> None:
        trade_source = (ROOT / "src/npctrade.cpp").read_text(encoding="utf-8")
        self.assertIn('faction_exodii( "exodii" )', trade_source)
        self.assertIn("bionic_install_service_multiplier( installer )", trade_source)

        runtime_test = (ROOT / "tests/bionics_test.cpp").read_text(encoding="utf-8")
        self.assertIn("Exodii retain the least expensive deterministic CBM service", runtime_test)
        self.assertIn("bionic_install_service_multiplier( rubik ) == 1", runtime_test)
        self.assertIn("bionic_install_service_multiplier( ordinary_installer ) == 2", runtime_test)

        workflow = (ROOT / ".github/workflows/windows-release.yml").read_text(encoding="utf-8")
        self.assertIn("bionics_test.cpp", workflow)
        self.assertIn('"[bionics][progression]"', workflow)


if __name__ == "__main__": unittest.main()
