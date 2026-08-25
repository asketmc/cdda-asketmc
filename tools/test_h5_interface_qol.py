#!/usr/bin/env python3
"""Focused data contracts for the H5 interface backport."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KEYBINDINGS = ROOT / "data" / "raw" / "keybindings.json"


def event_key(event):
    return (
        event.get("input_method"),
        event.get("key"),
        tuple(sorted(event.get("mod", []))),
    )


def main():
    entries = json.loads(KEYBINDINGS.read_text(encoding="utf-8"))
    default_entries = [
        entry for entry in entries
        if entry.get("category") in (None, "DEFAULTMODE")
    ]
    insert = next(entry for entry in default_entries if entry.get("id") == "insert")
    morale = next(entry for entry in default_entries if entry.get("id") == "morale")

    assert len( insert["bindings"] ) == 1
    insert_key = event_key(insert["bindings"][0])
    assert insert_key == ("keyboard_code", "b", ("ctrl",))
    assert any(
        event_key(event) == ("keyboard_any", "v", ())
        for event in morale["bindings"]
    )

    conflicts = [
        entry.get("id") for entry in default_entries
        if entry.get("id") != "insert"
        and any(event_key(event) == insert_key for event in entry.get("bindings", []))
    ]
    assert not conflicts, "Insert shortcut conflicts with: " + ", ".join(conflicts)
    print("PASS H5 keybindings: Ctrl+B Insert is unique; v Morale is preserved")


if __name__ == "__main__":
    main()
