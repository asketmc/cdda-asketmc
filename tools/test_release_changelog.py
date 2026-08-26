import hashlib
import json
import pathlib
import copy
import subprocess
import tempfile
import unittest
import zipfile

from tools import release_changelog


ROOT = pathlib.Path(__file__).resolve().parents[1]


def run_git(root: pathlib.Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def commit_file(
    root: pathlib.Path,
    name: str,
    content: str,
    subject: str,
    author: str | None = None,
) -> str:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    run_git(root, "add", name)
    arguments = ["commit", "-m", subject]
    if author is not None:
        arguments.extend(["--author", author])
    run_git(root, *arguments)
    return run_git(root, "rev-parse", "HEAD")


def valid_entry(identifier: str = "entry") -> dict:
    return {
        "id": identifier,
        "category": "Bugfixes",
        "audience": "players",
        "summary": "Keep the target available.",
        "compatibility": "save-compatible",
    }


def valid_fragment(pr: int = 1) -> dict:
    return {"schema": 1, "pr": pr, "entries": [valid_entry()]}


def write_baseline_history(
    root: pathlib.Path, tag: str = "v0.G-additive-2026.08.25"
) -> tuple[dict, dict[int, dict]]:
    fragment = valid_fragment(1)
    fragment_path = root / "changelog" / "changes" / "pr-1.json"
    fragment_path.parent.mkdir(parents=True, exist_ok=True)
    fragment_path.write_bytes(release_changelog.canonical_json_bytes(fragment))
    release = {
        "schema": 1,
        "tag": tag,
        "title": "CDDA 0.G Additive baseline",
        "date": "2026-08-25",
        "previous_release": None,
        "baseline": True,
        "changes": [
            {"pr": 1, "fragment_sha256": release_changelog.object_hash(fragment)}
        ],
        "baseline_entries": [valid_entry("baseline-state")],
        "known_limits": [],
        "validation": ["Validated."],
    }
    release_dir = root / "changelog" / "releases"
    release_dir.mkdir(parents=True, exist_ok=True)
    (release_dir / "index.json").write_bytes(
        release_changelog.canonical_json_bytes({"schema": 1, "releases": [tag]})
    )
    (release_dir / f"{tag}.json").write_bytes(
        release_changelog.canonical_json_bytes(release)
    )
    release_changelog.render_all(root)
    return release, {1: fragment}


class StrictJsonAndSchemaTest(unittest.TestCase):
    def test_duplicate_keys_and_non_finite_numbers_are_rejected(self) -> None:
        with self.assertRaisesRegex(release_changelog.ChangelogError, "duplicate JSON key"):
            release_changelog.parse_json_bytes(b'{"schema": 1, "schema": 1}', "test")
        with self.assertRaisesRegex(release_changelog.ChangelogError, "non-finite"):
            release_changelog.parse_json_bytes(b'{"value": NaN}', "test")

    def test_bom_and_invalid_utf8_are_rejected(self) -> None:
        with self.assertRaisesRegex(release_changelog.ChangelogError, "BOM"):
            release_changelog.parse_json_bytes(b"\xef\xbb\xbf{}", "test")
        with self.assertRaisesRegex(release_changelog.ChangelogError, "invalid UTF-8"):
            release_changelog.parse_json_bytes(b'"\xff"', "test")

    def test_fragment_rejects_bool_integer_unknown_key_and_multiline_text(self) -> None:
        fragment = valid_fragment()
        fragment["pr"] = True
        with self.assertRaisesRegex(release_changelog.ChangelogError, "integer"):
            release_changelog.validate_fragment(fragment, "fragment")

        fragment = valid_fragment()
        fragment["unexpected"] = 1
        with self.assertRaisesRegex(release_changelog.ChangelogError, "unknown keys"):
            release_changelog.validate_fragment(fragment, "fragment")

        fragment = valid_fragment()
        fragment["entries"][0]["summary"] = "first\nsecond"
        with self.assertRaisesRegex(release_changelog.ChangelogError, "line breaks"):
            release_changelog.validate_fragment(fragment, "fragment")

    def test_fragment_requires_exactly_one_nonempty_disposition(self) -> None:
        fragment = valid_fragment()
        fragment["skip"] = {"reason": "Not published."}
        with self.assertRaisesRegex(release_changelog.ChangelogError, "exactly one"):
            release_changelog.validate_fragment(fragment, "fragment")

        fragment = {"schema": 1, "pr": 1, "entries": []}
        with self.assertRaisesRegex(release_changelog.ChangelogError, "non-empty"):
            release_changelog.validate_fragment(fragment, "fragment")

        release_changelog.validate_fragment(
            {"schema": 1, "pr": 1, "skip": {"reason": "Internal test-only change."}},
            "fragment",
        )

    def test_filename_pr_and_duplicate_entry_ids_are_rejected(self) -> None:
        with self.assertRaisesRegex(release_changelog.ChangelogError, "does not match"):
            release_changelog.validate_fragment(valid_fragment(2), "pr-1.json", 1)
        fragment = valid_fragment()
        fragment["entries"].append(valid_entry())
        with self.assertRaisesRegex(release_changelog.ChangelogError, "duplicate entry id"):
            release_changelog.validate_fragment(fragment, "fragment")


class RepositoryReleaseHistoryTest(unittest.TestCase):
    def test_hashed_release_documents_are_checked_out_with_lf(self) -> None:
        attributes = run_git(
            ROOT,
            "check-attr",
            "eol",
            "--",
            "CHANGELOG.md",
            "PATCHNOTES_ADDITIVE_0G.md",
            "changelog/releases/index.json",
            "doc/releases/v0.G-additive-2026.08.25.md",
        ).splitlines()
        self.assertEqual(
            attributes,
            [
                "CHANGELOG.md: eol: lf",
                "PATCHNOTES_ADDITIVE_0G.md: eol: lf",
                "changelog/releases/index.json: eol: lf",
                "doc/releases/v0.G-additive-2026.08.25.md: eol: lf",
            ],
        )

    def test_repository_lints_and_generated_files_are_exact(self) -> None:
        tags, releases, fragments = release_changelog.lint_repository(
            ROOT, check_generated=True
        )
        self.assertGreaterEqual(len(tags), 2)
        self.assertEqual(
            tags[-2:],
            ["v0.G-additive-2026.08.26.1", "v0.G-additive-2026.08.25"],
        )
        expected = release_changelog.expected_generated_files(ROOT, tags, releases, fragments)
        self.assertGreaterEqual(len(expected), 3)
        for path, data in expected.items():
            self.assertEqual(path.read_bytes(), data)
        expected_hashes = {
            "doc/releases/v0.G-additive-2026.08.25.md": (
                "945ecf9e6c24c57f0c188e7109fe88789f56ee2f15e0cb9308fb62ff01379d9b"
            ),
            "doc/releases/v0.G-additive-2026.08.26.1.md": (
                "602503f155503e3fbaf8113f59a3ef39a17b32693a785701d74920c6adb9b4b3"
            ),
        }
        for relative, digest in expected_hashes.items():
            self.assertEqual(
                hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), digest
            )

    def test_retro_release_range_is_exact_and_failed_tag_is_not_a_boundary(self) -> None:
        integrations = release_changelog.first_parent_integrations(
            ROOT, "v0.G-additive-2026.08.25", "v0.G-additive-2026.08.26.1"
        )
        self.assertEqual([item["pr"] for item in integrations], [4, 3, 5, 6, 7, 12, 16])
        release_changelog.validate_tag(
            ROOT,
            "v0.G-additive-2026.08.26.1",
            "d58792d89dea9af8616a7f0d7f4b0e44c0554d3a",
        )
        with self.assertRaisesRegex(release_changelog.ChangelogError, "no indexed"):
            release_changelog.validate_tag(ROOT, "v0.G-additive-2026.08.26")

    def test_bootstrap_covers_every_unreleased_main_integration(self) -> None:
        integrations = release_changelog.first_parent_integrations(
            ROOT,
            "v0.G-additive-2026.08.26.1",
            "c685ae3aafcdbcbd5b8d54d200b62aee1e633b80",
        )
        self.assertEqual([item["pr"] for item in integrations], [8, 9, 10, 11, 17])
        _, _, fragments = release_changelog.lint_repository(ROOT, True)
        self.assertTrue(all(item["pr"] in fragments for item in integrations))

    def test_release_notes_have_multiple_entries_and_no_generator_branding(self) -> None:
        _, releases, fragments = release_changelog.lint_repository(ROOT)
        notes = release_changelog.render_release(
            releases["v0.G-additive-2026.08.26.1"], fragments
        )
        self.assertIn("Recover from Windows audio", notes)
        self.assertIn("Let NPC mopping jobs", notes)
        self.assertIn("Preserve pickup descriptions", notes)
        self.assertNotIn("generated by AI", notes.lower())
        self.assertNotIn("language model", notes.lower())

    def test_fragment_hash_change_invalidates_historical_release(self) -> None:
        tags, releases, fragments = release_changelog.lint_repository(ROOT)
        changed = copy.deepcopy(fragments)
        changed[3]["entries"][0]["summary"] = "Changed after publication."
        with self.assertRaisesRegex(release_changelog.ChangelogError, "hash mismatch"):
            release_changelog.verify_release_fragment_links(tags, releases, changed)

    def test_rendering_is_stable_and_markdown_is_escaped(self) -> None:
        _, releases, fragments = release_changelog.lint_repository(ROOT)
        first = release_changelog.render_release(releases["v0.G-additive-2026.08.25"], fragments)
        second = release_changelog.render_release(releases["v0.G-additive-2026.08.25"], fragments)
        self.assertEqual(first.encode(), second.encode())
        self.assertEqual(hashlib.sha256(first.encode()).digest(), hashlib.sha256(second.encode()).digest())
        self.assertIn("PATCHNOTES\\_ADDITIVE\\_0G.md", first)

    def test_explicit_skip_renders_its_reviewed_reason(self) -> None:
        release = {
            "title": "Test release",
            "date": "2026-08-27",
            "baseline": False,
            "previous_release": "v0.G-additive-2026.08.26.1",
            "baseline_entries": [],
            "changes": [{"pr": 99, "fragment_sha256": "0" * 64}],
            "known_limits": [],
            "validation": ["Validated."],
        }
        fragments = {
            99: {
                "schema": 1,
                "pr": 99,
                "skip": {"reason": "Internal test-only adjustment."},
            }
        }
        notes = release_changelog.render_release(release, fragments)
        self.assertIn("## Intentionally omitted", notes)
        self.assertIn("[PR #99]", notes)
        self.assertIn("Internal test-only adjustment.", notes)


class GitCoverageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temporary.name)
        run_git(self.root, "init", "-b", "main")
        run_git(self.root, "config", "user.email", "tests@example.invalid")
        run_git(self.root, "config", "user.name", "Release Tests")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_merge_and_squash_integrations_are_classified_in_first_parent_order(self) -> None:
        start = commit_file(self.root, "root.txt", "root\n", "Root")
        run_git(self.root, "checkout", "-b", "feature")
        commit_file(self.root, "feature.txt", "feature\n", "Feature work")
        run_git(self.root, "checkout", "main")
        run_git(
            self.root,
            "merge",
            "--no-ff",
            "feature",
            "-m",
            "Merge pull request #41 from owner/feature",
        )
        commit_file(self.root, "squash.txt", "squash\n", "Second feature (#42)")
        integrations = release_changelog.first_parent_integrations(self.root, start, "HEAD")
        self.assertEqual(
            [(item["pr"], item["style"]) for item in integrations],
            [(41, "merge"), (42, "squash")],
        )

    def test_direct_commit_and_second_parent_boundary_fail_closed(self) -> None:
        root_commit = commit_file(self.root, "root.txt", "root\n", "Root")
        run_git(self.root, "checkout", "-b", "feature")
        second_parent = commit_file(self.root, "feature.txt", "feature\n", "Feature")
        run_git(self.root, "checkout", "main")
        commit_file(self.root, "main.txt", "main\n", "Main work (#50)")
        run_git(
            self.root,
            "merge",
            "--no-ff",
            "feature",
            "-m",
            "Merge pull request #51 from owner/feature",
        )
        with self.assertRaisesRegex(release_changelog.ChangelogError, "exact first-parent"):
            release_changelog.first_parent_integrations(self.root, second_parent, "HEAD")

        commit_file(self.root, "direct.txt", "direct\n", "Unreviewed direct commit")
        with self.assertRaisesRegex(release_changelog.ChangelogError, "not a recognized"):
            release_changelog.first_parent_integrations(self.root, root_commit, "HEAD")

    def test_multi_commit_rebase_fails_closed(self) -> None:
        start = commit_file(self.root, "root.txt", "root\n", "Root")
        commit_file(self.root, "part-one.txt", "one\n", "Feature part one (#52)")
        commit_file(self.root, "part-two.txt", "two\n", "Feature part two (#52)")
        with self.assertRaisesRegex(release_changelog.ChangelogError, "rebase merges"):
            release_changelog.first_parent_integrations(self.root, start, "HEAD")

    def test_octopus_merge_fails_closed(self) -> None:
        start = commit_file(self.root, "root.txt", "root\n", "Root")
        run_git(self.root, "checkout", "-b", "feature-a")
        commit_file(self.root, "a.txt", "a\n", "A")
        run_git(self.root, "checkout", "main")
        run_git(self.root, "checkout", "-b", "feature-b")
        commit_file(self.root, "b.txt", "b\n", "B")
        run_git(self.root, "checkout", "main")
        run_git(
            self.root,
            "merge",
            "--no-ff",
            "feature-a",
            "feature-b",
            "-m",
            "Merge pull request #53 from owner/octopus",
        )
        with self.assertRaisesRegex(release_changelog.ChangelogError, "not a recognized"):
            release_changelog.first_parent_integrations(self.root, start, "HEAD")

    def test_pr_gate_accepts_one_new_fragment_and_rejects_old_fragment_edits(self) -> None:
        fragment_path = self.root / "changelog" / "changes" / "pr-1.json"
        fragment_path.parent.mkdir(parents=True)
        fragment_path.write_bytes(release_changelog.canonical_json_bytes(valid_fragment(1)))
        run_git(self.root, "add", ".")
        run_git(self.root, "commit", "-m", "Bootstrap (#1)")
        base = run_git(self.root, "rev-parse", "HEAD")

        (fragment_path.parent / "pr-2.json").write_bytes(
            release_changelog.canonical_json_bytes(valid_fragment(2))
        )
        run_git(self.root, "add", ".")
        run_git(self.root, "commit", "-m", "Add fragment (#2)")
        head = run_git(self.root, "rev-parse", "HEAD")
        release_changelog.check_pr(self.root, base, head, 2, "owner")
        release_changelog.check_main_update(self.root, base, head)

        fragment_path.write_bytes(release_changelog.canonical_json_bytes(valid_fragment(1) | {"skip": {"reason": "bad"}}))
        run_git(self.root, "add", ".")
        run_git(self.root, "commit", "-m", "Edit history (#3)")
        with self.assertRaisesRegex(release_changelog.ChangelogError, "immutable"):
            release_changelog.check_pr(self.root, head, "HEAD", 3, "owner")
        with self.assertRaisesRegex(release_changelog.ChangelogError, "immutable"):
            release_changelog.check_main_update(self.root, head, "HEAD")

    def test_renderer_update_may_regenerate_immutable_release_documents(self) -> None:
        write_baseline_history(self.root)
        (self.root / "CHANGELOG.md").write_text("old renderer\n", encoding="utf-8")
        historical_doc = self.root / "doc" / "releases" / "v0.G-additive-2026.08.25.md"
        historical_doc.write_text("old renderer\n", encoding="utf-8")
        run_git(self.root, "add", ".")
        run_git(self.root, "commit", "-m", "Historical renderer (#1)")
        base = run_git(self.root, "rev-parse", "HEAD")

        fragment_path = self.root / "changelog" / "changes" / "pr-2.json"
        fragment_path.write_bytes(
            release_changelog.canonical_json_bytes(valid_fragment(2))
        )
        release_changelog.render_all(self.root)
        run_git(self.root, "add", ".")
        run_git(self.root, "commit", "-m", "Refresh renderer output (#2)")
        release_changelog.check_pr(self.root, base, "HEAD", 2, "owner")

        valid_head = run_git(self.root, "rev-parse", "HEAD")
        (self.root / "changelog" / "changes" / "pr-3.json").write_bytes(
            release_changelog.canonical_json_bytes(valid_fragment(3))
        )
        historical_doc.write_text("tampered\n", encoding="utf-8")
        run_git(self.root, "add", ".")
        run_git(self.root, "commit", "-m", "Tamper with generated history (#3)")
        with self.assertRaisesRegex(release_changelog.ChangelogError, "stale"):
            release_changelog.check_pr(self.root, valid_head, "HEAD", 3, "owner")

    def test_dependabot_may_defer_fragment_to_release_preparation(self) -> None:
        fragment_path = self.root / "changelog" / "changes" / "pr-1.json"
        fragment_path.parent.mkdir(parents=True)
        fragment_path.write_bytes(release_changelog.canonical_json_bytes(valid_fragment(1)))
        run_git(self.root, "add", ".")
        run_git(self.root, "commit", "-m", "Bootstrap (#1)")
        base = run_git(self.root, "rev-parse", "HEAD")
        commit_file(
            self.root,
            "workflow.txt",
            "new\n",
            "Bump action/x from 1 to 2 (#2)",
            "dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>",
        )
        release_changelog.check_pr(
            self.root,
            base,
            "HEAD",
            2,
            "dependabot[bot]",
            "Bump action/x from 1 to 2",
        )
        with self.assertRaisesRegex(release_changelog.ChangelogError, "canonical bump title"):
            release_changelog.check_pr(
                self.root, base, "HEAD", 2, "dependabot[bot]", "Unrelated change"
            )
        release_changelog.check_main_update(self.root, base, "HEAD")
        entry = release_changelog._automatic_dependabot_entry(
            "Bump action/x from 1 to 2 (#2)", 2
        )
        self.assertIsNotNone(entry)
        self.assertEqual(entry["summary"], "Update action/x from 1 to 2.")
        self.assertIsNone(
            release_changelog._automatic_dependabot_entry("Arbitrary title (#2)", 2)
        )
        forged = dict(entry)
        forged["summary"] = "Hide an unrelated change."
        with self.assertRaisesRegex(release_changelog.ChangelogError, "canonical Dependabot"):
            release_changelog.verify_automatic_integrations(
                [{"pr": 2, "automatic": forged}],
                [
                    {
                        "pr": 2,
                        "subject": "Bump action/x from 1 to 2 (#2)",
                        "style": "squash",
                        "author_name": "dependabot[bot]",
                        "author_email": "49699333+dependabot[bot]@users.noreply.github.com",
                    }
                ],
                "release",
            )

    def test_release_pr_may_add_one_complete_delta_but_cannot_edit_history(self) -> None:
        previous_tag = "v0.G-additive-2026.08.25"
        new_tag = "v0.G-additive-2026.08.27"
        old_release, fragments = write_baseline_history(self.root, previous_tag)
        old_manifest = self.root / "changelog" / "releases" / f"{previous_tag}.json"
        run_git(self.root, "add", ".")
        run_git(self.root, "commit", "-m", "Previous release (#1)")
        run_git(self.root, "tag", previous_tag)
        commit_file(
            self.root,
            "feature.txt",
            "feature\n",
            "Bump action/x from 1 to 2 (#2)",
            "dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>",
        )
        base = run_git(self.root, "rev-parse", "HEAD")

        automatic_2 = release_changelog._automatic_dependabot_entry(
            "Bump action/x from 1 to 2 (#2)", 2
        )
        self.assertIsNotNone(automatic_2)
        release_fragment = valid_fragment(3)
        (self.root / "changelog" / "changes" / "pr-3.json").write_bytes(
            release_changelog.canonical_json_bytes(release_fragment)
        )
        new_manifest = {
            "schema": 1,
            "tag": new_tag,
            "title": "CDDA 0.G Additive 2026.08.27",
            "date": "2026-08-27",
            "previous_release": previous_tag,
            "baseline": False,
            "changes": [
                {"pr": 2, "automatic": automatic_2},
                {
                    "pr": 3,
                    "fragment_sha256": release_changelog.object_hash(release_fragment),
                },
            ],
            "baseline_entries": [],
            "known_limits": [],
            "validation": ["Validated."],
        }
        (self.root / "changelog" / "releases" / "index.json").write_bytes(
            release_changelog.canonical_json_bytes(
                {"schema": 1, "releases": [new_tag, previous_tag]}
            )
        )
        (self.root / "changelog" / "releases" / f"{new_tag}.json").write_bytes(
            release_changelog.canonical_json_bytes(new_manifest)
        )
        release_changelog.render_all(self.root)
        run_git(self.root, "add", ".")
        run_git(self.root, "commit", "-m", "Prepare release (#3)")
        release_head = run_git(self.root, "rev-parse", "HEAD")
        release_changelog._check_release_history_diff(
            self.root, base, release_head, 3, False
        )

        old_release["title"] = "Rewritten history"
        old_manifest.write_bytes(release_changelog.canonical_json_bytes(old_release))
        run_git(self.root, "add", ".")
        run_git(self.root, "commit", "-m", "Rewrite release history (#4)")
        with self.assertRaisesRegex(release_changelog.ChangelogError, "immutable"):
            release_changelog._check_release_history_diff(
                self.root, release_head, "HEAD", 4, False
            )


class ReleaseAssetBindingTest(unittest.TestCase):
    def test_release_asset_manifest_binds_external_and_embedded_documents(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = pathlib.Path(temporary)
            tag = "v0.G-additive-2026.08.26.1"
            commit = "d58792d89dea9af8616a7f0d7f4b0e44c0554d3a"
            _, releases, fragments = release_changelog.lint_repository(ROOT, True)
            notes = output / "RELEASE_NOTES.md"
            notes.write_bytes(
                release_changelog.render_release(releases[tag], fragments).encode("utf-8")
            )
            metadata = output / "RELEASE_METADATA.json"
            release_changelog.build_metadata(ROOT, tag, commit, notes, metadata)
            build_manifest = output / "BUILD_MANIFEST.txt"
            metadata_value = release_changelog.load_json(metadata)
            build_manifest.write_text(
                "\n".join(
                    [
                        f"commit sha: {commit}",
                        "release notes sha256: "
                        f"{metadata_value['documents']['RELEASE_NOTES.md']}",
                        f"release metadata sha256: {release_changelog.sha256_file(metadata)}",
                        "cumulative changelog sha256: "
                        f"{metadata_value['documents']['CHANGELOG.md']}",
                        "cumulative overview sha256: "
                        f"{metadata_value['documents']['PATCHNOTES_ADDITIVE_0G.md']}",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            archive_path = output / "release.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.write(build_manifest, "BUILD_MANIFEST.txt")
                archive.write(ROOT / "CHANGELOG.md", "CHANGELOG.md")
                archive.write(ROOT / "PATCHNOTES_ADDITIVE_0G.md", "PATCHNOTES_ADDITIVE_0G.md")
                archive.write(metadata, "RELEASE_METADATA.json")
                archive.write(notes, "RELEASE_NOTES.md")
            asset_manifest = output / "RELEASE_MANIFEST.json"
            release_changelog.build_asset_manifest(
                ROOT,
                tag,
                commit,
                archive_path,
                notes,
                build_manifest,
                metadata,
                asset_manifest,
            )
            checksum_paths = [build_manifest, asset_manifest, notes, archive_path]
            checksum_lines = [
                f"{release_changelog.sha256_file(path)}  {path.name}"
                for path in sorted(checksum_paths, key=lambda item: item.name)
            ]
            (output / "SHA256SUMS.txt").write_text(
                "\n".join(checksum_lines) + "\n", encoding="utf-8"
            )
            release_changelog.verify_assets(
                ROOT, asset_manifest, output, tag, commit
            )

            notes.write_text("tampered\n", encoding="utf-8")
            with self.assertRaisesRegex(release_changelog.ChangelogError, "wrong size|hash mismatch"):
                release_changelog.verify_assets(
                    ROOT, asset_manifest, output, tag, commit
                )


if __name__ == "__main__":
    unittest.main()
