#!/usr/bin/env python3

"""Enforce the editorial contract for PATCHNOTES_ADDITIVE_0G.md.

The fork keeps two complementary records, as described in doc/RELEASING.md:

* CHANGELOG.md is the generated, dated, per-release delta. Chronology, fork
  pull-request numbers, and release tags belong there and are produced from
  reviewed fragments in changelog/changes/.
* PATCHNOTES_ADDITIVE_0G.md is the evergreen catalogue of how this fork differs
  from vanilla 0.G. It answers "what do I get and why", not "when did it land".

This linter enforces the mechanical half of that split so the catalogue cannot
drift back into a second, hand-maintained changelog. Judgement calls stay in
AGENTS.md.
"""

from __future__ import annotations

import argparse
import pathlib
import re


PATCHNOTES_PATH = "PATCHNOTES_ADDITIVE_0G.md"

TITLE = "# CDDA 0.G Additive — what this fork changes"

# The ordered, closed set of top-level sections. Adding an area is a deliberate
# edit here plus a matching section in the document, which is the point: the
# taxonomy cannot grow silently one pull request at a time.
SECTIONS = (
    "How to read this file",
    "Vehicles and mobile bases",
    "Followers, NPCs, and camps",
    "Survival, crafting, and equipment",
    "Interface and quality of life",
    "Visuals, sound, and fonts",
    "Modding and scripting",
    "Optional mods",
    "Stability and save compatibility",
    "Known limits",
    "Non-goals",
)

# Sections whose bullets describe a difference from vanilla 0.G and therefore
# carry a tag. The remaining sections are prose or plain lists.
TAGGED_SECTIONS = frozenset(SECTIONS[1:8])

# The tag axis is "versus vanilla 0.G", not "versus my last commit". A defect
# this fork introduced and fixed before release was never `Fixed` for a reader,
# because they never had the broken version.
TAGS = ("New", "Improved", "Fixed")

# Budgets, not limits. They sit just above the document as written, so growth
# has to be paid for by merging or cutting an existing entry.
MAX_LINES = 450
MAX_LINE_LENGTH = 100
MAX_BULLETS_PER_SECTION = 20
MAX_BULLET_LENGTH = 480

HEADING_RE = re.compile(r"^(#+)\s*(.*)$")
BULLET_RE = re.compile(r"^(\s*)- (.*)$")
TAG_RE = re.compile(r"^`(\w+)` \S")
SHA_RE = re.compile(r"\b[0-9a-f]{8,40}\b")
DATE_RE = re.compile(r"\b\d{4}[-./]\d{2}[-./]\d{2}\b")
RELEASE_TAG_RE = re.compile(r"\bv0\.G-additive-[\d.]+")
FORK_PR_RE = re.compile(r"asketmc/cdda-asketmc/(?:pull|issues)/\d+")
BARE_PR_RE = re.compile(r"(?<![\w/])#\d+\b")
# Upstream provenance answers "is this proven code or homebrew", so a donor
# citation is welcome here. Only the fork's own numbering is redundant.
DONOR_RE = re.compile(r"\b(?:DDA|BN|TLG) #\d+\b")
TODO_RE = re.compile(r"\b(?:TODO|FIXME|XXX|WIP|HACK)\b")


def looks_like_commit_sha(text: str) -> bool:
    """Hex runs are only commit ids when they mix digits and letters.

    Ordinary English words such as "defaced" are pure hex characters, so a
    length test alone reports them.
    """
    return any(character.isdigit() for character in text) and any(
        character.isalpha() for character in text
    )


def check_line_hygiene(lines: list[str]) -> list[str]:
    problems = []
    for number, line in enumerate(lines, start=1):
        if line != line.rstrip():
            problems.append(f"{number}: trailing whitespace")
        if len(line) > MAX_LINE_LENGTH:
            problems.append(f"{number}: line exceeds {MAX_LINE_LENGTH} characters")
        if TODO_RE.search(line):
            problems.append(f"{number}: unfinished-work marker; this file ships to players")
        for match in SHA_RE.finditer(line):
            if looks_like_commit_sha(match.group()):
                problems.append(
                    f"{number}: commit id {match.group()[:12]}; provenance belongs in BACKPORTS.md"
                )
                break
        if DATE_RE.search(line) or RELEASE_TAG_RE.search(line):
            problems.append(f"{number}: dates and release tags belong in CHANGELOG.md")
        if FORK_PR_RE.search(line) or BARE_PR_RE.search(DONOR_RE.sub("", line)):
            problems.append(f"{number}: fork pull-request numbers belong in CHANGELOG.md")
    return problems


def check_headings(lines: list[str]) -> tuple[list[str], list[tuple[int, str]]]:
    """Validate the heading tree and return the located top-level sections."""
    problems = []
    located: list[tuple[int, str]] = []
    titles = 0
    for number, line in enumerate(lines, start=1):
        match = HEADING_RE.match(line)
        if not match:
            continue
        depth, text = len(match.group(1)), match.group(2)
        if depth == 1:
            titles += 1
            if number != 1:
                problems.append(f"{number}: the title must be the first line")
            if line.rstrip() != TITLE:
                problems.append(f"{number}: title must read {TITLE!r}")
        elif depth == 2:
            located.append((number, text))
        elif depth > 3:
            problems.append(f"{number}: headings deeper than ### are not allowed")
    if titles != 1:
        problems.append(f"1: expected exactly one title heading, found {titles}")

    found = [text for _, text in located]
    if found != list(SECTIONS):
        expected = "\n".join(f"    ## {name}" for name in SECTIONS)
        problems.append(
            "0: top-level sections must be exactly, and in this order:\n"
            + expected
            + "\n  found:\n"
            + "\n".join(f"    ## {name}" for name in found)
        )
    return problems, located


def section_of(number: int, located: list[tuple[int, str]]) -> str | None:
    current = None
    for start, name in located:
        if start <= number:
            current = name
        else:
            break
    return current


def collect_entries(
    lines: list[str], located: list[tuple[int, str]]
) -> tuple[list[str], list[tuple[int, str | None, str]]]:
    """Gather top-level bullets with their wrapped continuation lines.

    An entry is measured whole, so wrapping a paragraph across six lines does
    not smuggle it past the length budget.
    """
    problems = []
    entries: list[tuple[int, str | None, str]] = []
    start = 0
    section: str | None = None
    parts: list[str] = []

    def flush() -> None:
        nonlocal parts
        if parts:
            entries.append((start, section, " ".join(parts)))
            parts = []

    for number, line in enumerate(lines, start=1):
        match = BULLET_RE.match(line)
        if match:
            indent, body = match.group(1), match.group(2)
            if len(indent) % 2 or len(indent) > 2:
                problems.append(f"{number}: bullets nest at most one level, by two spaces")
            flush()
            if not indent:
                start, section, parts = number, section_of(number, located), [body]
            continue
        if not parts:
            continue
        if not line.strip() or HEADING_RE.match(line):
            flush()
            continue
        parts.append(line.strip())
    flush()
    return problems, entries


def check_bullets(lines: list[str], located: list[tuple[int, str]]) -> list[str]:
    problems, entries = collect_entries(lines, located)
    counts: dict[str, int] = {}
    for number, section, text in entries:
        if section is None:
            continue
        counts[section] = counts.get(section, 0) + 1
        if len(text) > MAX_BULLET_LENGTH:
            problems.append(
                f"{number}: entry is {len(text)} characters against a budget of"
                f" {MAX_BULLET_LENGTH}; split or cut it"
            )
        if section in TAGGED_SECTIONS:
            tag = TAG_RE.match(text)
            if not tag:
                allowed = ", ".join(f"`{name}`" for name in TAGS)
                problems.append(f"{number}: entry must open with one of {allowed}")
            elif tag.group(1) not in TAGS:
                problems.append(f"{number}: unknown tag `{tag.group(1)}`")
    for section, count in counts.items():
        if count > MAX_BULLETS_PER_SECTION:
            problems.append(
                f"0: section {section!r} has {count} entries; the budget is"
                f" {MAX_BULLETS_PER_SECTION}"
            )
    return problems


def lint(text: str) -> list[str]:
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    else:
        return ["0: file must end with exactly one newline"]

    problems = []
    if len(lines) > MAX_LINES:
        problems.append(f"0: file is {len(lines)} lines; the budget is {MAX_LINES}")
    problems.extend(check_line_hygiene(lines))
    heading_problems, located = check_headings(lines)
    problems.extend(heading_problems)
    problems.extend(check_bullets(lines, located))
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--path", default=PATCHNOTES_PATH)
    args = parser.parse_args()

    path = pathlib.Path(args.path)
    problems = lint(path.read_text(encoding="utf-8"))
    if not problems:
        print(f"{path}: ok")
        return 0
    for problem in problems:
        print(f"{path}:{problem}")
    print(f"{path}: {len(problems)} problems")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
