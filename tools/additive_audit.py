#!/usr/bin/env python3
"""Audit an additive CDDA backport against the exact 0.G source tree.

The audit treats ``data/json``, ``data/core``, and ``data/raw`` as loaded core
data and ``data/mods`` as a separate namespace.  Core top-level objects use
their loader identity where possible, including recipe result/id_suffix and
snippet category.  Unidentified objects are still protected by exact canonical
fingerprints, so deleting one cannot silently bypass the audit.  Existing
definitions may change only when their exact target fingerprint is present in
the manifest.
"""

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
import unittest


BASELINE_COMMIT = "d6ec466140839dd70c1a43671eb4a08b007695c2"
CORE_ROOTS = ("data/json", "data/core", "data/raw")
DEFAULT_MOD_METADATA_PATH = "data/mods/default.json"
IDENTITY_FIELDS = ("id", "abstract", "ident")
MANIFEST_IDENTITY_FIELDS = IDENTITY_FIELDS + (
    "result", "category", "mod_id"
)
ITEM_IDENTITY_NAMESPACE = "itype"
# DynamicDataLoader registers all of these through Item_factory, whose
# concrete templates and abstracts are keyed by a shared itype_id namespace.
ITEM_FACTORY_TYPES = frozenset({
    "AMMO", "ARMOR", "BATTERY", "BIONIC_ITEM", "BOOK", "COMESTIBLE",
    "ENGINE", "GENERIC", "GUN", "GUNMOD", "MAGAZINE", "PET_ARMOR",
    "TOOL", "TOOLMOD", "TOOL_ARMOR", "WHEEL"
})
WORKTREE_TARGET = "WORKTREE"
DONOR_REPOSITORY = "https://github.com/neonspectra/Cataclysm-2040.git"
EXPECTED_DONOR_IMPORTS = {
    "lockable_vehicle_doors": {
        "classification": "core",
        "donor_commit": "0ccfe3659c71d6a982290b2cd201737c6942b9bb"
    },
    "cbm_corpse_recovery": {
        "classification": "core",
        "donor_commit": "b6da28650d025ca47a99ab7db9e066b378c8e49e"
    },
    "useful_helicopters": {
        "classification": "optional_mod",
        "donor_commit": "dec27b76f7ab44a37c84971c63bf9062b1fd2503",
        "root": "data/mods/Useful_Helicopters_experimental",
        "mod_id": "useful_helicopters"
    }
}


class AuditFailure(Exception):
    """An input cannot be audited reliably."""


@dataclass(frozen=True, order=True)
class EntityKey:
    entity_type: str
    field: str
    value: str

    def label(self):
        return "{} {}={}".format(self.entity_type, self.field, self.value)


@dataclass(frozen=True)
class Occurrence:
    canonical: str
    path: str


@dataclass(frozen=True, order=True)
class AnonymousKey:
    path: str
    fingerprint: str

    def label(self):
        return "{} sha256={}".format(self.path, self.fingerprint)


@dataclass
class CoreIndex:
    entities: dict
    anonymous: Counter
    anonymous_paths: dict
    objects_by_path: dict
    paths: set
    resource_files: dict
    json_file_count: int
    object_count: int


@dataclass
class DefinitionChange:
    key: EntityKey
    removed_count: int
    added_count: int
    baseline_paths: tuple
    target_paths: tuple

    def kind(self):
        if self.removed_count and self.added_count:
            return "modified"
        if self.removed_count:
            return "definition removed"
        return "extended"


@dataclass
class CoreComparison:
    missing: list
    added: list
    changed: list
    anonymous_missing: Counter
    anonymous_added: Counter
    missing_paths: list
    changed_resources: list


@dataclass
class BuiltinModAuditResult:
    mod_id: str
    baseline: CoreIndex
    target: CoreIndex
    comparison: CoreComparison
    statuses: list
    anonymous_statuses: list
    resource_statuses: list


@dataclass
class BuiltinModAuditSummary:
    results: list
    added_mods: tuple
    missing_mods: tuple
    baseline_identity_count: int
    target_identity_count: int
    errors: list


class GitTreeSource:
    def __init__(self, repo_root, treeish):
        self.repo_root = Path(repo_root)
        self.treeish = treeish
        result = run_git(
            self.repo_root, "rev-parse", "--verify",
            "{}^{{tree}}".format(treeish)
        )
        self.tree_hash = result.strip()

    def iter_files(self, prefix):
        command = [
            "git", "-C", str(self.repo_root), "archive", "--format=tar",
            self.treeish, "--", prefix
        ]
        # Fully drain both pipes before parsing.  Streaming tarfile iteration
        # can stop at the tar end marker while git still has trailing archive
        # padding to write; on Windows that can fill stdout and deadlock while
        # the parent waits on stderr/process completion.
        process = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False
        )
        if process.returncode:
            raise AuditFailure(
                "git archive failed for {}: {}".format(
                    self.treeish,
                    process.stderr.decode("utf-8", errors="replace").strip()
                )
            )
        try:
            with tarfile.open(fileobj=io.BytesIO(process.stdout), mode="r:") as archive:
                for member in archive:
                    if not member.isfile():
                        continue
                    extracted = archive.extractfile(member)
                    if extracted is None:
                        raise AuditFailure(
                            "could not read {} from {}".format(
                                member.name, self.treeish
                            )
                        )
                    yield member.name.replace("\\", "/"), extracted.read()
        except tarfile.TarError as error:
            raise AuditFailure(
                "git archive failed for {}: {}".format(self.treeish, error)
            )

    def description(self):
        return "{} (tree {})".format(self.treeish, self.tree_hash)


class WorktreeSource:
    def __init__(self, repo_root):
        self.repo_root = Path(repo_root)

    def iter_files(self, prefix):
        target = self.repo_root.joinpath(*prefix.split("/"))
        if not target.exists():
            raise AuditFailure(
                "worktree path does not exist: {}".format(prefix)
            )
        paths = [target] if target.is_file() else target.rglob("*")
        for path in sorted((item for item in paths if item.is_file())):
            relative = path.relative_to(self.repo_root).as_posix()
            yield relative, path.read_bytes()

    def description(self):
        return WORKTREE_TARGET


def run_git(repo_root, *arguments):
    result = subprocess.run(
        ["git", "-C", str(repo_root)] + list(arguments),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        text=True
    )
    if result.returncode:
        raise AuditFailure(
            "git {} failed: {}".format(
                " ".join(arguments), result.stderr.strip()
            )
        )
    return result.stdout


def find_repo_root(requested_root):
    start = Path(requested_root or Path.cwd())
    output = run_git(start, "rev-parse", "--show-toplevel")
    return Path(output.strip())


def decode_json(raw, path):
    try:
        return json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AuditFailure("invalid JSON in {}: {}".format(path, error))


def top_level_objects(document, path):
    if isinstance(document, dict):
        return [document]
    if not isinstance(document, list):
        raise AuditFailure(
            "{} has a non-object, non-array JSON root".format(path)
        )
    if any(not isinstance(item, dict) for item in document):
        raise AuditFailure(
            "{} has a non-object member in its top-level array".format(path)
        )
    return document


def recipe_identity_value(result, id_suffix=""):
    return result if not id_suffix else "{}#{}".format(result, id_suffix)


def identity_namespace(entity_type):
    if entity_type in ITEM_FACTORY_TYPES:
        return ITEM_IDENTITY_NAMESPACE
    return entity_type


def mod_info_identity(entity, path):
    has_ident = "ident" in entity
    has_id = "id" in entity
    ident = entity.get("ident")
    modern_id = entity.get("id")
    if has_ident and (not isinstance(ident, str) or not ident):
        raise AuditFailure(
            "{} has MOD_INFO with an invalid ident".format(path)
        )
    if has_id and (not isinstance(modern_id, str) or not modern_id):
        raise AuditFailure(
            "{} has MOD_INFO with an invalid id".format(path)
        )
    if has_ident and has_id and ident != modern_id:
        raise AuditFailure(
            "{} has conflicting MOD_INFO ident {} and id {}".format(
                path, ident, modern_id
            )
        )
    if has_ident:
        # mod_manager::load_modfile tests ident first for 0.G compatibility.
        return ident
    if has_id:
        return modern_id
    raise AuditFailure(
        "{} has MOD_INFO without an id/ident".format(path)
    )


def entity_keys(entity, path):
    entity_type = entity.get("type")
    if entity_type == "MOD_INFO":
        return [EntityKey(
            entity_type, "mod_id", mod_info_identity(entity, path)
        )]
    if entity_type == "recipe" and "result" in entity:
        result = entity["result"]
        id_suffix = entity.get("id_suffix", "")
        if not isinstance(result, str) or not result:
            raise AuditFailure(
                "{} has a recipe without a string result".format(path)
            )
        if not isinstance(id_suffix, str):
            raise AuditFailure(
                "{} has a recipe with a non-string id_suffix".format(path)
            )
        return [EntityKey(
            entity_type, "result+id_suffix",
            recipe_identity_value(result, id_suffix)
        )]
    if entity_type == "uncraft" and "result" in entity:
        result = entity["result"]
        if not isinstance(result, str) or not result:
            raise AuditFailure(
                "{} has an uncraft definition without a string result".format(
                    path
                )
            )
        return [EntityKey(entity_type, "result", result)]
    if entity_type == "snippet" and "category" in entity:
        category = entity["category"]
        if not isinstance(category, str) or not category:
            raise AuditFailure(
                "{} has a snippet without a string category".format(path)
            )
        return [EntityKey(entity_type, "category", category)]

    present_fields = [field for field in IDENTITY_FIELDS if field in entity]
    if not present_fields:
        return []
    if not isinstance(entity_type, str) or not entity_type:
        raise AuditFailure(
            "{} has a top-level identity without a string type".format(path)
        )
    keys = []
    for field in present_fields:
        value = entity[field]
        if value == "" or value == []:
            # 0.G has two sentinel overmap records with an intentionally empty
            # id.  They are top-level objects, but do not identify entities.
            continue
        if isinstance(value, str) and value:
            values = [value]
        elif (
            isinstance(value, list) and value and
            all(isinstance(item, str) and item for item in value)
        ):
            values = value
        else:
            raise AuditFailure(
                "{} has an unsupported top-level {} value".format(path, field)
            )
        keys.extend(
            EntityKey(identity_namespace(entity_type), field, item)
            for item in values
        )
    return keys


def canonical_json(entity):
    return json.dumps(
        entity, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )


def canonical_fingerprint(canonical):
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def normalized_blob_fingerprint(raw):
    normalized = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(normalized).hexdigest()


def root_for_path(path, core_roots):
    for root in core_roots:
        if path == root or path.startswith(root.rstrip("/") + "/"):
            return root
    return None


def index_core_files(file_items, core_roots=CORE_ROOTS):
    entities = defaultdict(list)
    anonymous = Counter()
    anonymous_paths = defaultdict(list)
    objects_by_path = defaultdict(list)
    paths = set()
    resource_files = {}
    json_file_count = 0
    object_count = 0
    json_count_by_root = Counter()
    for path, raw in file_items:
        normalized_path = path.replace("\\", "/")
        matched_root = root_for_path(normalized_path, core_roots)
        if matched_root is None:
            continue
        paths.add(normalized_path)
        if not normalized_path.endswith(".json"):
            resource_files[normalized_path] = normalized_blob_fingerprint(raw)
            continue
        json_file_count += 1
        json_count_by_root[matched_root] += 1
        document = decode_json(raw, normalized_path)
        for entity in top_level_objects(document, normalized_path):
            object_count += 1
            canonical = canonical_json(entity)
            occurrence = Occurrence(canonical, normalized_path)
            objects_by_path[normalized_path].append(occurrence)
            keys = entity_keys(entity, normalized_path)
            for key in keys:
                entities[key].append(occurrence)
            if not keys:
                key = AnonymousKey(
                    normalized_path, canonical_fingerprint(canonical)
                )
                anonymous[key] += 1
                anonymous_paths[key].append(normalized_path)
    missing_roots = [
        root for root in core_roots if not json_count_by_root[root]
    ]
    if missing_roots:
        raise AuditFailure(
            "no core JSON files found under {}".format(
                ", ".join(missing_roots)
            )
        )
    return CoreIndex(
        dict(entities), anonymous, dict(anonymous_paths),
        dict(objects_by_path), paths, resource_files, json_file_count,
        object_count
    )


def load_core_index(source):
    def all_core_files():
        for root in CORE_ROOTS:
            yield from source.iter_files(root)

    return index_core_files(all_core_files())


def occurrence_counter(occurrences):
    return Counter(occurrence.canonical for occurrence in occurrences)


def occurrence_paths(occurrences, selected_canonicals):
    selected = set(selected_canonicals)
    return tuple(sorted({
        occurrence.path for occurrence in occurrences
        if occurrence.canonical in selected
    }))


def compare_core(baseline, target):
    baseline_keys = set(baseline.entities)
    target_keys = set(target.entities)
    missing = sorted(baseline_keys - target_keys)
    added = sorted(target_keys - baseline_keys)
    changed = []
    for key in sorted(baseline_keys & target_keys):
        baseline_occurrences = baseline.entities[key]
        target_occurrences = target.entities[key]
        baseline_counter = occurrence_counter(baseline_occurrences)
        target_counter = occurrence_counter(target_occurrences)
        if baseline_counter == target_counter:
            continue
        removed = baseline_counter - target_counter
        added_definitions = target_counter - baseline_counter
        changed.append(DefinitionChange(
            key=key,
            removed_count=sum(removed.values()),
            added_count=sum(added_definitions.values()),
            baseline_paths=occurrence_paths(baseline_occurrences, removed),
            target_paths=occurrence_paths(
                target_occurrences, added_definitions
            )
        ))
    anonymous_missing = baseline.anonymous - target.anonymous
    anonymous_added = target.anonymous - baseline.anonymous
    missing_paths = sorted(baseline.paths - target.paths)
    changed_resources = sorted(
        path for path in baseline.resource_files.keys() &
        target.resource_files.keys()
        if baseline.resource_files[path] != target.resource_files[path]
    )
    return CoreComparison(
        missing, added, changed, anonymous_missing, anonymous_added,
        missing_paths, changed_resources
    )


def validate_entity_uniqueness(keys, target, scope):
    errors = []
    for key in sorted(keys):
        occurrences = target.entities[key]
        if len(occurrences) <= 1:
            continue
        paths = sorted({occurrence.path for occurrence in occurrences})
        errors.append(
            "new {} entity has multiple target definitions: {} "
            "({} occurrences in {})".format(
                scope, key.label(), len(occurrences), ", ".join(paths)
            )
        )
    return errors


def validate_new_entity_uniqueness(comparison, target, scope="core"):
    return validate_entity_uniqueness(comparison.added, target, scope)


def validate_shared_namespace_collisions(target, scope):
    errors = []
    for key in sorted(target.entities):
        if key.entity_type != ITEM_IDENTITY_NAMESPACE:
            continue
        type_paths = defaultdict(set)
        for occurrence in target.entities[key]:
            literal_type = json.loads(occurrence.canonical).get("type")
            type_paths[literal_type].add(occurrence.path)
        if len(type_paths) <= 1:
            continue
        definitions = "; ".join(
            "{} in {}".format(literal_type, ", ".join(sorted(paths)))
            for literal_type, paths in sorted(type_paths.items())
        )
        errors.append(
            "cross-type {} collision in shared itype_id namespace: {} "
            "({})".format(scope, key.label(), definitions)
        )
    return errors


def entity_fingerprint(occurrences):
    digest = hashlib.sha256()
    for canonical in sorted(
        occurrence.canonical for occurrence in occurrences
    ):
        digest.update(canonical.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def manifest_entity_key(entry, context):
    try:
        entity_type = entry["type"]
        field = entry.get("field", "id")
        value = entry["id"]
    except (KeyError, AttributeError) as error:
        raise AuditFailure("{} is missing {}".format(context, error))
    if (
        not isinstance(entity_type, str) or not entity_type or
        field not in MANIFEST_IDENTITY_FIELDS or
        not isinstance(value, str) or not value
    ):
        raise AuditFailure("{} has an invalid entity key".format(context))
    if entity_type == "MOD_INFO":
        if field not in ("id", "ident", "mod_id"):
            raise AuditFailure(
                "{} has an invalid MOD_INFO identity field".format(context)
            )
        return EntityKey(entity_type, "mod_id", value)
    if field == "result":
        if entity_type == "recipe":
            id_suffix = entry.get("id_suffix", "")
            if not isinstance(id_suffix, str):
                raise AuditFailure(
                    "{} has an invalid recipe id_suffix".format(context)
                )
            return EntityKey(
                entity_type, "result+id_suffix",
                recipe_identity_value(value, id_suffix)
            )
        if entity_type != "uncraft":
            raise AuditFailure(
                "{} uses result identity for unsupported type {}".format(
                    context, entity_type
                )
            )
    if field == "category" and entity_type != "snippet":
        raise AuditFailure(
            "{} uses category identity for unsupported type {}".format(
                context, entity_type
            )
        )
    return EntityKey(identity_namespace(entity_type), field, value)


def validate_extension_files(manifest_entries, comparison, baseline, target):
    errors = []
    statuses = []
    allowed = {}
    changes = {change.key: change for change in comparison.changed}
    hash_pattern = re.compile(r"^[0-9a-f]{64}$")
    seen_paths = set()
    for index, entry in enumerate(manifest_entries):
        context = "allowed_extension_files[{}]".format(index)
        if not isinstance(entry, dict):
            errors.append("{} is not an object".format(context))
            continue
        path = entry.get("path")
        entity_type = entry.get("type")
        expected_count = entry.get("expected_count")
        expected_fingerprint = entry.get("target_fingerprint")
        reason = entry.get("reason")
        if (
            not isinstance(path, str) or not path.endswith(".json") or
            root_for_path(path, CORE_ROOTS) is None or
            not isinstance(entity_type, str) or not entity_type or
            not isinstance(expected_count, int) or
            isinstance(expected_count, bool) or expected_count < 1 or
            not isinstance(expected_fingerprint, str) or
            not hash_pattern.match(expected_fingerprint)
        ):
            errors.append("{} has an invalid extension identity".format(
                context
            ))
            continue
        if not isinstance(reason, str) or not reason.strip():
            errors.append("{} has no reason".format(context))
            continue
        if path in seen_paths:
            errors.append("duplicate extension-file entry: {}".format(path))
            continue
        seen_paths.add(path)
        if path in baseline.paths:
            errors.append(
                "extension file already exists in the 0.G baseline: {}".format(
                    path
                )
            )
        occurrences = target.objects_by_path.get(path, [])
        if len(occurrences) != expected_count:
            errors.append(
                "extension file {} has {} objects, expected {}".format(
                    path, len(occurrences), expected_count
                )
            )
            continue
        actual_fingerprint = entity_fingerprint(occurrences)
        if actual_fingerprint != expected_fingerprint:
            errors.append(
                "extension file {} fingerprint mismatch: expected {}, "
                "got {}".format(
                    path, expected_fingerprint, actual_fingerprint
                )
            )

        file_keys = []
        for object_index, occurrence in enumerate(occurrences):
            entity = json.loads(occurrence.canonical)
            if entity.get("type") != entity_type:
                errors.append(
                    "{} object {} has type {}, expected {}".format(
                        path, object_index, entity.get("type"), entity_type
                    )
                )
                continue
            keys = entity_keys(entity, path)
            if len(keys) != 1 or keys[0].field != "id":
                errors.append(
                    "{} object {} does not have one stable id identity".format(
                        path, object_index
                    )
                )
                continue
            file_keys.append((keys[0], occurrence.canonical))

        key_counts = Counter(key for key, _ in file_keys)
        for key, count in sorted(key_counts.items()):
            if count != 1:
                errors.append(
                    "extension file {} repeats {} {} times".format(
                        path, key.label(), count
                    )
                )
                continue
            if key not in baseline.entities:
                errors.append(
                    "extension file {} targets non-baseline {}".format(
                        path, key.label()
                    )
                )
                continue
            change = changes.get(key)
            if change is None:
                errors.append(
                    "extension file {} did not extend {}".format(
                        path, key.label()
                    )
                )
                continue
            extension_canonical = next(
                canonical for candidate, canonical in file_keys
                if candidate == key
            )
            expected_target = occurrence_counter(baseline.entities[key])
            expected_target[extension_canonical] += 1
            actual_target = occurrence_counter(target.entities[key])
            if actual_target != expected_target:
                errors.append(
                    "extension file {} is not the only change to {}".format(
                        path, key.label()
                    )
                )
                continue
            if key in allowed:
                errors.append(
                    "multiple extension files target {}".format(key.label())
                )
                continue
            allowed[key] = reason.strip()
        statuses.append((path, len(file_keys), reason.strip()))
    return allowed, statuses, errors


def validate_allowlist(
    manifest_entries, comparison, baseline, target, extension_allowed=None,
    context_name="allowed_core_changes", scope_label="core"
):
    errors = []
    extension_allowed = extension_allowed or {}
    allowed = {}
    hash_pattern = re.compile(r"^[0-9a-f]{64}$")
    for index, entry in enumerate(manifest_entries):
        context = "{}[{}]".format(context_name, index)
        key = manifest_entity_key(entry, context)
        if key in allowed:
            errors.append("duplicate allow-list entry: {}".format(key.label()))
            continue
        fingerprint = entry.get("target_fingerprint")
        reason = entry.get("reason")
        if (
            not isinstance(fingerprint, str) or
            not hash_pattern.match(fingerprint)
        ):
            errors.append(
                "{} has an invalid target fingerprint".format(context)
            )
            continue
        if not isinstance(reason, str) or not reason.strip():
            errors.append("{} has no reason".format(context))
            continue
        allowed[key] = (fingerprint, reason.strip())

    for key in sorted(set(allowed) & set(extension_allowed)):
        errors.append(
            "definition is allowed both directly and by extension file: "
            "{}".format(key.label())
        )

    changed_keys = {change.key for change in comparison.changed}
    statuses = []
    for change in comparison.changed:
        entry = allowed.get(change.key)
        if entry is None:
            extension_reason = extension_allowed.get(change.key)
            if extension_reason is not None:
                statuses.append((
                    change, "ALLOWED EXTENSION", extension_reason
                ))
                continue
            errors.append(
                "unallowlisted {} definition change: {}".format(
                    scope_label, change.key.label()
                )
            )
            statuses.append((change, "UNALLOWLISTED", ""))
            continue
        expected_fingerprint, reason = entry
        actual_fingerprint = entity_fingerprint(target.entities[change.key])
        if actual_fingerprint != expected_fingerprint:
            errors.append(
                "allow-list fingerprint mismatch for {}: expected {}, "
                "got {}".format(
                    change.key.label(), expected_fingerprint,
                    actual_fingerprint
                )
            )
            statuses.append((change, "FINGERPRINT MISMATCH", reason))
        else:
            statuses.append((change, "ALLOWED", reason))

    for key in sorted(set(allowed) - changed_keys):
        errors.append("stale allow-list entry: {}".format(key.label()))
    for key in allowed:
        if key not in baseline.entities:
            errors.append(
                "allow-list key was not present in the 0.G baseline: "
                "{}".format(
                    key.label()
                )
            )
        if key not in target.entities:
            errors.append(
                "allow-list key is absent from the target: {}".format(
                    key.label()
                )
            )
    return statuses, errors


def validate_anonymous_allowlist(
    manifest_entries, comparison, baseline, target,
    context_name="allowed_anonymous_changes", roots=CORE_ROOTS,
    scope_label="core"
):
    errors = []
    statuses = []
    remaining = comparison.anonymous_missing.copy()
    hash_pattern = re.compile(r"^[0-9a-f]{64}$")
    seen = set()
    for index, entry in enumerate(manifest_entries):
        context = "{}[{}]".format(context_name, index)
        if not isinstance(entry, dict):
            errors.append("{} is not an object".format(context))
            continue
        path = entry.get("path")
        target_path = entry.get("target_path", path)
        baseline_fingerprint = entry.get("baseline_fingerprint")
        target_fingerprint = entry.get("target_fingerprint")
        count = entry.get("count", 1)
        reason = entry.get("reason")
        identity = (
            path, baseline_fingerprint, target_path, target_fingerprint
        )
        if identity in seen:
            errors.append("duplicate anonymous allow-list entry: {}".format(
                identity
            ))
            continue
        seen.add(identity)
        if (
            not isinstance(path, str) or not path or
            root_for_path(path, roots) is None or
            not isinstance(target_path, str) or not target_path or
            root_for_path(target_path, roots) is None or
            not isinstance(baseline_fingerprint, str) or
            not hash_pattern.match(baseline_fingerprint) or
            not isinstance(target_fingerprint, str) or
            not hash_pattern.match(target_fingerprint) or
            not isinstance(count, int) or isinstance(count, bool) or count < 1
        ):
            errors.append("{} has an invalid anonymous identity".format(
                context
            ))
            continue
        if not isinstance(reason, str) or not reason.strip():
            errors.append("{} has no reason".format(context))
            continue
        baseline_key = AnonymousKey(path, baseline_fingerprint)
        target_key = AnonymousKey(target_path, target_fingerprint)
        if baseline.anonymous[baseline_key] < count:
            errors.append(
                "{} baseline anonymous object is absent or has count below {}: "
                "{}".format(context, count, baseline_key.label())
            )
        if target.anonymous[target_key] < count:
            errors.append(
                "{} target anonymous object is absent or has count below {}: "
                "{}".format(context, count, target_key.label())
            )
        if comparison.anonymous_added[target_key] < count:
            errors.append(
                "{} target anonymous fingerprint is not a newly added "
                "replacement: {}".format(context, target_key.label())
            )
        if remaining[baseline_key] < count:
            errors.append(
                "stale anonymous allow-list entry: {}".format(
                    baseline_key.label()
                )
            )
        else:
            remaining[baseline_key] -= count
            if remaining[baseline_key] == 0:
                del remaining[baseline_key]
            statuses.append((baseline_key, target_key, count, reason.strip()))
    for key, count in sorted(remaining.items()):
        errors.append(
            "baseline anonymous {} object disappeared ({} copy/copies): "
            "{}".format(scope_label, count, key.label())
        )
    return statuses, errors


def validate_resource_allowlist(
    manifest_entries, comparison, baseline, target,
    context_name="allowed_resource_changes", roots=CORE_ROOTS,
    scope_label="core"
):
    errors = []
    allowed = {}
    hash_pattern = re.compile(r"^[0-9a-f]{64}$")
    for index, entry in enumerate(manifest_entries):
        context = "{}[{}]".format(context_name, index)
        if not isinstance(entry, dict):
            errors.append("{} is not an object".format(context))
            continue
        path = entry.get("path")
        fingerprint = entry.get("target_fingerprint")
        reason = entry.get("reason")
        if (
            not isinstance(path, str) or not path or
            root_for_path(path, roots) is None or
            not isinstance(fingerprint, str) or
            not hash_pattern.match(fingerprint)
        ):
            errors.append("{} has an invalid resource identity".format(
                context
            ))
            continue
        if not isinstance(reason, str) or not reason.strip():
            errors.append("{} has no reason".format(context))
            continue
        if path in allowed:
            errors.append("duplicate resource allow-list entry: {}".format(
                path
            ))
            continue
        allowed[path] = (fingerprint, reason.strip())

    statuses = []
    changed = set(comparison.changed_resources)
    for path in comparison.changed_resources:
        entry = allowed.get(path)
        if entry is None:
            errors.append(
                "unallowlisted {} resource change: {}".format(
                    scope_label, path
                )
            )
            statuses.append((path, "UNALLOWLISTED", ""))
            continue
        expected, reason = entry
        actual = target.resource_files[path]
        if expected != actual:
            errors.append(
                "resource fingerprint mismatch for {}: expected {}, "
                "got {}".format(path, expected, actual)
            )
            statuses.append((path, "FINGERPRINT MISMATCH", reason))
        else:
            statuses.append((path, "ALLOWED", reason))
    for path in sorted(set(allowed) - changed):
        errors.append("stale resource allow-list entry: {}".format(path))
    return statuses, errors


def normalized_tree_fingerprint(files, root):
    prefix = root.rstrip("/") + "/"
    selected = sorted(
        (path, raw) for path, raw in files.items() if path.startswith(prefix)
    )
    if not selected:
        raise AuditFailure(
            "optional mod root is empty or absent: {}".format(root)
        )
    digest = hashlib.sha256()
    for path, raw in selected:
        relative = path[len(prefix):]
        normalized = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(normalized)
        digest.update(b"\0")
    return digest.hexdigest()


@dataclass(frozen=True)
class ModMetadata:
    dependencies: tuple
    path: str
    root: str


def load_mod_metadata(mod_files):
    metadata = {}
    metadata_paths = sorted(
        path for path in mod_files
        if path == DEFAULT_MOD_METADATA_PATH or path.endswith("/modinfo.json")
    )
    for path in metadata_paths:
        document = decode_json(mod_files[path], path)
        for entity in top_level_objects(document, path):
            if entity.get("type") != "MOD_INFO":
                continue
            mod_id = mod_info_identity(entity, path)
            dependencies = entity.get("dependencies", [])
            if not (
                isinstance(dependencies, list) and
                all(isinstance(item, str) and item for item in dependencies)
            ):
                raise AuditFailure(
                    "{} has invalid MOD_INFO dependencies".format(path)
                )
            if mod_id in metadata:
                raise AuditFailure("duplicate MOD_INFO id: {}".format(mod_id))
            root = (
                path if path == DEFAULT_MOD_METADATA_PATH else
                path.rsplit("/", 1)[0]
            )
            metadata[mod_id] = ModMetadata(
                tuple(dependencies), path, root
            )
    if "dev:default" not in metadata:
        raise AuditFailure(
            "data/mods/default.json does not define dev:default"
        )
    return metadata


def default_enabled_mods(metadata):
    enabled = set()
    pending = list(metadata["dev:default"].dependencies)
    while pending:
        mod_id = pending.pop()
        if mod_id in enabled:
            continue
        enabled.add(mod_id)
        if mod_id not in metadata:
            raise AuditFailure(
                "default mod dependency has no MOD_INFO definition: {}".format(
                    mod_id
                )
            )
        pending.extend(metadata[mod_id].dependencies)
    return enabled


def mod_file_items(mod_files, metadata):
    prefix = metadata.root.rstrip("/") + "/"
    selected = sorted(
        (path, raw) for path, raw in mod_files.items()
        if path == metadata.root or path.startswith(prefix)
    )
    if not selected:
        raise AuditFailure(
            "built-in mod root is empty or absent: {}".format(
                metadata.root
            )
        )
    return selected


def load_builtin_mod_indexes(mod_files, metadata):
    return {
        mod_id: index_core_files(
            mod_file_items(mod_files, mod),
            core_roots=(mod.root,)
        )
        for mod_id, mod in metadata.items()
    }


def group_builtin_mod_allowlist(entries, context_name):
    grouped = defaultdict(list)
    errors = []
    for index, entry in enumerate(entries):
        context = "{}[{}]".format(context_name, index)
        if not isinstance(entry, dict):
            errors.append("{} is not an object".format(context))
            continue
        mod_id = entry.get("mod_id")
        if not isinstance(mod_id, str) or not mod_id:
            errors.append("{} has no mod_id".format(context))
            continue
        grouped[mod_id].append(entry)
    return dict(grouped), errors


def audit_builtin_mods(
    baseline_files, target_files, baseline_metadata, target_metadata,
    allowed_changes, allowed_anonymous_changes, allowed_resource_changes
):
    change_groups, errors = group_builtin_mod_allowlist(
        allowed_changes, "allowed_builtin_mod_changes"
    )
    anonymous_groups, group_errors = group_builtin_mod_allowlist(
        allowed_anonymous_changes,
        "allowed_builtin_mod_anonymous_changes"
    )
    errors.extend(group_errors)
    resource_groups, group_errors = group_builtin_mod_allowlist(
        allowed_resource_changes,
        "allowed_builtin_mod_resource_changes"
    )
    errors.extend(group_errors)

    baseline_indexes = load_builtin_mod_indexes(
        baseline_files, baseline_metadata
    )
    target_indexes = load_builtin_mod_indexes(target_files, target_metadata)
    baseline_ids = set(baseline_indexes)
    target_ids = set(target_indexes)
    common_ids = baseline_ids & target_ids
    added_ids = tuple(sorted(target_ids - baseline_ids))
    missing_ids = tuple(sorted(baseline_ids - target_ids))

    for mod_id in missing_ids:
        errors.append(
            "baseline built-in mod disappeared: {} ({})".format(
                mod_id, baseline_metadata[mod_id].root
            )
        )

    configured_ids = (
        set(change_groups) | set(anonymous_groups) | set(resource_groups)
    )
    for mod_id in sorted(configured_ids - common_ids):
        errors.append(
            "built-in mod allow-list references a mod that is not present "
            "in both baseline and target: {}".format(mod_id)
        )

    results = []
    for mod_id in sorted(common_ids):
        baseline = baseline_indexes[mod_id]
        target = target_indexes[mod_id]
        comparison = compare_core(baseline, target)
        scope = "built-in mod {}".format(mod_id)
        errors.extend(validate_shared_namespace_collisions(target, scope))
        context_suffix = "[{}]".format(mod_id)
        statuses, mod_errors = validate_allowlist(
            change_groups.get(mod_id, []), comparison, baseline, target,
            context_name=(
                "allowed_builtin_mod_changes" + context_suffix
            ),
            scope_label=scope
        )
        errors.extend(mod_errors)
        roots = tuple(sorted({
            baseline_metadata[mod_id].root,
            target_metadata[mod_id].root
        }))
        anonymous_statuses, mod_errors = validate_anonymous_allowlist(
            anonymous_groups.get(mod_id, []), comparison, baseline, target,
            context_name=(
                "allowed_builtin_mod_anonymous_changes" + context_suffix
            ),
            roots=roots, scope_label=scope
        )
        errors.extend(mod_errors)
        resource_statuses, mod_errors = validate_resource_allowlist(
            resource_groups.get(mod_id, []), comparison, baseline, target,
            context_name=(
                "allowed_builtin_mod_resource_changes" + context_suffix
            ),
            roots=roots, scope_label=scope
        )
        errors.extend(mod_errors)
        errors.extend(
            validate_new_entity_uniqueness(comparison, target, scope)
        )
        for missing in comparison.missing:
            errors.append(
                "baseline {} entity disappeared: {}".format(
                    scope, missing.label()
                )
            )
        for path in comparison.missing_paths:
            errors.append(
                "baseline {} path disappeared: {}".format(scope, path)
            )
        results.append(BuiltinModAuditResult(
            mod_id, baseline, target, comparison, statuses,
            anonymous_statuses, resource_statuses
        ))

    for mod_id in added_ids:
        target = target_indexes[mod_id]
        scope = "built-in mod {}".format(mod_id)
        errors.extend(validate_shared_namespace_collisions(target, scope))
        errors.extend(validate_entity_uniqueness(
            target.entities, target, scope
        ))

    return BuiltinModAuditSummary(
        results=results,
        added_mods=added_ids,
        missing_mods=missing_ids,
        baseline_identity_count=sum(
            len(index.entities) for index in baseline_indexes.values()
        ),
        target_identity_count=sum(
            len(index.entities) for index in target_indexes.values()
        ),
        errors=errors
    )


def validate_donor_imports(
    imports, baseline, target, mod_files, metadata, default_enabled
):
    messages = []
    errors = []
    import_keys = set()
    all_target_paths = target.paths | set(mod_files)
    hash_pattern = re.compile(r"^[0-9a-f]{40}$")
    fingerprint_pattern = re.compile(r"^[0-9a-f]{64}$")
    for index, entry in enumerate(imports):
        context = "donor_imports[{}]".format(index)
        if not isinstance(entry, dict):
            errors.append("{} is not an object".format(context))
            continue
        import_key = entry.get("key")
        name = entry.get("name")
        donor_commit = entry.get("donor_commit")
        classification = entry.get("classification")
        if not isinstance(import_key, str) or not import_key:
            errors.append("{} has no key".format(context))
            continue
        if import_key in import_keys:
            errors.append("duplicate donor import key: {}".format(import_key))
            continue
        import_keys.add(import_key)
        if not isinstance(name, str) or not name:
            errors.append("{} has no name".format(context))
            name = import_key
        if (
            not isinstance(donor_commit, str) or
            not hash_pattern.match(donor_commit)
        ):
            errors.append("{} has an invalid donor commit".format(context))
        expected_import = EXPECTED_DONOR_IMPORTS.get(import_key)
        if expected_import is not None:
            for field, expected_value in expected_import.items():
                if entry.get(field) != expected_value:
                    errors.append(
                        "{} must set {} to {}".format(
                            import_key, field, expected_value
                        )
                    )
        required_paths = entry.get("required_paths", [])
        if not (
            isinstance(required_paths, list) and
            all(isinstance(path, str) and path for path in required_paths)
        ):
            errors.append("{} has invalid required_paths".format(context))
            required_paths = []
        for path in required_paths:
            if path not in all_target_paths:
                errors.append(
                    "{} is missing required path {}".format(name, path)
                )

        if classification == "core":
            for path in required_paths:
                if root_for_path(path, CORE_ROOTS) is None:
                    errors.append(
                        "core import {} has non-core required path {}".format(
                            name, path
                        )
                    )
            required_entities = entry.get("required_entities", [])
            if (
                not isinstance(required_entities, list) or
                not required_entities
            ):
                errors.append("{} has no required core entities".format(name))
                continue
            for entity_index, required in enumerate(required_entities):
                entity_context = "{}.required_entities[{}]".format(
                    context, entity_index
                )
                key = manifest_entity_key(required, entity_context)
                if key not in target.entities:
                    errors.append(
                        "{} is missing required core entity {}".format(
                            name, key.label()
                        )
                    )
                    continue
                if (
                    required.get("new_since_baseline", False) and
                    key in baseline.entities
                ):
                    errors.append(
                        "{} requires {} to be new, but it exists in the "
                        "baseline".format(
                            name, key.label()
                        )
                    )
                expected = required.get("target_fingerprint")
                if (
                    not isinstance(expected, str) or
                    not fingerprint_pattern.match(expected)
                ):
                    errors.append(
                        "{} must have an exact target fingerprint".format(
                            entity_context
                        )
                    )
                else:
                    actual = entity_fingerprint(target.entities[key])
                    if actual != expected:
                        errors.append(
                            "{} fingerprint mismatch for {}".format(
                                name, key.label()
                            )
                        )
            messages.append("CORE {} ({})".format(name, donor_commit))
        elif classification == "optional_mod":
            root = entry.get("root")
            mod_id = entry.get("mod_id")
            expected_tree = entry.get("tree_fingerprint")
            if (
                not isinstance(root, str) or
                not root.startswith("data/mods/") or root.endswith("/")
            ):
                errors.append(
                    "{} has an invalid optional mod root".format(name)
                )
                continue
            for path in required_paths:
                if not path.startswith(root + "/"):
                    errors.append(
                        "optional import {} has path outside its root: "
                        "{}".format(
                            name, path
                        )
                    )
            if not isinstance(mod_id, str) or not mod_id:
                errors.append("{} has no optional mod id".format(name))
                continue
            expected_modinfo_path = root + "/modinfo.json"
            mod_metadata = metadata.get(mod_id)
            if mod_metadata is None:
                errors.append(
                    "{} has no MOD_INFO entry for {}".format(name, mod_id)
                )
            elif mod_metadata.path != expected_modinfo_path:
                errors.append(
                    "{} MOD_INFO is at {}, expected {}".format(
                        name, mod_metadata.path, expected_modinfo_path
                    )
                )
            if (
                not isinstance(expected_tree, str) or
                not fingerprint_pattern.match(expected_tree)
            ):
                errors.append(
                    "{} has an invalid tree fingerprint".format(name)
                )
            else:
                actual_tree = normalized_tree_fingerprint(mod_files, root)
                if actual_tree != expected_tree:
                    errors.append(
                        "{} tree fingerprint mismatch: expected {}, "
                        "got {}".format(
                            name, expected_tree, actual_tree
                        )
                    )
            if mod_id in default_enabled:
                errors.append(
                    "optional mod {} is default-enabled (directly or "
                    "transitively)".format(
                        mod_id
                    )
                )
            messages.append(
                "OPTIONAL {} ({}, id {}; not default-enabled)".format(
                    name, donor_commit, mod_id
                )
            )
        else:
            errors.append(
                "{} has invalid classification {}".format(name, classification)
            )
    for import_key in sorted(set(EXPECTED_DONOR_IMPORTS) - import_keys):
        errors.append("missing required donor import: {}".format(import_key))
    return messages, errors


def load_manifest(path):
    try:
        raw = Path(path).read_bytes()
    except OSError as error:
        raise AuditFailure("cannot read manifest {}: {}".format(path, error))
    manifest = decode_json(raw, str(path))
    if not isinstance(manifest, dict):
        raise AuditFailure("manifest root must be an object")
    if manifest.get("schema_version") != 3:
        raise AuditFailure("manifest schema_version must be 3")
    if manifest.get("baseline_commit") != BASELINE_COMMIT:
        raise AuditFailure(
            "manifest baseline must be exact 0.G commit {}".format(
                BASELINE_COMMIT
            )
        )
    if manifest.get("core_roots") != list(CORE_ROOTS):
        raise AuditFailure(
            "manifest core_roots must be {}".format(list(CORE_ROOTS))
        )
    if manifest.get("donor_repository") != DONOR_REPOSITORY:
        raise AuditFailure(
            "manifest donor_repository must be {}".format(DONOR_REPOSITORY)
        )
    allowed_changes = manifest.get("allowed_core_changes")
    allowed_extension_files = manifest.get("allowed_extension_files")
    allowed_anonymous_changes = manifest.get("allowed_anonymous_changes")
    allowed_resource_changes = manifest.get("allowed_resource_changes")
    allowed_builtin_mod_changes = manifest.get(
        "allowed_builtin_mod_changes"
    )
    allowed_builtin_mod_anonymous_changes = manifest.get(
        "allowed_builtin_mod_anonymous_changes"
    )
    allowed_builtin_mod_resource_changes = manifest.get(
        "allowed_builtin_mod_resource_changes"
    )
    donor_imports = manifest.get("donor_imports")
    if not isinstance(allowed_changes, list):
        raise AuditFailure("manifest allowed_core_changes must be an array")
    if not isinstance(allowed_extension_files, list):
        raise AuditFailure(
            "manifest allowed_extension_files must be an array"
        )
    if not isinstance(allowed_anonymous_changes, list):
        raise AuditFailure(
            "manifest allowed_anonymous_changes must be an array"
        )
    if not isinstance(allowed_resource_changes, list):
        raise AuditFailure(
            "manifest allowed_resource_changes must be an array"
        )
    if not isinstance(allowed_builtin_mod_changes, list):
        raise AuditFailure(
            "manifest allowed_builtin_mod_changes must be an array"
        )
    if not isinstance(allowed_builtin_mod_anonymous_changes, list):
        raise AuditFailure(
            "manifest allowed_builtin_mod_anonymous_changes must be an "
            "array"
        )
    if not isinstance(allowed_builtin_mod_resource_changes, list):
        raise AuditFailure(
            "manifest allowed_builtin_mod_resource_changes must be an array"
        )
    if not isinstance(donor_imports, list):
        raise AuditFailure("manifest donor_imports must be an array")
    return manifest


def load_mod_files(source):
    return {
        path.replace("\\", "/"): raw
        for path, raw in source.iter_files("data/mods")
    }


def format_paths(paths):
    return ", ".join(paths) if paths else "(no replacement definition)"


def execute_audit(repo_root, target_name, manifest_path):
    manifest = load_manifest(manifest_path)
    baseline_source = GitTreeSource(repo_root, BASELINE_COMMIT)
    if target_name.upper() == WORKTREE_TARGET:
        target_source = WorktreeSource(repo_root)
    else:
        target_source = GitTreeSource(repo_root, target_name)

    baseline = load_core_index(baseline_source)
    target = load_core_index(target_source)
    comparison = compare_core(baseline, target)
    extension_allowed, extension_statuses, extension_errors = (
        validate_extension_files(
            manifest["allowed_extension_files"], comparison,
            baseline, target
        )
    )
    statuses, errors = validate_allowlist(
        manifest["allowed_core_changes"], comparison, baseline, target,
        extension_allowed
    )
    errors.extend(extension_errors)
    anonymous_statuses, anonymous_errors = validate_anonymous_allowlist(
        manifest["allowed_anonymous_changes"], comparison, baseline, target
    )
    errors.extend(anonymous_errors)
    resource_statuses, resource_errors = validate_resource_allowlist(
        manifest["allowed_resource_changes"], comparison, baseline, target
    )
    errors.extend(resource_errors)
    errors.extend(validate_new_entity_uniqueness(comparison, target))
    errors.extend(validate_shared_namespace_collisions(target, "core"))
    for missing in comparison.missing:
        errors.append(
            "baseline core entity disappeared: {}".format(missing.label())
        )
    for path in comparison.missing_paths:
        errors.append("baseline core path disappeared: {}".format(path))

    baseline_mod_files = load_mod_files(baseline_source)
    target_mod_files = load_mod_files(target_source)
    baseline_metadata = load_mod_metadata(baseline_mod_files)
    target_metadata = load_mod_metadata(target_mod_files)
    builtin_mods = audit_builtin_mods(
        baseline_mod_files, target_mod_files,
        baseline_metadata, target_metadata,
        manifest["allowed_builtin_mod_changes"],
        manifest["allowed_builtin_mod_anonymous_changes"],
        manifest["allowed_builtin_mod_resource_changes"]
    )
    errors.extend(builtin_mods.errors)
    enabled = default_enabled_mods(target_metadata)
    donor_messages, donor_errors = validate_donor_imports(
        manifest["donor_imports"], baseline, target, target_mod_files,
        target_metadata, enabled
    )
    errors.extend(donor_errors)

    print("baseline: {}".format(baseline_source.description()))
    print("target:   {}".format(target_source.description()))
    print(
        "core: {} baseline identities; {} target identities; {} added; "
        "{} missing; {} anonymous baseline objects".format(
            len(baseline.entities), len(target.entities),
            len(comparison.added), len(comparison.missing),
            sum(baseline.anonymous.values())
        )
    )
    print(
        "core definitions changed for {} existing IDs:".format(
            len(comparison.changed)
        )
    )
    if not statuses:
        print("  (none)")
    for change, status, reason in statuses:
        print(
            "  {} {} [{}]".format(
                status, change.key.label(), change.kind()
            )
        )
        print("    baseline: {}".format(format_paths(change.baseline_paths)))
        print("    target:   {}".format(format_paths(change.target_paths)))
        if reason:
            print("    reason:   {}".format(reason))

    print("strict extension files:")
    if not extension_statuses:
        print("  (none)")
    for path, count, reason in extension_statuses:
        print("  ALLOWED {} ({} baseline-ID extensions)".format(path, count))
        print("    reason:   {}".format(reason))

    print(
        "anonymous core replacements: {}".format(len(anonymous_statuses))
    )
    for baseline_key, target_key, count, reason in anonymous_statuses:
        print(
            "  ALLOWED {} copy/copies {} -> {}".format(
                count, baseline_key.label(), target_key.label()
            )
        )
        print("    reason:   {}".format(reason))

    print("non-JSON core resource changes:")
    if not resource_statuses:
        print("  (none)")
    for path, status, reason in resource_statuses:
        print("  {} {}".format(status, path))
        if reason:
            print("    reason:   {}".format(reason))

    changed_mod_definitions = sum(
        len(result.comparison.changed) for result in builtin_mods.results
    )
    anonymous_mod_replacements = sum(
        len(result.anonymous_statuses) for result in builtin_mods.results
    )
    changed_mod_resources = sum(
        len(result.resource_statuses) for result in builtin_mods.results
    )
    print(
        "built-in mods: {} baseline packages; {} target packages; "
        "{} baseline identities; {} target identities; {} added packages; "
        "{} missing packages".format(
            len(baseline_metadata), len(target_metadata),
            builtin_mods.baseline_identity_count,
            builtin_mods.target_identity_count,
            len(builtin_mods.added_mods), len(builtin_mods.missing_mods)
        )
    )
    print(
        "built-in mod definitions changed for {} existing IDs:".format(
            changed_mod_definitions
        )
    )
    printed_mod_changes = False
    for result in builtin_mods.results:
        if not result.statuses:
            continue
        printed_mod_changes = True
        print("  MOD {}:".format(result.mod_id))
        for change, status, reason in result.statuses:
            print(
                "    {} {} [{}]".format(
                    status, change.key.label(), change.kind()
                )
            )
            print(
                "      baseline: {}".format(
                    format_paths(change.baseline_paths)
                )
            )
            print(
                "      target:   {}".format(
                    format_paths(change.target_paths)
                )
            )
            if reason:
                print("      reason:   {}".format(reason))
    if not printed_mod_changes:
        print("  (none)")
    print(
        "anonymous built-in-mod replacements: {}".format(
            anonymous_mod_replacements
        )
    )
    for result in builtin_mods.results:
        for baseline_key, target_key, count, reason in (
            result.anonymous_statuses
        ):
            print(
                "  ALLOWED MOD {} {} copy/copies {} -> {}".format(
                    result.mod_id, count, baseline_key.label(),
                    target_key.label()
                )
            )
            print("    reason:   {}".format(reason))
    print(
        "non-JSON built-in-mod resource changes: {}".format(
            changed_mod_resources
        )
    )
    for result in builtin_mods.results:
        for path, status, reason in result.resource_statuses:
            print("  {} MOD {} {}".format(status, result.mod_id, path))
            if reason:
                print("    reason:   {}".format(reason))
    print("new built-in mod packages:")
    if not builtin_mods.added_mods:
        print("  (none)")
    for mod_id in builtin_mods.added_mods:
        print(
            "  {} ({})".format(mod_id, target_metadata[mod_id].root)
        )

    print("donor imports:")
    for message in donor_messages:
        print("  {}".format(message))

    if errors:
        print("FAIL additive audit ({} error(s)):".format(len(errors)))
        for error in errors:
            print("  ERROR {}".format(error))
        return 1
    print(
        "PASS additive audit: no baseline core or built-in-mod identities, "
        "anonymous objects, resources, or paths disappeared; all {} core "
        "and {} built-in-mod changed identities were explicitly "
        "fingerprinted".format(
            len(comparison.changed), changed_mod_definitions
        )
    )
    return 0


def json_file(entities):
    return json.dumps(entities, ensure_ascii=False).encode("utf-8")


class AdditiveAuditSelfTests(unittest.TestCase):
    def index(self, entities):
        return index_core_files(
            [("data/json/fixture.json", json_file(entities))],
            core_roots=("data/json",)
        )

    def mod_tree(self, definitions_by_mod, resources_by_mod=None):
        files = {
            DEFAULT_MOD_METADATA_PATH: json_file([{
                "type": "MOD_INFO", "id": "dev:default",
                "dependencies": []
            }])
        }
        for mod_id, definitions in definitions_by_mod.items():
            root = "data/mods/{}".format(mod_id)
            files["{}/modinfo.json".format(root)] = json_file([{
                "type": "MOD_INFO", "id": mod_id,
                "dependencies": []
            }])
            if definitions:
                files["{}/definitions.json".format(root)] = json_file(
                    definitions
                )
        for mod_id, resources in (resources_by_mod or {}).items():
            root = "data/mods/{}".format(mod_id)
            for relative_path, raw in resources.items():
                files["{}/{}".format(root, relative_path)] = raw
        return files

    def audit_mod_trees(
        self, baseline_files, target_files, changes=None,
        anonymous_changes=None, resource_changes=None
    ):
        return audit_builtin_mods(
            baseline_files, target_files,
            load_mod_metadata(baseline_files),
            load_mod_metadata(target_files),
            changes or [], anonymous_changes or [], resource_changes or []
        )

    def test_additive_id_passes_without_allowlist(self):
        baseline = self.index([{"type": "thing", "id": "old", "value": 1}])
        target = self.index([
            {"type": "thing", "id": "old", "value": 1},
            {"type": "thing", "id": "new", "value": 2}
        ])
        comparison = compare_core(baseline, target)
        self.assertEqual([], comparison.missing)
        self.assertEqual(1, len(comparison.added))
        self.assertEqual([], comparison.changed)

    def test_disappearing_id_is_detected(self):
        baseline = self.index([{"type": "thing", "id": "old"}])
        target = self.index([{"type": "thing", "id": "new"}])
        self.assertEqual(
            [EntityKey("thing", "id", "old")],
            compare_core(baseline, target).missing
        )

    def test_new_id_with_multiple_target_definitions_is_rejected(self):
        baseline = self.index([{"type": "thing", "id": "old"}])
        target = self.index([
            {"type": "thing", "id": "old"},
            {"type": "thing", "id": "new", "value": 1},
            {"type": "thing", "id": "new", "value": 2}
        ])
        comparison = compare_core(baseline, target)

        errors = validate_new_entity_uniqueness(comparison, target)

        self.assertEqual(1, len(errors))
        self.assertIn("thing id=new", errors[0])
        self.assertIn("2 occurrences", errors[0])

        unique_target = self.index([
            {"type": "thing", "id": "old"},
            {"type": "thing", "id": "new", "value": 1}
        ])
        self.assertEqual(
            [],
            validate_new_entity_uniqueness(
                compare_core(baseline, unique_target), unique_target
            )
        )

    def test_changed_definition_requires_exact_allowlist_fingerprint(self):
        baseline = self.index([{"type": "thing", "id": "old", "value": 1}])
        target = self.index([{"type": "thing", "id": "old", "value": 2}])
        comparison = compare_core(baseline, target)
        _, errors = validate_allowlist([], comparison, baseline, target)
        self.assertTrue(any("unallowlisted" in error for error in errors))
        key = EntityKey("thing", "id", "old")
        entry = {
            "type": "thing", "id": "old", "reason": "fixture feature",
            "target_fingerprint": entity_fingerprint(target.entities[key])
        }
        statuses, errors = validate_allowlist(
            [entry], comparison, baseline, target
        )
        self.assertEqual([], errors)
        self.assertEqual("ALLOWED", statuses[0][1])
        entry["target_fingerprint"] = "0" * 64
        _, errors = validate_allowlist([entry], comparison, baseline, target)
        self.assertTrue(
            any("fingerprint mismatch" in error for error in errors)
        )

    def test_new_fragment_for_existing_id_is_reported_as_change(self):
        original = {"type": "group", "id": "shared", "entries": ["a"]}
        extension = {"type": "group", "id": "shared", "entries": ["b"]}
        baseline = self.index([original])
        target = self.index([original, extension])
        comparison = compare_core(baseline, target)
        self.assertEqual(1, len(comparison.changed))
        self.assertEqual("extended", comparison.changed[0].kind())

    def test_item_types_share_itype_identity_and_reject_collisions(self):
        original = {
            "type": "GENERIC", "id": "shared_item", "value": 1
        }
        conflicting = {
            "type": "AMMO", "id": "shared_item", "value": 2
        }
        baseline = self.index([original])
        target = self.index([original, conflicting])
        key = EntityKey(ITEM_IDENTITY_NAMESPACE, "id", "shared_item")
        self.assertIn(key, baseline.entities)
        self.assertIn(key, target.entities)
        comparison = compare_core(baseline, target)
        self.assertEqual([], comparison.added)
        self.assertEqual([], comparison.missing)
        self.assertEqual([key], [change.key for change in comparison.changed])
        collision_errors = validate_shared_namespace_collisions(
            target, "core"
        )
        self.assertEqual(1, len(collision_errors))
        self.assertIn("AMMO", collision_errors[0])
        self.assertIn("GENERIC", collision_errors[0])
        self.assertIn("shared_item", collision_errors[0])
        _, allow_errors = validate_allowlist([{
            "type": "GENERIC", "id": "shared_item",
            "target_fingerprint": entity_fingerprint(target.entities[key]),
            "reason": "collision fixture must still fail"
        }], comparison, baseline, target)
        self.assertEqual([], allow_errors)
        self.assertEqual(1, len(collision_errors))

        replacement = self.index([conflicting])
        replacement_comparison = compare_core(baseline, replacement)
        self.assertEqual([], replacement_comparison.added)
        self.assertEqual([], replacement_comparison.missing)
        _, errors = validate_allowlist(
            [], replacement_comparison, baseline, replacement
        )
        self.assertTrue(any(
            "unallowlisted core definition change" in error
            for error in errors
        ))
        self.assertEqual(
            [], validate_shared_namespace_collisions(replacement, "core")
        )

        manifest_key = manifest_entity_key({
            "type": "GENERIC", "id": "shared_item"
        }, "fixture")
        self.assertEqual(key, manifest_key)

    def test_recipe_identity_includes_result_and_suffix(self):
        indexed = self.index([
            {"type": "recipe", "result": "widget", "difficulty": 1},
            {
                "type": "recipe", "result": "widget",
                "id_suffix": "alternate", "difficulty": 2
            }
        ])
        self.assertIn(
            EntityKey("recipe", "result+id_suffix", "widget"),
            indexed.entities
        )
        self.assertIn(
            EntityKey(
                "recipe", "result+id_suffix", "widget#alternate"
            ),
            indexed.entities
        )

    def test_snippet_category_is_a_stable_identity(self):
        indexed = self.index([{
            "type": "snippet", "category": "<rule_text>", "text": "rule"
        }])
        self.assertIn(
            EntityKey("snippet", "category", "<rule_text>"),
            indexed.entities
        )

    def test_anonymous_baseline_object_cannot_disappear(self):
        baseline = self.index([{"type": "speech", "sound": "hello"}])
        target = self.index([{"type": "speech", "sound": "goodbye"}])
        comparison = compare_core(baseline, target)
        self.assertEqual(1, sum(comparison.anonymous_missing.values()))
        _, errors = validate_anonymous_allowlist(
            [], comparison, baseline, target
        )
        self.assertTrue(
            any("anonymous core object disappeared" in error for error in errors)
        )
        baseline_key = next(iter(comparison.anonymous_missing))
        target_key = next(iter(comparison.anonymous_added))
        entry = {
            "path": baseline_key.path,
            "baseline_fingerprint": baseline_key.fingerprint,
            "target_fingerprint": target_key.fingerprint,
            "reason": "fixture replacement"
        }
        _, errors = validate_anonymous_allowlist(
            [entry], comparison, baseline, target
        )
        self.assertEqual([], errors)

    def test_core_and_raw_roots_are_indexed(self):
        indexed = index_core_files([
            (
                "data/json/fixture.json",
                json_file([{"type": "thing", "id": "json"}])
            ),
            (
                "data/core/fixture.json",
                json_file([{"type": "thing", "id": "core"}])
            ),
            (
                "data/raw/fixture.json",
                json_file([{"type": "thing", "id": "raw"}])
            ),
            ("data/raw/resource.txt", b"resource\r\n")
        ])
        self.assertIn(EntityKey("thing", "id", "json"), indexed.entities)
        self.assertIn(EntityKey("thing", "id", "core"), indexed.entities)
        self.assertIn(EntityKey("thing", "id", "raw"), indexed.entities)
        self.assertIn("data/raw/resource.txt", indexed.resource_files)

    def test_git_tree_source_drains_complete_archive(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            fixture = repo / "data" / "raw" / "fixture.json"
            fixture.parent.mkdir(parents=True)
            fixture.write_bytes(b'[ { "type": "thing", "id": "raw" } ]\n')
            run_git(repo, "init", "-q")
            run_git(repo, "config", "core.autocrlf", "false")
            run_git(repo, "config", "user.name", "Additive Audit Test")
            run_git(repo, "config", "user.email", "audit@example.invalid")
            run_git(repo, "add", "data/raw/fixture.json")
            run_git(repo, "commit", "-q", "-m", "fixture")

            source = GitTreeSource(repo, "HEAD")
            archived = dict(source.iter_files("data/raw"))
            self.assertEqual(
                fixture.read_bytes(), archived["data/raw/fixture.json"]
            )

    def test_strict_extension_file_only_adds_baseline_id_fragments(self):
        baseline = index_core_files([
            (
                "data/json/vehicles.json",
                json_file([{"type": "vehicle", "id": "car", "base": 1}])
            )
        ], core_roots=("data/json",))
        extension_path = "data/json/vehicles/zz_extension.json"
        target = index_core_files([
            (
                "data/json/vehicles.json",
                json_file([{"type": "vehicle", "id": "car", "base": 1}])
            ),
            (
                extension_path,
                json_file([{"type": "vehicle", "id": "car", "extra": 1}])
            )
        ], core_roots=("data/json",))
        comparison = compare_core(baseline, target)
        entry = {
            "path": extension_path,
            "type": "vehicle",
            "expected_count": 1,
            "target_fingerprint": entity_fingerprint(
                target.objects_by_path[extension_path]
            ),
            "reason": "fixture extension"
        }
        allowed, _, errors = validate_extension_files(
            [entry], comparison, baseline, target
        )
        self.assertEqual([], errors)
        key = EntityKey("vehicle", "id", "car")
        self.assertIn(key, allowed)
        statuses, errors = validate_allowlist(
            [], comparison, baseline, target, allowed
        )
        self.assertEqual([], errors)
        self.assertEqual("ALLOWED EXTENSION", statuses[0][1])

        tampered = index_core_files([
            (
                "data/json/vehicles.json",
                json_file([{"type": "vehicle", "id": "car", "base": 2}])
            ),
            (
                extension_path,
                json_file([{"type": "vehicle", "id": "car", "extra": 1}])
            )
        ], core_roots=("data/json",))
        _, _, errors = validate_extension_files(
            [entry], compare_core(baseline, tampered), baseline, tampered
        )
        self.assertTrue(
            any("is not the only change" in error for error in errors)
        )

    def test_optional_mod_can_be_detected_through_default_dependency(self):
        mod_files = {
            "data/mods/default.json": json_file([{
                "type": "MOD_INFO", "id": "dev:default",
                "dependencies": ["dda", "bridge"]
            }]),
            "data/mods/dda/modinfo.json": json_file([{
                "type": "MOD_INFO", "id": "dda", "dependencies": []
            }]),
            "data/mods/bridge/modinfo.json": json_file([{
                "type": "MOD_INFO", "id": "bridge",
                "dependencies": ["optional"]
            }]),
            "data/mods/optional/modinfo.json": json_file([{
                "type": "MOD_INFO", "id": "optional",
                "dependencies": ["dda"]
            }])
        }
        enabled = default_enabled_mods(load_mod_metadata(mod_files))
        self.assertIn("optional", enabled)

    def test_mod_info_uses_ident_precedence_and_rejects_conflicts(self):
        legacy_files = {
            DEFAULT_MOD_METADATA_PATH: json_file([{
                "type": "MOD_INFO", "ident": "dev:default",
                "dependencies": ["optional"]
            }]),
            "data/mods/optional/modinfo.json": json_file([{
                "type": "MOD_INFO", "ident": "optional",
                "dependencies": []
            }])
        }
        metadata = load_mod_metadata(legacy_files)
        self.assertIn("dev:default", metadata)
        self.assertIn("optional", default_enabled_mods(metadata))
        default_index = load_builtin_mod_indexes(
            legacy_files, metadata
        )["dev:default"]
        self.assertIn(
            EntityKey("MOD_INFO", "mod_id", "dev:default"),
            default_index.entities
        )

        matching_dual_fields = dict(legacy_files)
        matching_dual_fields[DEFAULT_MOD_METADATA_PATH] = json_file([{
            "type": "MOD_INFO", "ident": "dev:default",
            "id": "dev:default", "dependencies": ["optional"]
        }])
        self.assertIn(
            "dev:default", load_mod_metadata(matching_dual_fields)
        )

        conflicting_fields = dict(legacy_files)
        conflicting_fields[DEFAULT_MOD_METADATA_PATH] = json_file([{
            "type": "MOD_INFO", "ident": "spoofed-default",
            "id": "dev:default", "dependencies": []
        }])
        with self.assertRaisesRegex(
            AuditFailure, "conflicting MOD_INFO ident"
        ):
            load_mod_metadata(conflicting_fields)

    def test_builtin_mod_allowlists_are_scoped_and_exact(self):
        baseline_files = self.mod_tree({
            "alpha": [{"type": "thing", "id": "shared", "value": 1}],
            "beta": [{"type": "thing", "id": "shared", "value": 1}]
        })
        target_files = self.mod_tree({
            "alpha": [{"type": "thing", "id": "shared", "value": 2}],
            "beta": [{"type": "thing", "id": "shared", "value": 3}]
        })
        target_metadata = load_mod_metadata(target_files)
        target_indexes = load_builtin_mod_indexes(
            target_files, target_metadata
        )
        key = EntityKey("thing", "id", "shared")
        alpha_entry = {
            "mod_id": "alpha", "type": "thing", "id": "shared",
            "target_fingerprint": entity_fingerprint(
                target_indexes["alpha"].entities[key]
            ),
            "reason": "alpha fixture change"
        }
        summary = self.audit_mod_trees(
            baseline_files, target_files, [alpha_entry]
        )
        unallowlisted = [
            error for error in summary.errors
            if "unallowlisted built-in mod" in error
        ]
        self.assertEqual(1, len(unallowlisted))
        self.assertIn("beta", unallowlisted[0])

        beta_entry = {
            "mod_id": "beta", "type": "thing", "id": "shared",
            "target_fingerprint": entity_fingerprint(
                target_indexes["beta"].entities[key]
            ),
            "reason": "beta fixture change"
        }
        summary = self.audit_mod_trees(
            baseline_files, target_files, [alpha_entry, beta_entry]
        )
        self.assertEqual([], summary.errors)
        self.assertEqual(
            2,
            sum(len(result.statuses) for result in summary.results)
        )

        alpha_entry["target_fingerprint"] = "0" * 64
        summary = self.audit_mod_trees(
            baseline_files, target_files, [alpha_entry, beta_entry]
        )
        self.assertTrue(any(
            "fingerprint mismatch" in error for error in summary.errors
        ))

    def test_builtin_mod_resources_fail_closed(self):
        definitions = {
            "alpha": [{"type": "thing", "id": "stable"}]
        }
        baseline_files = self.mod_tree(
            definitions, {"alpha": {"readme.txt": b"old\r\n"}}
        )
        target_files = self.mod_tree(
            definitions, {"alpha": {"readme.txt": b"new\n"}}
        )
        summary = self.audit_mod_trees(baseline_files, target_files)
        self.assertTrue(any(
            "unallowlisted built-in mod alpha resource change" in error
            for error in summary.errors
        ))

        resource_path = "data/mods/alpha/readme.txt"
        resource_entry = {
            "mod_id": "alpha", "path": resource_path,
            "target_fingerprint": normalized_blob_fingerprint(b"new\n"),
            "reason": "fixture resource update"
        }
        summary = self.audit_mod_trees(
            baseline_files, target_files,
            resource_changes=[resource_entry]
        )
        self.assertEqual([], summary.errors)

        missing_resource_files = self.mod_tree(definitions)
        summary = self.audit_mod_trees(
            baseline_files, missing_resource_files
        )
        self.assertTrue(any(
            "baseline built-in mod alpha path disappeared" in error and
            resource_path in error
            for error in summary.errors
        ))

    def test_builtin_mod_identity_and_package_removal_fail_closed(self):
        baseline_files = self.mod_tree({
            "alpha": [{"type": "thing", "id": "kept"}],
            "beta": [{"type": "thing", "id": "removed"}]
        })
        missing_identity_files = self.mod_tree({
            "alpha": [{"type": "thing", "id": "kept"}],
            "beta": [{"type": "thing", "id": "replacement"}]
        })
        summary = self.audit_mod_trees(
            baseline_files, missing_identity_files
        )
        self.assertTrue(any(
            "baseline built-in mod beta entity disappeared" in error and
            "thing id=removed" in error
            for error in summary.errors
        ))

        missing_files = self.mod_tree({
            "alpha": [{"type": "thing", "id": "kept"}]
        })
        summary = self.audit_mod_trees(baseline_files, missing_files)
        self.assertEqual(("beta",), summary.missing_mods)
        self.assertTrue(any(
            "baseline built-in mod disappeared: beta" in error
            for error in summary.errors
        ))

        duplicate_files = self.mod_tree({
            "alpha": [{"type": "thing", "id": "kept"}],
            "gamma": [
                {"type": "thing", "id": "duplicate", "value": 1},
                {"type": "thing", "id": "duplicate", "value": 2}
            ]
        })
        alpha_only = self.mod_tree({
            "alpha": [{"type": "thing", "id": "kept"}]
        })
        summary = self.audit_mod_trees(alpha_only, duplicate_files)
        self.assertEqual(("gamma",), summary.added_mods)
        self.assertTrue(any(
            "new built-in mod gamma entity has multiple target definitions"
            in error and "thing id=duplicate" in error
            for error in summary.errors
        ))

    def test_optional_tree_fingerprint_normalizes_line_endings(self):
        lf_files = {"data/mods/example/readme.txt": b"one\ntwo\n"}
        crlf_files = {"data/mods/example/readme.txt": b"one\r\ntwo\r\n"}
        self.assertEqual(
            normalized_tree_fingerprint(lf_files, "data/mods/example"),
            normalized_tree_fingerprint(crlf_files, "data/mods/example")
        )


def run_self_tests():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        AdditiveAuditSelfTests
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


def parse_arguments(arguments):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        help="repository root (default: discover from current directory)"
    )
    parser.add_argument(
        "--target", default="HEAD",
        help=(
            "Git tree-ish to audit, or WORKTREE for current files "
            "(default: HEAD)"
        )
    )
    parser.add_argument(
        "--manifest",
        help="manifest path (default: tools/additive_audit_manifest.json)"
    )
    parser.add_argument(
        "--self-test", action="store_true",
        help=(
            "run focused in-process regression tests instead of a "
            "repository audit"
        )
    )
    return parser.parse_args(arguments)


def main(arguments=None):
    options = parse_arguments(arguments)
    if options.self_test:
        return run_self_tests()
    try:
        repo_root = find_repo_root(options.repo)
        manifest_path = (
            Path(options.manifest).resolve() if options.manifest else
            repo_root / "tools" / "additive_audit_manifest.json"
        )
        return execute_audit(repo_root, options.target, manifest_path)
    except AuditFailure as error:
        print("FAIL additive audit: {}".format(error))
        return 2


if __name__ == "__main__":
    sys.exit(main())
