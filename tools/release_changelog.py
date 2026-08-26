#!/usr/bin/env python3

"""Deterministic, reviewable release changelog tooling for the additive fork."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import unicodedata
import zipfile
from typing import Any, Iterable


ROOT = pathlib.Path(__file__).resolve().parents[1]
CHANGE_DIR = pathlib.Path("changelog/changes")
RELEASE_DIR = pathlib.Path("changelog/releases")
RELEASE_DOC_DIR = pathlib.Path("doc/releases")
INDEX_PATH = RELEASE_DIR / "index.json"
REPOSITORY = "asketmc/cdda-asketmc"
REPOSITORY_URL = f"https://github.com/{REPOSITORY}"

CATEGORY_ORDER = (
    "Features",
    "Content",
    "Interface",
    "Mods",
    "Balance",
    "Bugfixes",
    "Performance",
    "Build",
    "Infrastructure",
    "I18N",
)
AUDIENCE_ORDER = ("players", "maintainers")
COMPATIBILITY = {
    "save-compatible": "Compatible with existing 0.G additive saves.",
    "new-world-recommended": "A new world is recommended to receive the complete change.",
    "new-world-required": "A new world is required.",
    "not-applicable": "Not applicable to save data.",
    "unknown": "Save impact has not been established.",
}
TAG_RE = re.compile(r"v0\.G-additive-\d{4}\.\d{2}\.\d{2}(?:\.\d+)?\Z")
FRAGMENT_RE = re.compile(r"pr-([1-9]\d*)\.json\Z")
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
HASH_RE = re.compile(r"[0-9a-f]{64}\Z")
ENTRY_ID_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
MERGE_PR_RE = re.compile(r"Merge pull request #([1-9]\d*) from \S+\Z")
SQUASH_PR_RE = re.compile(r".+ \(#([1-9]\d*)\)\Z")
DEPENDABOT_RE = re.compile(r"Bump (.+) from (\S+) to (\S+) \(#([1-9]\d*)\)\Z")
DEPENDABOT_PR_TITLE_RE = re.compile(r"Bump (.+) from (\S+) to (\S+)\Z")
DEPENDABOT_EMAIL_RE = re.compile(
    r"(?:49699333\+)?dependabot\[bot\]@users\.noreply\.github\.com\Z"
)


class ChangelogError(ValueError):
    """A fail-closed release changelog contract violation."""


def _reject_constant(value: str) -> None:
    raise ChangelogError(f"non-finite JSON number is forbidden: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ChangelogError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_json_bytes(data: bytes, source: str) -> Any:
    if data.startswith(b"\xef\xbb\xbf"):
        raise ChangelogError(f"{source}: UTF-8 BOM is forbidden")
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ChangelogError(f"{source}: invalid UTF-8") from error
    try:
        return json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as error:
        raise ChangelogError(f"{source}: invalid JSON: {error.msg}") from error


def load_json(path: pathlib.Path) -> Any:
    try:
        return parse_json_bytes(path.read_bytes(), str(path))
    except FileNotFoundError as error:
        raise ChangelogError(f"missing required file: {path}") from error


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def object_hash(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def atomic_write(path: pathlib.Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False
    ) as temporary:
        temporary.write(data)
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = pathlib.Path(temporary.name)
    try:
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def require_object(value: Any, source: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ChangelogError(f"{source}: expected a JSON object")
    return value


def require_keys(
    value: dict[str, Any], required: set[str], optional: set[str], source: str
) -> None:
    missing = sorted(required - value.keys())
    unknown = sorted(value.keys() - required - optional)
    if missing:
        raise ChangelogError(f"{source}: missing keys: {', '.join(missing)}")
    if unknown:
        raise ChangelogError(f"{source}: unknown keys: {', '.join(unknown)}")


def require_int(value: Any, source: str, minimum: int = 1) -> int:
    if type(value) is not int or value < minimum:
        raise ChangelogError(f"{source}: expected an integer >= {minimum}")
    return value


def require_bool(value: Any, source: str) -> bool:
    if type(value) is not bool:
        raise ChangelogError(f"{source}: expected a boolean")
    return value


def require_text(value: Any, source: str, maximum: int = 400) -> str:
    if not isinstance(value, str):
        raise ChangelogError(f"{source}: expected text")
    if not value or value != value.strip():
        raise ChangelogError(f"{source}: text must be non-empty and trimmed")
    if len(value) > maximum:
        raise ChangelogError(f"{source}: text exceeds {maximum} characters")
    if unicodedata.normalize("NFC", value) != value:
        raise ChangelogError(f"{source}: text must use NFC Unicode normalization")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ChangelogError(f"{source}: controls and line breaks are forbidden")
    return value


def require_text_list(value: Any, source: str, maximum_items: int = 20) -> list[str]:
    if not isinstance(value, list):
        raise ChangelogError(f"{source}: expected an array")
    if len(value) > maximum_items:
        raise ChangelogError(f"{source}: too many entries")
    return [require_text(item, f"{source}[{index}]") for index, item in enumerate(value)]


def validate_entry(value: Any, source: str) -> dict[str, Any]:
    entry = require_object(value, source)
    require_keys(
        entry,
        {"id", "category", "audience", "summary", "compatibility"},
        {"details", "known_limits"},
        source,
    )
    entry_id = require_text(entry["id"], f"{source}.id", 80)
    if not ENTRY_ID_RE.fullmatch(entry_id):
        raise ChangelogError(f"{source}.id: expected lowercase kebab-case")
    category = require_text(entry["category"], f"{source}.category", 40)
    if category not in CATEGORY_ORDER:
        raise ChangelogError(f"{source}.category: unsupported category {category!r}")
    audience = require_text(entry["audience"], f"{source}.audience", 20)
    if audience not in AUDIENCE_ORDER:
        raise ChangelogError(f"{source}.audience: unsupported audience {audience!r}")
    require_text(entry["summary"], f"{source}.summary", 240)
    compatibility = require_text(entry["compatibility"], f"{source}.compatibility", 40)
    if compatibility not in COMPATIBILITY:
        raise ChangelogError(
            f"{source}.compatibility: unsupported value {compatibility!r}"
        )
    if "details" in entry:
        require_text_list(entry["details"], f"{source}.details", 12)
        if not entry["details"]:
            raise ChangelogError(f"{source}.details: empty arrays are forbidden")
    if "known_limits" in entry:
        require_text_list(entry["known_limits"], f"{source}.known_limits", 8)
        if not entry["known_limits"]:
            raise ChangelogError(f"{source}.known_limits: empty arrays are forbidden")
    return entry


def validate_fragment(value: Any, source: str, expected_pr: int | None = None) -> dict[str, Any]:
    fragment = require_object(value, source)
    require_keys(fragment, {"schema", "pr"}, {"entries", "skip"}, source)
    if fragment["schema"] != 1 or type(fragment["schema"]) is not int:
        raise ChangelogError(f"{source}.schema: expected integer 1")
    pr = require_int(fragment["pr"], f"{source}.pr")
    if expected_pr is not None and pr != expected_pr:
        raise ChangelogError(f"{source}: filename PR {expected_pr} does not match JSON PR {pr}")
    has_entries = "entries" in fragment
    has_skip = "skip" in fragment
    if has_entries == has_skip:
        raise ChangelogError(f"{source}: exactly one of entries or skip is required")
    if has_entries:
        entries = fragment["entries"]
        if not isinstance(entries, list) or not entries:
            raise ChangelogError(f"{source}.entries: expected a non-empty array")
        ids: set[str] = set()
        for index, entry_value in enumerate(entries):
            entry = validate_entry(entry_value, f"{source}.entries[{index}]")
            if entry["id"] in ids:
                raise ChangelogError(f"{source}: duplicate entry id {entry['id']!r}")
            ids.add(entry["id"])
    else:
        skip = require_object(fragment["skip"], f"{source}.skip")
        require_keys(skip, {"reason"}, set(), f"{source}.skip")
        require_text(skip["reason"], f"{source}.skip.reason", 240)
    return fragment


def load_fragments(root: pathlib.Path) -> dict[int, dict[str, Any]]:
    directory = root / CHANGE_DIR
    if not directory.is_dir():
        raise ChangelogError(f"missing changelog fragment directory: {directory}")
    result: dict[int, dict[str, Any]] = {}
    for path in sorted(directory.glob("*.json"), key=lambda item: item.name):
        match = FRAGMENT_RE.fullmatch(path.name)
        if not match:
            raise ChangelogError(f"invalid fragment filename: {path.relative_to(root)}")
        pr = int(match.group(1))
        fragment = validate_fragment(load_json(path), str(path.relative_to(root)), pr)
        if pr in result:
            raise ChangelogError(f"duplicate fragment for PR #{pr}")
        result[pr] = fragment
    if not result:
        raise ChangelogError("at least one changelog fragment is required")
    return result


def validate_release_change(value: Any, source: str) -> dict[str, Any]:
    change = require_object(value, source)
    require_keys(change, {"pr"}, {"fragment_sha256", "automatic"}, source)
    require_int(change["pr"], f"{source}.pr")
    has_fragment = "fragment_sha256" in change
    has_automatic = "automatic" in change
    if has_fragment == has_automatic:
        raise ChangelogError(
            f"{source}: exactly one of fragment_sha256 or automatic is required"
        )
    if has_fragment:
        digest = require_text(change["fragment_sha256"], f"{source}.fragment_sha256", 64)
        if not HASH_RE.fullmatch(digest):
            raise ChangelogError(f"{source}.fragment_sha256: expected a lowercase SHA-256")
    else:
        validate_entry(change["automatic"], f"{source}.automatic")
    return change


def validate_release(value: Any, source: str) -> dict[str, Any]:
    release = require_object(value, source)
    require_keys(
        release,
        {
            "schema",
            "tag",
            "title",
            "date",
            "previous_release",
            "baseline",
            "changes",
            "baseline_entries",
            "known_limits",
            "validation",
        },
        set(),
        source,
    )
    if release["schema"] != 1 or type(release["schema"]) is not int:
        raise ChangelogError(f"{source}.schema: expected integer 1")
    tag = require_text(release["tag"], f"{source}.tag", 80)
    if not TAG_RE.fullmatch(tag):
        raise ChangelogError(f"{source}.tag: unsupported release tag")
    require_text(release["title"], f"{source}.title", 120)
    date_text = require_text(release["date"], f"{source}.date", 10)
    try:
        parsed_date = dt.date.fromisoformat(date_text)
    except ValueError as error:
        raise ChangelogError(f"{source}.date: expected YYYY-MM-DD") from error
    if parsed_date.isoformat() != date_text:
        raise ChangelogError(f"{source}.date: expected canonical YYYY-MM-DD")
    baseline = require_bool(release["baseline"], f"{source}.baseline")
    previous = release["previous_release"]
    if baseline:
        if previous is not None:
            raise ChangelogError(f"{source}: a baseline release must have previous_release null")
    else:
        previous = require_text(previous, f"{source}.previous_release", 80)
        if not TAG_RE.fullmatch(previous):
            raise ChangelogError(f"{source}.previous_release: unsupported release tag")
    changes = release["changes"]
    if not isinstance(changes, list):
        raise ChangelogError(f"{source}.changes: expected an array")
    if not changes and not baseline:
        raise ChangelogError(f"{source}.changes: a delta release cannot be empty")
    seen_prs: set[int] = set()
    for index, change_value in enumerate(changes):
        change = validate_release_change(change_value, f"{source}.changes[{index}]")
        if change["pr"] in seen_prs:
            raise ChangelogError(f"{source}: duplicate PR #{change['pr']}")
        seen_prs.add(change["pr"])
    baseline_entries = release["baseline_entries"]
    if not isinstance(baseline_entries, list):
        raise ChangelogError(f"{source}.baseline_entries: expected an array")
    if baseline and not baseline_entries:
        raise ChangelogError(f"{source}.baseline_entries: baseline snapshot cannot be empty")
    if not baseline and baseline_entries:
        raise ChangelogError(f"{source}.baseline_entries: only the baseline may use these")
    ids: set[str] = set()
    for index, entry_value in enumerate(baseline_entries):
        entry = validate_entry(entry_value, f"{source}.baseline_entries[{index}]")
        if entry["id"] in ids:
            raise ChangelogError(f"{source}: duplicate baseline entry id {entry['id']!r}")
        ids.add(entry["id"])
    require_text_list(release["known_limits"], f"{source}.known_limits", 20)
    validation = require_text_list(release["validation"], f"{source}.validation", 20)
    if not validation:
        raise ChangelogError(f"{source}.validation: at least one statement is required")
    return release


def load_release_index(root: pathlib.Path) -> list[str]:
    path = root / INDEX_PATH
    index = require_object(load_json(path), str(path.relative_to(root)))
    require_keys(index, {"schema", "releases"}, set(), str(path.relative_to(root)))
    if index["schema"] != 1 or type(index["schema"]) is not int:
        raise ChangelogError(f"{path.relative_to(root)}.schema: expected integer 1")
    releases = index["releases"]
    if not isinstance(releases, list) or not releases:
        raise ChangelogError(f"{path.relative_to(root)}.releases: expected a non-empty array")
    tags = [require_text(tag, f"{path.relative_to(root)}.releases[{i}]", 80) for i, tag in enumerate(releases)]
    if len(tags) != len(set(tags)):
        raise ChangelogError(f"{path.relative_to(root)}: duplicate release tags")
    if any(not TAG_RE.fullmatch(tag) for tag in tags):
        raise ChangelogError(f"{path.relative_to(root)}: unsupported release tag")
    return tags


def load_releases(root: pathlib.Path) -> tuple[list[str], dict[str, dict[str, Any]]]:
    tags = load_release_index(root)
    directory = root / RELEASE_DIR
    manifest_paths = sorted(
        path for path in directory.glob("*.json") if path.name != INDEX_PATH.name
    )
    expected_names = {f"{tag}.json" for tag in tags}
    actual_names = {path.name for path in manifest_paths}
    if expected_names != actual_names:
        missing = sorted(expected_names - actual_names)
        extra = sorted(actual_names - expected_names)
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if extra:
            details.append(f"unindexed: {', '.join(extra)}")
        raise ChangelogError("release manifest/index mismatch (" + "; ".join(details) + ")")
    releases: dict[str, dict[str, Any]] = {}
    for path in manifest_paths:
        release = validate_release(load_json(path), str(path.relative_to(root)))
        if path.name != f"{release['tag']}.json":
            raise ChangelogError(f"{path.relative_to(root)}: filename does not match tag")
        releases[release["tag"]] = release
    for index, tag in enumerate(tags):
        release = releases[tag]
        expected_previous = tags[index + 1] if index + 1 < len(tags) else None
        if release["previous_release"] != expected_previous:
            raise ChangelogError(
                f"{tag}: previous_release must be {expected_previous!r} to match index order"
            )
        if release["baseline"] != (index == len(tags) - 1):
            raise ChangelogError(f"{tag}: only the oldest indexed release may be baseline")
        if index + 1 < len(tags) and release["date"] < releases[tags[index + 1]]["date"]:
            raise ChangelogError(f"{tag}: release dates are not newest-first")
    return tags, releases


def verify_release_fragment_links(
    tags: list[str], releases: dict[str, dict[str, Any]], fragments: dict[int, dict[str, Any]]
) -> None:
    used_prs: set[int] = set()
    for tag in reversed(tags):
        release = releases[tag]
        for change in release["changes"]:
            pr = change["pr"]
            if pr in used_prs:
                raise ChangelogError(f"PR #{pr} appears in more than one release")
            used_prs.add(pr)
            if "fragment_sha256" in change:
                if pr not in fragments:
                    raise ChangelogError(f"{tag}: missing fragment for PR #{pr}")
                actual = object_hash(fragments[pr])
                if actual != change["fragment_sha256"]:
                    raise ChangelogError(
                        f"{tag}: fragment hash mismatch for PR #{pr}; published history is immutable"
                    )


def markdown_escape(text: str) -> str:
    result = text.replace("\\", "\\\\")
    for character in "`*_[<>]":
        result = result.replace(character, "\\" + character)
    return result


def entries_for_release(
    release: dict[str, Any], fragments: dict[int, dict[str, Any]]
) -> list[tuple[dict[str, Any], int | None]]:
    entries: list[tuple[dict[str, Any], int | None]] = [
        (entry, None) for entry in release["baseline_entries"]
    ]
    for change in release["changes"]:
        pr = change["pr"]
        if "automatic" in change:
            entries.append((change["automatic"], pr))
            continue
        fragment = fragments[pr]
        for entry in fragment.get("entries", []):
            entries.append((entry, pr))
    return entries


def _render_entry(entry: dict[str, Any], pr: int | None) -> list[str]:
    source = ""
    if pr is not None:
        source = f" ([PR #{pr}]({REPOSITORY_URL}/pull/{pr}))"
    lines = [f"- {markdown_escape(entry['summary'])}{source}"]
    for detail in entry.get("details", []):
        lines.append(f"  - {markdown_escape(detail)}")
    if entry["audience"] == "players":
        lines.append(f"  - Save compatibility: {COMPATIBILITY[entry['compatibility']]}")
    for known_limit in entry.get("known_limits", []):
        lines.append(f"  - Known limit: {markdown_escape(known_limit)}")
    return lines


def render_release(release: dict[str, Any], fragments: dict[int, dict[str, Any]]) -> str:
    lines = [f"# {release['title']}", "", f"Released: {release['date']}", ""]
    if release["baseline"]:
        lines.extend(
            [
                "This is the first release in the strict changelog chain. It records the fork state at adoption and the pull requests merged into that build.",
                "",
            ]
        )
    else:
        previous = release["previous_release"]
        lines.extend(
            [
                f"Changes since [{previous}]({REPOSITORY_URL}/releases/tag/{previous}).",
                "",
            ]
        )
    lines.extend(
        [
            f"For the cumulative fork overview, see [PATCHNOTES_ADDITIVE_0G.md]({REPOSITORY_URL}/blob/main/PATCHNOTES_ADDITIVE_0G.md).",
            "",
        ]
    )
    all_entries = entries_for_release(release, fragments)
    for audience in AUDIENCE_ORDER:
        audience_entries = [(entry, pr) for entry, pr in all_entries if entry["audience"] == audience]
        if not audience_entries:
            continue
        lines.extend(
            [
                "## Player changes" if audience == "players" else "## Build and maintainer changes",
                "",
            ]
        )
        for category in CATEGORY_ORDER:
            category_entries = [
                (entry, pr) for entry, pr in audience_entries if entry["category"] == category
            ]
            if not category_entries:
                continue
            lines.extend([f"### {category}", ""])
            for entry, pr in category_entries:
                lines.extend(_render_entry(entry, pr))
            lines.append("")
    skipped = [
        change["pr"]
        for change in release["changes"]
        if "fragment_sha256" in change and "skip" in fragments[change["pr"]]
    ]
    if skipped:
        lines.extend(["## Intentionally omitted", ""])
        for pr in skipped:
            reason = markdown_escape(fragments[pr]["skip"]["reason"])
            lines.append(f"- [PR #{pr}]({REPOSITORY_URL}/pull/{pr}): {reason}")
        lines.append("")
    if release["known_limits"]:
        lines.extend(["## Known limits", ""])
        lines.extend(f"- {markdown_escape(item)}" for item in release["known_limits"])
        lines.append("")
    lines.extend(["## Validation recorded for this release", ""])
    lines.extend(f"- {markdown_escape(item)}" for item in release["validation"])
    lines.append("")
    return "\n".join(lines)


def render_changelog(
    tags: list[str], releases: dict[str, dict[str, Any]], fragments: dict[int, dict[str, Any]]
) -> str:
    lines = [
        "# CDDA 0.G Additive release changelog",
        "",
        "This file is generated from reviewed changelog fragments and immutable release manifests. Do not edit it by hand.",
        "",
        "- The release sections below are deltas, newest first.",
        "- [PATCHNOTES_ADDITIVE_0G.md](PATCHNOTES_ADDITIVE_0G.md) remains the cumulative, curated overview of the fork.",
        "- [Release process](doc/RELEASING.md) explains how a release is prepared and verified.",
        "",
    ]
    for tag in tags:
        rendered = render_release(releases[tag], fragments).rstrip("\n").splitlines()
        for line in rendered:
            if line.startswith("#"):
                line = "#" + line
            lines.append(line)
        lines.append("")
    return "\n".join(lines)


def expected_generated_files(
    root: pathlib.Path,
    tags: list[str],
    releases: dict[str, dict[str, Any]],
    fragments: dict[int, dict[str, Any]],
) -> dict[pathlib.Path, bytes]:
    result = {
        root / "CHANGELOG.md": render_changelog(tags, releases, fragments).encode("utf-8")
    }
    for tag in tags:
        result[root / RELEASE_DOC_DIR / f"{tag}.md"] = render_release(
            releases[tag], fragments
        ).encode("utf-8")
    return result


def lint_repository(root: pathlib.Path, check_generated: bool = False) -> tuple[list[str], dict[str, dict[str, Any]], dict[int, dict[str, Any]]]:
    fragments = load_fragments(root)
    tags, releases = load_releases(root)
    verify_release_fragment_links(tags, releases, fragments)
    if check_generated:
        for path, expected in expected_generated_files(root, tags, releases, fragments).items():
            try:
                actual = path.read_bytes()
            except FileNotFoundError as error:
                raise ChangelogError(f"generated file is missing: {path.relative_to(root)}") from error
            if actual != expected:
                raise ChangelogError(
                    f"generated file is stale: {path.relative_to(root)}; run release_changelog.py render-all"
                )
    return tags, releases, fragments


def render_all(root: pathlib.Path) -> None:
    tags, releases, fragments = lint_repository(root)
    for path, data in expected_generated_files(root, tags, releases, fragments).items():
        atomic_write(path, data)


def git(root: pathlib.Path, arguments: list[str], check: bool = True) -> str:
    environment = os.environ.copy()
    environment.update({"LC_ALL": "C", "LANG": "C", "TZ": "UTC"})
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        env=environment,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="strict",
        shell=False,
    )
    if check and result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise ChangelogError(f"git {' '.join(arguments)} failed: {message}")
    return result.stdout


def resolve_commit(root: pathlib.Path, reference: str) -> str:
    commit = git(root, ["rev-parse", "--verify", f"{reference}^{{commit}}"], check=True).strip()
    if not SHA_RE.fullmatch(commit):
        raise ChangelogError(f"{reference}: git did not resolve a full lowercase commit SHA")
    return commit


def first_parent_integrations(
    root: pathlib.Path, start_exclusive: str, end_inclusive: str
) -> list[dict[str, Any]]:
    start = resolve_commit(root, start_exclusive)
    end = resolve_commit(root, end_inclusive)
    if start == end:
        return []
    lines = git(
        root,
        [
            "log",
            "--first-parent",
            "--reverse",
            "--format=%H%x09%P%x09%an%x09%ae%x09%s",
            f"{start}..{end}",
        ],
    ).splitlines()
    if not lines:
        raise ChangelogError(f"{start_exclusive} is not on the first-parent chain of {end_inclusive}")
    previous = start
    integrations: list[dict[str, Any]] = []
    for line in lines:
        parts = line.split("\t", 4)
        if len(parts) != 5:
            raise ChangelogError("unexpected git log record")
        commit, parent_text, author_name, author_email, subject = parts
        parents = parent_text.split()
        if not parents or parents[0] != previous:
            raise ChangelogError(
                f"{start_exclusive} is not on the exact first-parent chain of {end_inclusive}"
            )
        merge_match = MERGE_PR_RE.fullmatch(subject)
        squash_match = SQUASH_PR_RE.fullmatch(subject)
        if merge_match and len(parents) == 2:
            pr = int(merge_match.group(1))
            style = "merge"
        elif squash_match and len(parents) == 1:
            pr = int(squash_match.group(1))
            style = "squash"
        else:
            raise ChangelogError(
                f"{commit}: first-parent commit is not a recognized GitHub PR integration: {subject!r}"
            )
        if any(item["pr"] == pr for item in integrations):
            raise ChangelogError(
                f"{commit}: PR #{pr} appears more than once; rebase merges are unsupported"
            )
        integrations.append(
            {
                "commit": commit,
                "parents": parents,
                "subject": subject,
                "author_name": author_name,
                "author_email": author_email,
                "pr": pr,
                "style": style,
            }
        )
        previous = commit
    if previous != end:
        raise ChangelogError("first-parent enumeration did not reach the target commit")
    return integrations


def validate_tag(root: pathlib.Path, tag: str, expected_commit: str | None = None) -> None:
    tags, releases, fragments = lint_repository(root, check_generated=True)
    if tag not in releases:
        raise ChangelogError(f"no indexed release manifest for {tag}")
    release = releases[tag]
    target = resolve_commit(root, f"refs/tags/{tag}")
    if expected_commit is not None:
        if not SHA_RE.fullmatch(expected_commit):
            raise ChangelogError("--expected-commit must be a full lowercase commit SHA")
        if target != expected_commit:
            raise ChangelogError(f"tag {tag} resolves to {target}, expected {expected_commit}")
    if release["baseline"]:
        return
    integrations = first_parent_integrations(root, release["previous_release"], target)
    actual_prs = [item["pr"] for item in integrations]
    expected_prs = [item["pr"] for item in release["changes"]]
    if actual_prs != expected_prs:
        raise ChangelogError(
            f"{tag}: manifest PR order {expected_prs} does not cover exact first-parent range {actual_prs}"
        )
    verify_automatic_integrations(release["changes"], integrations, fragments, tag)
    verify_release_fragment_links(tags, releases, fragments)


def _git_path_exists(root: pathlib.Path, revision: str, path: str) -> bool:
    result = git(root, ["ls-tree", "--name-only", revision, "--", path], check=True)
    return path in result.splitlines()


def _git_json(root: pathlib.Path, revision: str, path: str) -> Any:
    data = git(root, ["show", f"{revision}:{path}"]).encode("utf-8")
    return parse_json_bytes(data, f"{revision}:{path}")


def _name_status_diff(
    root: pathlib.Path, base: str, head: str, paths: Iterable[str]
) -> list[tuple[str, str]]:
    output = git(
        root,
        ["diff", "--name-status", "--no-renames", base, head, "--", *paths],
    )
    records: list[tuple[str, str]] = []
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) != 2:
            raise ChangelogError(f"unexpected git name-status record: {line!r}")
        records.append((parts[0], parts[1]))
    return records


def _check_release_history_diff(
    root: pathlib.Path, base: str, head: str, pr: int, bootstrap: bool
) -> None:
    records = _name_status_diff(
        root,
        base,
        head,
        (RELEASE_DIR.as_posix(), RELEASE_DOC_DIR.as_posix(), "CHANGELOG.md"),
    )
    if bootstrap:
        for status, path in records:
            if status != "A":
                raise ChangelogError(
                    f"bootstrap release history may only add files, found {status} {path}"
                )
        if records:
            _verify_generated_checkout(root, head)
        return
    if not records:
        return

    release_records = [record for record in records if record[1].startswith(f"{RELEASE_DIR.as_posix()}/")]
    if not release_records:
        _verify_generated_rewrites(root, head, records)
        return
    manifest_additions = [
        path
        for status, path in release_records
        if status == "A" and path != INDEX_PATH.as_posix()
    ]
    expected_release_records = {
        ("M", INDEX_PATH.as_posix()),
        *(("A", path) for path in manifest_additions),
    }
    if len(manifest_additions) != 1 or set(release_records) != expected_release_records:
        raise ChangelogError(
            "published release manifests are immutable; a release PR may only add one manifest and update index.json"
        )
    manifest_path = manifest_additions[0]
    tag = pathlib.PurePosixPath(manifest_path).stem
    if not TAG_RE.fullmatch(tag):
        raise ChangelogError(f"invalid added release manifest name: {manifest_path}")
    required_other = {
        ("A", f"{RELEASE_DOC_DIR.as_posix()}/{tag}.md"),
        ("M", "CHANGELOG.md"),
    }
    other_records = set(records) - set(release_records)
    generated_paths = _verify_generated_checkout(root, head)
    allowed_historical_docs = {
        ("M", path)
        for path in generated_paths
        if path.startswith(f"{RELEASE_DOC_DIR.as_posix()}/")
    }
    if not required_other.issubset(other_records) or not other_records.issubset(
        required_other | allowed_historical_docs
    ):
        raise ChangelogError(
            "release PR must add its generated release document, update CHANGELOG.md, "
            f"and may only regenerate indexed historical documents; found {sorted(other_records)}"
        )
    release = validate_release(
        _git_json(root, head, manifest_path), f"{head}:{manifest_path}"
    )
    if release["tag"] != tag:
        raise ChangelogError(f"{manifest_path}: embedded tag does not match filename")
    index = require_object(
        _git_json(root, head, INDEX_PATH.as_posix()), f"{head}:{INDEX_PATH.as_posix()}"
    )
    require_keys(index, {"schema", "releases"}, set(), f"{head}:{INDEX_PATH.as_posix()}")
    if not isinstance(index["releases"], list) or not index["releases"] or index["releases"][0] != tag:
        raise ChangelogError(f"{tag}: new release must be the first index entry")
    expected_prs = [item["pr"] for item in release["changes"]]
    integrations = first_parent_integrations(root, release["previous_release"], base)
    actual_prs = [item["pr"] for item in integrations]
    actual_prs.append(pr)
    if expected_prs != actual_prs:
        raise ChangelogError(
            f"{tag}: release PR coverage {expected_prs} must equal current main range plus PR #{pr}: {actual_prs}"
        )
    verify_automatic_integrations(
        release["changes"][:-1],
        integrations,
        load_fragments(root),
        tag,
    )
    if "automatic" in release["changes"][-1]:
        raise ChangelogError(
            f"{tag}: release-preparation PR #{pr} must use its reviewed fragment"
        )


def _generated_paths_from_checkout(root: pathlib.Path) -> set[str]:
    tags, releases, fragments = lint_repository(root, check_generated=True)
    return {
        path.relative_to(root).as_posix()
        for path in expected_generated_files(root, tags, releases, fragments)
    }


def _verify_generated_checkout(root: pathlib.Path, head: str) -> set[str]:
    if resolve_commit(root, "HEAD") != resolve_commit(root, head):
        raise ChangelogError("generated-file verification requires HEAD to match --head")
    return _generated_paths_from_checkout(root)


def _verify_generated_rewrites(
    root: pathlib.Path,
    head: str,
    records: list[tuple[str, str]],
) -> None:
    allowed = _verify_generated_checkout(root, head)
    invalid = [
        (status, path)
        for status, path in records
        if status != "M" or path not in allowed
    ]
    if invalid:
        raise ChangelogError(
            "renderer-only changes may only rewrite indexed generated files; "
            f"found {invalid}"
        )


def check_pr(
    root: pathlib.Path,
    base: str,
    head: str,
    pr: int,
    author: str,
    title: str | None = None,
) -> None:
    require_int(pr, "--pr")
    base_commit = resolve_commit(root, base)
    head_commit = resolve_commit(root, head)
    diff = git(
        root,
        ["diff", "--name-status", "--no-renames", base_commit, head_commit, "--", CHANGE_DIR.as_posix()],
    )
    records = [line.split("\t") for line in diff.splitlines() if line]
    for record in records:
        if len(record) != 2 or record[0] != "A":
            raise ChangelogError("existing changelog fragments are immutable; only additions are allowed")
    added = [record[1] for record in records]
    expected = f"{CHANGE_DIR.as_posix()}/pr-{pr}.json"
    bootstrap = not _git_path_exists(root, base_commit, CHANGE_DIR.as_posix())
    _check_release_history_diff(root, base_commit, head_commit, pr, bootstrap)
    dependabot = author == "dependabot[bot]"
    if bootstrap:
        if expected not in added:
            raise ChangelogError(f"bootstrap PR must add its own fragment: {expected}")
    elif dependabot and not added:
        if title is None or not _is_canonical_dependabot_title(title, pr):
            raise ChangelogError(
                f"Dependabot PR #{pr} without a fragment must use its canonical bump title"
            )
        return
    elif added != [expected]:
        raise ChangelogError(
            f"PR #{pr} must add exactly one fragment named {expected}; found {added}"
        )
    for path in added:
        match = FRAGMENT_RE.fullmatch(pathlib.PurePosixPath(path).name)
        if not match:
            raise ChangelogError(f"invalid fragment filename: {path}")
        fragment_pr = int(match.group(1))
        validate_fragment(_git_json(root, head_commit, path), f"{head_commit}:{path}", fragment_pr)


def check_main_update(root: pathlib.Path, base: str, head: str) -> None:
    integrations = first_parent_integrations(root, base, head)
    if len(integrations) != 1:
        raise ChangelogError(
            "main updates must contain exactly one recognized PR integration"
        )
    integration = integrations[0]
    author = "dependabot[bot]" if _is_dependabot_integration(integration) else "main-integration"
    check_pr(root, base, head, integration["pr"], author, integration["subject"])


def _automatic_dependabot_entry(subject: str, pr: int) -> dict[str, Any] | None:
    match = DEPENDABOT_RE.fullmatch(subject)
    if not match or int(match.group(4)) != pr:
        return None
    dependency, old, new, _ = match.groups()
    identifier = re.sub(r"[^a-z0-9]+", "-", dependency.lower()).strip("-")[:50]
    return {
        "id": f"update-{identifier}-{pr}",
        "category": "Infrastructure",
        "audience": "maintainers",
        "summary": f"Update {dependency} from {old} to {new}.",
        "compatibility": "not-applicable",
    }


def _is_canonical_dependabot_title(title: str, pr: int) -> bool:
    if _automatic_dependabot_entry(title, pr) is not None:
        return True
    return DEPENDABOT_PR_TITLE_RE.fullmatch(title) is not None


def _is_dependabot_integration(integration: dict[str, Any]) -> bool:
    return (
        integration.get("style") == "squash"
        and integration.get("author_name") == "dependabot[bot]"
        and isinstance(integration.get("author_email"), str)
        and DEPENDABOT_EMAIL_RE.fullmatch(integration["author_email"]) is not None
        and _automatic_dependabot_entry(integration["subject"], integration["pr"])
        is not None
    )


def verify_automatic_integrations(
    changes: list[dict[str, Any]],
    integrations: list[dict[str, Any]],
    fragments: dict[int, dict[str, Any]],
    source: str,
) -> None:
    if len(changes) != len(integrations):
        raise ChangelogError(f"{source}: integration/change count mismatch")
    for change, integration in zip(changes, integrations):
        if change["pr"] != integration["pr"]:
            raise ChangelogError(f"{source}: integration PR order mismatch")
        if "automatic" not in change:
            continue
        if change["pr"] in fragments:
            raise ChangelogError(
                f"{source}: automatic PR #{change['pr']} entry cannot replace its reviewed fragment"
            )
        expected = _automatic_dependabot_entry(integration["subject"], integration["pr"])
        if not _is_dependabot_integration(integration) or change["automatic"] != expected:
            raise ChangelogError(
                f"{source}: automatic PR #{change['pr']} entry is not the canonical Dependabot derivation"
            )


def prepare_release(
    root: pathlib.Path,
    tag: str,
    title: str,
    date_text: str,
    previous: str,
    target: str,
    release_pr: int,
) -> None:
    tags, releases, fragments = lint_repository(root, check_generated=True)
    if tag in releases or (root / RELEASE_DIR / f"{tag}.json").exists():
        raise ChangelogError(f"release already exists: {tag}")
    if previous != tags[0]:
        raise ChangelogError(f"previous release must be current index head {tags[0]}")
    if previous not in releases:
        raise ChangelogError(f"unknown previous release: {previous}")
    if release_pr not in fragments:
        raise ChangelogError(f"release preparation PR #{release_pr} needs its own fragment first")
    integrations = first_parent_integrations(root, previous, target)
    if release_pr in {item["pr"] for item in integrations}:
        raise ChangelogError("release preparation PR is already present in target history")
    changes = []
    for integration in integrations:
        pr = integration["pr"]
        if pr in fragments:
            changes.append({"pr": pr, "fragment_sha256": object_hash(fragments[pr])})
            continue
        automatic = _automatic_dependabot_entry(integration["subject"], pr)
        if automatic is None or not _is_dependabot_integration(integration):
            raise ChangelogError(
                f"PR #{pr} has no fragment and is not a deterministic Dependabot bump"
            )
        changes.append({"pr": pr, "automatic": automatic})
    changes.append(
        {"pr": release_pr, "fragment_sha256": object_hash(fragments[release_pr])}
    )
    release = {
        "schema": 1,
        "tag": tag,
        "title": title,
        "date": date_text,
        "previous_release": previous,
        "baseline": False,
        "changes": changes,
        "baseline_entries": [],
        "known_limits": [],
        "validation": [
            "The tag workflow must reproduce identical executable and ZIP hashes from two clean release builds.",
            "The exact staged archive must pass checksum, metadata, extraction, and --check-mods dda validation before publication.",
        ],
    }
    validate_release(release, tag)
    atomic_write(root / RELEASE_DIR / f"{tag}.json", canonical_json_bytes(release))
    atomic_write(
        root / INDEX_PATH,
        canonical_json_bytes({"schema": 1, "releases": [tag, *tags]}),
    )
    render_all(root)


def release_field(root: pathlib.Path, tag: str, field: str) -> str:
    _, releases, _ = lint_repository(root)
    if tag not in releases:
        raise ChangelogError(f"unknown release: {tag}")
    if field not in {"title", "previous_release", "date"}:
        raise ChangelogError(f"unsupported release field: {field}")
    value = releases[tag][field]
    if value is None:
        raise ChangelogError(f"{tag}.{field} is null")
    return str(value)


def build_metadata(
    root: pathlib.Path, tag: str, commit: str, notes: pathlib.Path, output: pathlib.Path
) -> None:
    _, releases, _ = lint_repository(root, check_generated=True)
    if tag not in releases:
        raise ChangelogError(f"unknown release: {tag}")
    if not SHA_RE.fullmatch(commit):
        raise ChangelogError("commit must be a full lowercase SHA")
    release = releases[tag]
    expected_notes = render_release(release, load_fragments(root)).encode("utf-8")
    actual_notes = notes.read_bytes()
    if actual_notes != expected_notes:
        raise ChangelogError("release notes do not match the reviewed manifest")
    source_path = root / RELEASE_DIR / f"{tag}.json"
    documents = {}
    for name, path in (
        ("CHANGELOG.md", root / "CHANGELOG.md"),
        ("PATCHNOTES_ADDITIVE_0G.md", root / "PATCHNOTES_ADDITIVE_0G.md"),
        ("RELEASE_NOTES.md", notes),
    ):
        documents[name] = sha256_file(path)
    metadata = {
        "schema": 1,
        "tag": tag,
        "title": release["title"],
        "commit": commit,
        "previous_release": release["previous_release"],
        "source_manifest_sha256": sha256_file(source_path),
        "documents": documents,
    }
    atomic_write(output, canonical_json_bytes(metadata))


def build_asset_manifest(
    root: pathlib.Path,
    tag: str,
    commit: str,
    archive: pathlib.Path,
    notes: pathlib.Path,
    build_manifest_path: pathlib.Path,
    metadata: pathlib.Path,
    output: pathlib.Path,
) -> None:
    _, releases, _ = lint_repository(root, check_generated=True)
    if tag not in releases:
        raise ChangelogError(f"unknown release: {tag}")
    if not SHA_RE.fullmatch(commit):
        raise ChangelogError("commit must be a full lowercase SHA")
    release = releases[tag]
    source_manifest_hash = sha256_file(root / RELEASE_DIR / f"{tag}.json")
    embedded = validate_runtime_metadata(load_json(metadata), str(metadata))
    if embedded["tag"] != tag or embedded["commit"] != commit:
        raise ChangelogError("release metadata tag/commit mismatch")
    if (
        embedded["title"] != release["title"]
        or embedded["previous_release"] != release["previous_release"]
        or embedded["source_manifest_sha256"] != source_manifest_hash
    ):
        raise ChangelogError("release metadata does not match the reviewed source manifest")
    assets = []
    for path in sorted((archive, build_manifest_path, notes), key=lambda item: item.name):
        assets.append(
            {"name": path.name, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)}
        )
    manifest = {
        "schema": 1,
        "tag": tag,
        "title": release["title"],
        "commit": commit,
        "previous_release": release["previous_release"],
        "source_manifest_sha256": source_manifest_hash,
        "embedded_metadata_sha256": sha256_file(metadata),
        "assets": assets,
    }
    validate_asset_manifest(manifest, str(output))
    atomic_write(output, canonical_json_bytes(manifest))


def validate_runtime_metadata(value: Any, source: str) -> dict[str, Any]:
    metadata = require_object(value, source)
    require_keys(
        metadata,
        {"schema", "tag", "title", "commit", "previous_release", "source_manifest_sha256", "documents"},
        set(),
        source,
    )
    if metadata["schema"] != 1 or type(metadata["schema"]) is not int:
        raise ChangelogError(f"{source}.schema: expected integer 1")
    if not TAG_RE.fullmatch(require_text(metadata["tag"], f"{source}.tag", 80)):
        raise ChangelogError(f"{source}.tag: invalid tag")
    require_text(metadata["title"], f"{source}.title", 120)
    if not SHA_RE.fullmatch(require_text(metadata["commit"], f"{source}.commit", 40)):
        raise ChangelogError(f"{source}.commit: invalid SHA")
    previous = metadata["previous_release"]
    if previous is not None and not TAG_RE.fullmatch(require_text(previous, f"{source}.previous_release", 80)):
        raise ChangelogError(f"{source}.previous_release: invalid tag")
    if not HASH_RE.fullmatch(require_text(metadata["source_manifest_sha256"], f"{source}.source_manifest_sha256", 64)):
        raise ChangelogError(f"{source}.source_manifest_sha256: invalid hash")
    documents = require_object(metadata["documents"], f"{source}.documents")
    expected_documents = {"CHANGELOG.md", "PATCHNOTES_ADDITIVE_0G.md", "RELEASE_NOTES.md"}
    require_keys(documents, expected_documents, set(), f"{source}.documents")
    for name, digest in documents.items():
        if not HASH_RE.fullmatch(require_text(digest, f"{source}.documents.{name}", 64)):
            raise ChangelogError(f"{source}.documents.{name}: invalid hash")
    return metadata


def validate_asset_manifest(value: Any, source: str) -> dict[str, Any]:
    manifest = require_object(value, source)
    require_keys(
        manifest,
        {"schema", "tag", "title", "commit", "previous_release", "source_manifest_sha256", "embedded_metadata_sha256", "assets"},
        set(),
        source,
    )
    if manifest["schema"] != 1 or type(manifest["schema"]) is not int:
        raise ChangelogError(f"{source}.schema: expected integer 1")
    if not TAG_RE.fullmatch(require_text(manifest["tag"], f"{source}.tag", 80)):
        raise ChangelogError(f"{source}.tag: invalid tag")
    require_text(manifest["title"], f"{source}.title", 120)
    if not SHA_RE.fullmatch(require_text(manifest["commit"], f"{source}.commit", 40)):
        raise ChangelogError(f"{source}.commit: invalid SHA")
    previous = manifest["previous_release"]
    if previous is not None and not TAG_RE.fullmatch(require_text(previous, f"{source}.previous_release", 80)):
        raise ChangelogError(f"{source}.previous_release: invalid tag")
    for key in ("source_manifest_sha256", "embedded_metadata_sha256"):
        if not HASH_RE.fullmatch(require_text(manifest[key], f"{source}.{key}", 64)):
            raise ChangelogError(f"{source}.{key}: invalid hash")
    assets = manifest["assets"]
    if not isinstance(assets, list) or len(assets) != 3:
        raise ChangelogError(f"{source}.assets: expected exactly three authenticated assets")
    names = []
    for index, asset_value in enumerate(assets):
        asset = require_object(asset_value, f"{source}.assets[{index}]")
        require_keys(asset, {"name", "size_bytes", "sha256"}, set(), f"{source}.assets[{index}]")
        name = require_text(asset["name"], f"{source}.assets[{index}].name", 180)
        if pathlib.PurePath(name).name != name or name in {".", ".."}:
            raise ChangelogError(f"{source}.assets[{index}].name: expected a basename")
        require_int(asset["size_bytes"], f"{source}.assets[{index}].size_bytes")
        if not HASH_RE.fullmatch(require_text(asset["sha256"], f"{source}.assets[{index}].sha256", 64)):
            raise ChangelogError(f"{source}.assets[{index}].sha256: invalid hash")
        names.append(name)
    if names != sorted(names) or len(names) != len(set(names)):
        raise ChangelogError(f"{source}.assets: names must be unique and sorted")
    if "BUILD_MANIFEST.txt" not in names or "RELEASE_NOTES.md" not in names:
        raise ChangelogError(f"{source}.assets: required document assets are missing")
    archives = [name for name in names if name.endswith(".zip")]
    if len(archives) != 1:
        raise ChangelogError(f"{source}.assets: expected exactly one ZIP")
    return manifest


def parse_checksum_file(path: pathlib.Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    result: dict[str, str] = {}
    for line in lines:
        match = re.fullmatch(r"([0-9a-f]{64})  ([^/\\]+)", line)
        if not match:
            raise ChangelogError(f"{path}: malformed checksum line")
        digest, name = match.groups()
        if name in result:
            raise ChangelogError(f"{path}: duplicate checksum name {name}")
        result[name] = digest
    if list(result) != sorted(result):
        raise ChangelogError(f"{path}: checksum entries must be sorted by filename")
    return result


def verify_assets(
    root: pathlib.Path,
    manifest_path: pathlib.Path,
    directory: pathlib.Path,
    expected_tag: str,
    expected_commit: str,
) -> None:
    directory = directory.resolve(strict=True)
    expected_manifest_path = directory / "RELEASE_MANIFEST.json"
    if manifest_path.resolve(strict=True) != expected_manifest_path:
        raise ChangelogError(
            "--manifest must name RELEASE_MANIFEST.json inside --directory"
        )
    manifest = validate_asset_manifest(load_json(manifest_path), str(manifest_path))
    if manifest["tag"] != expected_tag or manifest["commit"] != expected_commit:
        raise ChangelogError("release asset manifest tag/commit mismatch")
    tags, releases, fragments = lint_repository(root, check_generated=True)
    if expected_tag not in releases:
        raise ChangelogError(f"unknown release: {expected_tag}")
    release = releases[expected_tag]
    source_path = root / RELEASE_DIR / f"{expected_tag}.json"
    source_manifest_hash = sha256_file(source_path)
    if source_manifest_hash != manifest["source_manifest_sha256"]:
        raise ChangelogError("source release manifest hash mismatch")
    if (
        manifest["title"] != release["title"]
        or manifest["previous_release"] != release["previous_release"]
    ):
        raise ChangelogError("release asset manifest does not match reviewed release identity")
    expected_notes = render_release(release, fragments).encode("utf-8")
    expected_asset_names = set()
    for asset in manifest["assets"]:
        expected_asset_names.add(asset["name"])
        path = directory / asset["name"]
        if not path.is_file() or path.stat().st_size != asset["size_bytes"]:
            raise ChangelogError(f"asset is missing or has wrong size: {asset['name']}")
        if sha256_file(path) != asset["sha256"]:
            raise ChangelogError(f"asset hash mismatch: {asset['name']}")
    if (directory / "RELEASE_NOTES.md").read_bytes() != expected_notes:
        raise ChangelogError("external release notes differ from reviewed release notes")
    checksums = parse_checksum_file(directory / "SHA256SUMS.txt")
    checksum_names = expected_asset_names | {manifest_path.name}
    if set(checksums) != checksum_names:
        raise ChangelogError(
            f"SHA256SUMS.txt names {sorted(checksums)}, expected {sorted(checksum_names)}"
        )
    for name, digest in checksums.items():
        if sha256_file(directory / name) != digest:
            raise ChangelogError(f"SHA256SUMS.txt mismatch: {name}")
    archive_name = next(name for name in expected_asset_names if name.endswith(".zip"))
    with zipfile.ZipFile(directory / archive_name) as archive:
        required = {
            "BUILD_MANIFEST.txt",
            "CHANGELOG.md",
            "PATCHNOTES_ADDITIVE_0G.md",
            "RELEASE_METADATA.json",
            "RELEASE_NOTES.md",
        }
        if not required.issubset(archive.namelist()):
            raise ChangelogError("archive lacks release documentation")
        if archive.read("RELEASE_NOTES.md") != expected_notes:
            raise ChangelogError("embedded release notes differ from reviewed release notes")
        if archive.read("BUILD_MANIFEST.txt") != (directory / "BUILD_MANIFEST.txt").read_bytes():
            raise ChangelogError("embedded and external build manifests differ")
        metadata_bytes = archive.read("RELEASE_METADATA.json")
        if sha256_bytes(metadata_bytes) != manifest["embedded_metadata_sha256"]:
            raise ChangelogError("embedded release metadata hash mismatch")
        metadata = validate_runtime_metadata(
            parse_json_bytes(metadata_bytes, "archive:RELEASE_METADATA.json"),
            "archive:RELEASE_METADATA.json",
        )
        if metadata["tag"] != expected_tag or metadata["commit"] != expected_commit:
            raise ChangelogError("embedded release metadata tag/commit mismatch")
        if (
            metadata["title"] != release["title"]
            or metadata["previous_release"] != release["previous_release"]
            or metadata["source_manifest_sha256"] != source_manifest_hash
        ):
            raise ChangelogError("embedded release metadata does not match reviewed release identity")
        for name in ("CHANGELOG.md", "PATCHNOTES_ADDITIVE_0G.md", "RELEASE_NOTES.md"):
            if sha256_bytes(archive.read(name)) != metadata["documents"][name]:
                raise ChangelogError(f"embedded document hash mismatch: {name}")
        build_manifest_text = archive.read("BUILD_MANIFEST.txt").decode("utf-8", errors="strict")
        expected_receipts = {
            "release notes sha256": metadata["documents"]["RELEASE_NOTES.md"],
            "release metadata sha256": manifest["embedded_metadata_sha256"],
            "cumulative changelog sha256": metadata["documents"]["CHANGELOG.md"],
            "cumulative overview sha256": metadata["documents"]["PATCHNOTES_ADDITIVE_0G.md"],
        }
        build_lines = build_manifest_text.splitlines()
        for label, digest in expected_receipts.items():
            matches = [line for line in build_lines if line.startswith(f"{label}:")]
            if matches != [f"{label}: {digest}"]:
                raise ChangelogError(f"build manifest receipt mismatch: {label}")
    if tags[0] != expected_tag and releases[expected_tag]["baseline"] is False:
        # Historical release verification is allowed, but a newly tagged release must
        # always be represented in the chain. No lexicographic tag guessing occurs.
        pass


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, default=ROOT)
    subparsers = parser.add_subparsers(dest="command", required=True)

    lint = subparsers.add_parser("lint")
    lint.add_argument("--check-generated", action="store_true")

    subparsers.add_parser("render-all")

    render = subparsers.add_parser("render-release")
    render.add_argument("--tag", required=True)
    render.add_argument("--output", type=pathlib.Path, required=True)

    check = subparsers.add_parser("check-pr")
    check.add_argument("--base", required=True)
    check.add_argument("--head", required=True)
    check.add_argument("--pr", type=int, required=True)
    check.add_argument("--author", required=True)
    check.add_argument("--title")

    check_main = subparsers.add_parser("check-main")
    check_main.add_argument("--base", required=True)
    check_main.add_argument("--head", required=True)

    validate = subparsers.add_parser("validate-tag")
    validate.add_argument("--tag", required=True)
    validate.add_argument("--expected-commit")

    field = subparsers.add_parser("release-field")
    field.add_argument("--tag", required=True)
    field.add_argument("--field", required=True)

    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--tag", required=True)
    prepare.add_argument("--title", required=True)
    prepare.add_argument("--date", required=True)
    prepare.add_argument("--previous", required=True)
    prepare.add_argument("--target", default="origin/main")
    prepare.add_argument("--release-pr", type=int, required=True)

    metadata = subparsers.add_parser("build-metadata")
    metadata.add_argument("--tag", required=True)
    metadata.add_argument("--commit", required=True)
    metadata.add_argument("--notes", type=pathlib.Path, required=True)
    metadata.add_argument("--output", type=pathlib.Path, required=True)

    asset_manifest = subparsers.add_parser("build-asset-manifest")
    asset_manifest.add_argument("--tag", required=True)
    asset_manifest.add_argument("--commit", required=True)
    asset_manifest.add_argument("--archive", type=pathlib.Path, required=True)
    asset_manifest.add_argument("--notes", type=pathlib.Path, required=True)
    asset_manifest.add_argument("--build-manifest", type=pathlib.Path, required=True)
    asset_manifest.add_argument("--metadata", type=pathlib.Path, required=True)
    asset_manifest.add_argument("--output", type=pathlib.Path, required=True)

    verify = subparsers.add_parser("verify-assets")
    verify.add_argument("--manifest", type=pathlib.Path, required=True)
    verify.add_argument("--directory", type=pathlib.Path, required=True)
    verify.add_argument("--expected-tag", required=True)
    verify.add_argument("--expected-commit", required=True)

    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = args.root.resolve(strict=True)
    try:
        if args.command == "lint":
            lint_repository(root, args.check_generated)
        elif args.command == "render-all":
            render_all(root)
        elif args.command == "render-release":
            _, releases, fragments = lint_repository(root, check_generated=True)
            if args.tag not in releases:
                raise ChangelogError(f"unknown release: {args.tag}")
            atomic_write(args.output, render_release(releases[args.tag], fragments).encode("utf-8"))
        elif args.command == "check-pr":
            check_pr(root, args.base, args.head, args.pr, args.author, args.title)
        elif args.command == "check-main":
            check_main_update(root, args.base, args.head)
        elif args.command == "validate-tag":
            validate_tag(root, args.tag, args.expected_commit)
        elif args.command == "release-field":
            print(release_field(root, args.tag, args.field))
        elif args.command == "prepare":
            prepare_release(
                root,
                args.tag,
                args.title,
                args.date,
                args.previous,
                args.target,
                args.release_pr,
            )
        elif args.command == "build-metadata":
            build_metadata(root, args.tag, args.commit, args.notes, args.output)
        elif args.command == "build-asset-manifest":
            build_asset_manifest(
                root,
                args.tag,
                args.commit,
                args.archive,
                args.notes,
                args.build_manifest,
                args.metadata,
                args.output,
            )
        elif args.command == "verify-assets":
            verify_assets(
                root,
                args.manifest,
                args.directory,
                args.expected_tag,
                args.expected_commit,
            )
        else:  # pragma: no cover - argparse enforces this
            raise ChangelogError(f"unsupported command: {args.command}")
    except (ChangelogError, OSError, zipfile.BadZipFile) as error:
        print(f"release changelog error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
