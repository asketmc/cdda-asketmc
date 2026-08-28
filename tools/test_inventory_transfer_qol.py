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

    def entry(self, action, category=None):
        return next(
            item for item in self.bindings
            if item.get("id") == action and item.get("category") == category
        )

    def test_classic_inventory_sort_uses_modified_key(self):
        bindings = self.entry("SORT", "INVENTORY")["bindings"]
        self.assertEqual(
            bindings,
            [{"input_method": "keyboard_code", "key": "s", "mod": ["ctrl"]}],
        )

    def test_numeric_right_accepts_arrow_and_keypad(self):
        bindings = self.entry("TEXT.RIGHT")["bindings"]
        self.assertIn({"input_method": "keyboard_any", "key": "RIGHT"}, bindings)
        self.assertIn({"input_method": "keyboard_code", "key": "KEYPAD_6"}, bindings)


if __name__ == "__main__":
    unittest.main()
