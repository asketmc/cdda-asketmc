#!/usr/bin/env python3
"""Focused input contracts for inventory transfer QoL."""

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class InventoryTransferInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bindings = json.loads(
            (ROOT / "data/raw/keybindings.json").read_text(encoding="utf-8")
        )
        cls.inventory_ui = (ROOT / "src/inventory_ui.cpp").read_text(encoding="utf-8")
        cls.game_inventory = (ROOT / "src/game_inventory.cpp").read_text(encoding="utf-8")
        cls.sdltiles = (ROOT / "src/sdltiles.cpp").read_text(encoding="utf-8")

    def entry(self, action, category=None):
        return next(
            item for item in self.bindings
            if item.get("id") == action and item.get("category") == category
        )

    def test_classic_inventory_sort_uses_modified_key(self):
        bindings = self.entry("SORT", "INVENTORY")["bindings"]
        self.assertIn({"input_method": "keyboard_char", "key": "CTRL+S"}, bindings)
        self.assertIn(
            {"input_method": "keyboard_code", "key": "s", "mod": ["ctrl"]},
            bindings,
        )

    def test_numeric_right_accepts_arrow_and_keypad(self):
        bindings = self.entry("TEXT.RIGHT")["bindings"]
        self.assertIn({"input_method": "keyboard_any", "key": "RIGHT"}, bindings)
        self.assertNotIn({"input_method": "keyboard_code", "key": "KEYPAD_6"}, bindings)
        self.assertIn("case SDLK_KP_6:", self.sdltiles)
        self.assertIn("keysym.mod & KMOD_NUM ? 0 : KEY_RIGHT", self.sdltiles)
        self.assertIn('query_string( "", true )', self.inventory_ui)

    def test_sorting_is_scoped_to_classic_pickup_and_drop(self):
        drop_ctor = self.inventory_ui.split(
            "inventory_drop_selector::inventory_drop_selector", 1
        )[1].split("void inventory_multiselector::deselect_contained_items", 1)[0]
        self.assertNotIn("enable_sorting();", drop_ctor)
        self.assertIn("inv_s.enable_sorting();", self.game_inventory)
        pickup_ctor = self.inventory_ui.split(
            "pickup_selector::pickup_selector", 1
        )[1].split("void pickup_selector::apply_selection", 1)[0]
        self.assertIn("enable_sorting();", pickup_ctor)


if __name__ == "__main__":
    unittest.main()
