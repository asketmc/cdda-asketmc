import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class WindowsReleaseWorkflowContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = (ROOT / ".github" / "workflows" / "windows-release.yml").read_text(
            encoding="utf-8"
        )
        cls.quality = (ROOT / ".github" / "workflows" / "quality.yml").read_text(
            encoding="utf-8"
        )
        cls.makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        cls.tests_makefile = (ROOT / "tests" / "Makefile").read_text(encoding="utf-8")

    def test_all_actions_are_pinned_to_full_commit(self) -> None:
        uses = re.findall(r"^\s+(?:- )?uses:\s*([^\s#]+)", self.workflow, flags=re.MULTILINE)
        self.assertGreaterEqual(len(uses), 8)
        for action in uses:
            self.assertRegex(action, r"^[^@]+@[0-9a-f]{40}$")

    def test_release_is_tag_gated_and_main_ancestry_checked(self) -> None:
        self.assertIn('tags:\n      - "v0.G-additive-*"', self.workflow)
        self.assertIn('git merge-base --is-ancestor "${GITHUB_SHA}" origin/main', self.workflow)
        self.assertIn("env.RELEASE_BUILD == 'true'", self.workflow)
        self.assertIn("release_changelog.py validate-tag", self.workflow)
        self.assertIn("--expected-commit \"${GITHUB_SHA}\"", self.workflow)

    def test_release_boundary_fails_before_toolchain_acquisition(self) -> None:
        boundary = self.workflow.index(
            "- name: Verify reviewed release boundary before toolchain acquisition"
        )
        documents = self.workflow.index("- name: Prepare reviewed release documents")
        host_tools = self.workflow.index("- name: Install host tools")
        restore_toolchain = self.workflow.index("- name: Restore MXE archives")
        self.assertLess(boundary, documents)
        self.assertLess(documents, host_tools)
        self.assertLess(host_tools, restore_toolchain)
        self.assertIn("gh release view \"${previous_release}\"", self.workflow)
        self.assertNotIn("git tag --sort", self.workflow)

    def test_pull_requests_do_not_save_or_upload_build_outputs(self) -> None:
        save_conditions = re.findall(
            r"- name: Save .*?\n\s+if: ([^\n]+)", self.workflow, flags=re.DOTALL
        )
        self.assertEqual(len(save_conditions), 2)
        self.assertTrue(all("github.event_name != 'pull_request'" in condition for condition in save_conditions))
        upload_section = self.workflow[self.workflow.index("- name: Stage tagged release bundle") :]
        self.assertIn("if: env.RELEASE_BUILD == 'true'", upload_section)

    def test_exact_zip_is_validated_before_prerelease(self) -> None:
        validation = self.workflow[
            self.workflow.index("  validate-windows-release:") :
            self.workflow.index("  publish-release:")
        ]
        self.assertIn("Expected exactly one release archive", validation)
        self.assertIn(
            "$checkMods = Start-Process -FilePath '.\\cataclysm-tiles.exe' "
            "-ArgumentList @('--check-mods', 'dda') -NoNewWindow -Wait -PassThru",
            validation,
        )
        self.assertIn(
            'if ($checkMods.ExitCode -ne 0) { throw "--check-mods dda failed with exit code '
            '$($checkMods.ExitCode)" }',
            validation,
        )
        self.assertNotIn("$LASTEXITCODE", validation)
        self.assertIn("needs: validate-windows-release", self.workflow)
        self.assertIn("--prerelease", self.workflow)
        self.assertNotIn("--clobber", self.workflow)
        self.assertIn("cmp SHA256SUMS.txt existing/SHA256SUMS.txt", self.workflow)

    def test_release_build_compares_two_build_outputs(self) -> None:
        self.assertIn('test "${first_exe}" = "${second_exe}"', self.workflow)
        self.assertIn('test "${first_zip}" = "${second_zip}"', self.workflow)
        self.assertIn('build_distribution "${second_prefix}" 0', self.workflow)
        self.assertIn('export SOURCE_DATE_EPOCH="${source_epoch}"', self.workflow)
        compare_archives = self.workflow.index('test "${first_zip}" = "${second_zip}"')
        build_tests = self.workflow.index('TEST_SOURCES="test_main.cpp')
        self.assertLess(compare_archives, build_tests)

    def test_manual_dispatch_uploads_a_downloadable_build(self) -> None:
        start = self.workflow.index("- name: Stage requested Windows build")
        end = self.workflow.index("- name: Stage tagged release bundle")
        stage = self.workflow[start:end]
        self.assertLess(
            self.workflow.index("- name: Build and package Windows distribution"),
            start,
        )
        self.assertIn("if: github.event_name == 'workflow_dispatch'", stage)
        self.assertIn("uses: actions/upload-artifact@", stage)
        self.assertIn("name: windows-build-${{ github.sha }}", stage)
        self.assertIn("release-output/cdda-0g-additive-asketmc-*-windows-x64-tiles-sound.zip", stage)
        self.assertIn("release-output/SHA256SUMS.txt", stage)
        self.assertIn("release-output/BUILD_MANIFEST.txt", stage)
        self.assertIn("if-no-files-found: error", stage)
        self.assertIn("retention-days: 1", stage)

    def test_focused_gameplay_catch_gates_execute_and_fail_closed(self) -> None:
        self.assertIn("sudo apt-get install --yes ccache wine64", self.workflow)
        self.assertIn(
            'TEST_SOURCES="test_main.cpp fake_messages.cpp map_helpers.cpp player_helpers.cpp advanced_inventory_test.cpp butchery_progress_test.cpp climbing_test.cpp npc_hostility_test.cpp"',
            self.workflow,
        )
        self.assertIn('"${test_bin}"', self.workflow)
        self.assertIn('"[climbing][z-level]"', self.workflow)
        self.assertIn('"[npc][morale][hostility]"', self.workflow)
        self.assertIn(
            '"[advanced_inventory][backport],[inventory][sorting][backport],[inventory][numeric][backport]"',
            self.workflow,
        )
        self.assertIn('"[butchery][progress]"', self.workflow)
        self.assertIn("timeout 10m", self.workflow)
        self.assertIn('("climbing", "climbing-test-results.xml")', self.workflow)
        self.assertIn('("NPC hostility", "npc-hostility-test-results.xml")', self.workflow)
        self.assertIn('("inventory transfer", "inventory-test-results.xml")', self.workflow)
        self.assertIn('("butchery progress", "butchery-test-results.xml")', self.workflow)
        self.assertIn("gate discovered zero test cases", self.workflow)
        self.assertIn("gate reported", self.workflow)
        self.assertIn("ifdef TEST_SOURCES", self.tests_makefile)
        self.assertIn("SOURCES = $(TEST_SOURCES)", self.tests_makefile)

    def test_reviewed_documents_are_inside_and_outside_the_archive(self) -> None:
        build = self.workflow[
            self.workflow.index("- name: Build and package Windows distribution") :
            self.workflow.index("- name: Save compiler cache for trusted events")
        ]
        for name in (
            "CHANGELOG.md",
            "PATCHNOTES_ADDITIVE_0G.md",
            "RELEASE_METADATA.json",
            "RELEASE_NOTES.md",
        ):
            self.assertIn(name, build)
        copy_notes = build.index('cp release-source/RELEASE_NOTES.md "${dist_dir}/RELEASE_NOTES.md"')
        package = build.index("python3 tools/package_windows_release.py \\")
        self.assertLess(copy_notes, package)
        self.assertIn('--release-tag "${GITHUB_REF_NAME}"', build)
        self.assertIn("release_changelog.py build-asset-manifest", build)
        self.assertIn("| LC_ALL=C sort -k2 > SHA256SUMS.txt", build)

    def test_make_staging_contract_is_used_without_make_zip(self) -> None:
        self.assertRegex(self.makefile, r"(?m)^BINDIST_DIR = \$\(BUILD_PREFIX\)bindist$")
        self.assertIn('dist_dir="${build_prefix}bindist"', self.workflow)
        self.assertIn('"JSON_FORMATTER_BIN=${build_prefix}json_formatter.exe"', self.workflow)
        self.assertIn("BINDIST_CMD=:", self.workflow)
        self.assertNotIn('dist_dir="cataclysmdda-${version}"', self.workflow)

    def test_cached_toolchains_are_verified_before_save(self) -> None:
        verify = self.workflow.index("- name: Verify MXE archives")
        save = self.workflow.index("- name: Save verified MXE archives")
        install = self.workflow.index("- name: Install verified MXE toolchain")
        self.assertLess(verify, save)
        self.assertLess(save, install)

    def test_existing_release_requires_exact_assets_and_bytes(self) -> None:
        self.assertIn('test "${#remote_assets[@]}" -eq 5', self.workflow)
        self.assertIn('cmp "${asset}" "existing/${asset_name}"', self.workflow)
        self.assertIn("cmp RELEASE_MANIFEST.json existing/RELEASE_MANIFEST.json", self.workflow)
        self.assertIn("cmp RELEASE_NOTES.md existing/RELEASE_NOTES.md", self.workflow)
        self.assertIn("cmp RELEASE_NOTES.md existing/RELEASE_BODY.md", self.workflow)
        self.assertIn("sha256sum --check SHA256SUMS.txt", self.workflow)
        self.assertNotIn("--clobber", self.workflow)

    def test_release_body_comes_only_from_reviewed_manifest(self) -> None:
        self.assertIn("release_changelog.py render-release", self.workflow)
        self.assertIn("--notes-file RELEASE_NOTES.md", self.workflow)
        self.assertNotIn("This remains a prerelease", self.workflow)
        self.assertNotIn("cat > RELEASE_NOTES.md", self.workflow)

    def test_staged_and_published_asset_sets_are_complete(self) -> None:
        stage = self.workflow[
            self.workflow.index("- name: Stage tagged release bundle") :
            self.workflow.index("  validate-windows-release:")
        ]
        for name in (
            "BUILD_MANIFEST.txt",
            "RELEASE_MANIFEST.json",
            "RELEASE_NOTES.md",
            "SHA256SUMS.txt",
        ):
            self.assertIn(f"release-output/{name}", stage)
        self.assertIn(
            '"${asset}" BUILD_MANIFEST.txt RELEASE_MANIFEST.json RELEASE_NOTES.md SHA256SUMS.txt',
            self.workflow,
        )

    def test_quality_gate_uses_exact_pr_identity_and_full_history(self) -> None:
        self.assertIn("fetch-depth: 0", self.quality)
        self.assertIn(
            "ref: ${{ github.event.pull_request.head.sha || github.sha }}", self.quality
        )
        self.assertIn("tools.test_release_changelog", self.quality)
        self.assertIn("release_changelog.py lint --check-generated", self.quality)
        self.assertIn("PR_BASE_SHA: ${{ github.event.pull_request.base.sha }}", self.quality)
        self.assertIn("PR_HEAD_SHA: ${{ github.event.pull_request.head.sha }}", self.quality)
        self.assertIn("PR_NUMBER: ${{ github.event.pull_request.number }}", self.quality)
        self.assertIn("PUSH_BEFORE_SHA: ${{ github.event.before }}", self.quality)
        self.assertIn("PUSH_HEAD_SHA: ${{ github.sha }}", self.quality)
        self.assertIn('--base "${PR_BASE_SHA}"', self.quality)
        self.assertIn('--head "${PR_HEAD_SHA}"', self.quality)
        self.assertIn('--pr "${PR_NUMBER}"', self.quality)
        self.assertIn("release_changelog.py check-main", self.quality)
        self.assertIn('--base "${PUSH_BEFORE_SHA}"', self.quality)
        self.assertIn('--head "${PUSH_HEAD_SHA}"', self.quality)

    def test_new_and_existing_releases_share_exact_remote_readback(self) -> None:
        build = self.workflow[self.workflow.index("  publish-release:") :]
        superseded = build.index("release_changelog.py verify-superseded-release")
        create = build.index('gh release create "${GITHUB_REF_NAME}"')
        readback = build.index('mkdir existing')
        self.assertLess(superseded, create)
        self.assertLess(create, readback)
        self.assertEqual(build.count("mkdir existing"), 1)
        self.assertEqual(build.count("cmp RELEASE_NOTES.md existing/RELEASE_NOTES.md"), 1)
        self.assertIn(
            "--jq '.body | @base64' | base64 --decode > existing/RELEASE_BODY.md",
            build,
        )

    def test_every_job_declares_least_privilege_permissions(self) -> None:
        jobs = re.split(r"(?m)^  (?=[a-z][a-z0-9-]*:$)", self.workflow.split("\njobs:\n", 1)[1])
        job_blocks = [block for block in jobs if block.strip()]
        self.assertEqual(len(job_blocks), 3)
        for block in job_blocks:
            job_name = block.split(":", 1)[0]
            self.assertIn("    permissions:\n", block, f"{job_name} has no explicit permissions")

    def test_only_the_publish_job_may_write(self) -> None:
        self.assertEqual(self.workflow.count("contents: write"), 1)
        publish = self.workflow[self.workflow.index("  publish-release:") :]
        self.assertIn("contents: write", publish)

    def test_release_archive_gets_build_provenance(self) -> None:
        publish = self.workflow[self.workflow.index("  publish-release:") :]
        self.assertIn("actions/attest-build-provenance@", publish)
        self.assertIn("id-token: write", publish)
        self.assertIn("attestations: write", publish)
        self.assertIn(
            "subject-path: release-output/cdda-0g-additive-asketmc-*-windows-x64-tiles-sound.zip",
            publish,
        )

    def test_run_blocks_do_not_interpolate_workflow_context(self) -> None:
        self.assertNotIn("[regex]::Escape('${{", self.workflow)
        self.assertIn("EXPECTED_SHA: ${{ github.sha }}", self.workflow)
        self.assertIn("[regex]::Escape($env:EXPECTED_SHA)", self.workflow)


if __name__ == "__main__":
    unittest.main()
