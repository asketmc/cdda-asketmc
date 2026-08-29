#!/usr/bin/env python3

import pathlib
import unittest

from tools.patchnotes_lint import (
    PATCHNOTES_PATH,
    SECTIONS,
    TAGGED_SECTIONS,
    TITLE,
    lint,
    looks_like_commit_sha,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]


def build(**overrides: str) -> str:
    """Assemble a minimal conforming document, optionally replacing a section."""
    parts = [TITLE, "", "One line of framing prose.", ""]
    for name in SECTIONS:
        parts.append(f"## {name}")
        parts.append("")
        if name in overrides:
            parts.append(overrides[name])
        elif name in TAGGED_SECTIONS:
            parts.append("- `New` Something a player can observe.")
        else:
            parts.append("- Something a player can observe.")
        parts.append("")
    return "\n".join(parts[:-1]) + "\n"


class PatchnotesLintTest(unittest.TestCase):
    def test_minimal_conforming_document_passes(self) -> None:
        self.assertEqual(lint(build()), [])

    def test_hex_word_is_not_mistaken_for_a_commit_id(self) -> None:
        self.assertFalse(looks_like_commit_sha("defaced"))
        self.assertFalse(looks_like_commit_sha("12345678"))
        self.assertTrue(looks_like_commit_sha("d6ec4661"))

    def test_rejects_commit_ids(self) -> None:
        document = build(**{"Optional mods": "- `New` See d6ec466140839dd70c1a43671eb4a08b007695c2."})
        self.assertIn("BACKPORTS.md", "\n".join(lint(document)))

    def test_rejects_dates_and_release_tags(self) -> None:
        dated = build(**{"Known limits": "- Fixed on 2026-08-26."})
        tagged = build(**{"Known limits": "- Shipped in v0.G-additive-2026.08.25."})
        for document in (dated, tagged):
            self.assertIn("CHANGELOG.md", "\n".join(lint(document)))

    def test_rejects_fork_pull_request_references(self) -> None:
        bare = build(**{"Known limits": "- Tracked in #27."})
        linked = build(
            **{"Known limits": "- See https://github.com/asketmc/cdda-asketmc/pull/27 here."}
        )
        for document in (bare, linked):
            self.assertIn("CHANGELOG.md", "\n".join(lint(document)))

    def test_allows_upstream_donor_links(self) -> None:
        document = build(
            **{
                "Optional mods": (
                    "- `New` Rotor content.\n"
                    "  ([DDA #73610](https://github.com/CleverRaven/Cataclysm-DDA/pull/73610))"
                )
            }
        )
        self.assertEqual(lint(document), [])

    def test_rejects_unfinished_work_markers(self) -> None:
        document = build(**{"Known limits": "- TODO: add Catch coverage."})
        self.assertIn("ships to players", "\n".join(lint(document)))

    def test_requires_a_tag_in_difference_sections(self) -> None:
        document = build(**{"Vehicles and mobile bases": "- Vehicles can be locked."})
        self.assertIn("must open with one of", "\n".join(lint(document)))

    def test_rejects_unknown_tags(self) -> None:
        document = build(**{"Vehicles and mobile bases": "- `Tweaked` Vehicles can be locked."})
        self.assertIn("unknown tag", "\n".join(lint(document)))

    def test_does_not_require_a_tag_outside_difference_sections(self) -> None:
        self.assertEqual(lint(build(**{"Non-goals": "- No wholesale 0.H merge."})), [])

    def test_rejects_missing_reordered_and_invented_sections(self) -> None:
        missing = build().replace(f"## {SECTIONS[-1]}\n", "")
        invented = build().replace(f"## {SECTIONS[2]}", "## Assorted other things")
        for document in (missing, invented):
            self.assertIn("in this order", "\n".join(lint(document)))

    def test_rejects_deep_headings_and_deep_nesting(self) -> None:
        deep_heading = build(**{"Known limits": "#### Sub-sub-heading\n\n- A limit."})
        deep_bullet = build(**{"Known limits": "- A limit.\n    - Over-indented detail."})
        self.assertIn("deeper than ###", "\n".join(lint(deep_heading)))
        self.assertIn("at most one level", "\n".join(lint(deep_bullet)))

    def test_measures_a_wrapped_entry_whole(self) -> None:
        wrapped = "\n".join(["- `New` Padding word." + " word" * 12] + ["  and more" * 8] * 8)
        problems = lint(build(**{"Vehicles and mobile bases": wrapped}))
        self.assertEqual(len(problems), 1)
        self.assertIn("against a budget of", problems[0])

    def test_counts_entries_against_the_section_budget(self) -> None:
        crowded = "\n".join(f"- `New` Entry number {index}." for index in range(30))
        self.assertIn("the budget is", "\n".join(lint(build(**{"Modding and scripting": crowded}))))

    def test_rejects_a_missing_final_newline(self) -> None:
        self.assertIn("exactly one newline", "\n".join(lint(build().rstrip("\n"))))

    def test_checked_in_patchnotes_conform(self) -> None:
        text = (ROOT / PATCHNOTES_PATH).read_text(encoding="utf-8")
        self.assertEqual(lint(text), [])


if __name__ == "__main__":
    unittest.main()
