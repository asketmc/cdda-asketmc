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
        cls.makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    def test_all_actions_are_pinned_to_full_commit(self) -> None:
        uses = re.findall(r"^\s+(?:- )?uses:\s*([^\s#]+)", self.workflow, flags=re.MULTILINE)
        self.assertGreaterEqual(len(uses), 8)
        for action in uses:
            self.assertRegex(action, r"^[^@]+@[0-9a-f]{40}$")

    def test_release_is_tag_gated_and_main_ancestry_checked(self) -> None:
        self.assertIn('tags:\n      - "v0.G-additive-*"', self.workflow)
        self.assertIn('git merge-base --is-ancestor "${GITHUB_SHA}" origin/main', self.workflow)
        self.assertIn("env.RELEASE_BUILD == 'true'", self.workflow)

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
        self.assertIn('test "${#remote_assets[@]}" -eq 3', self.workflow)
        self.assertIn('cmp "${asset}" "existing/${asset_name}"', self.workflow)
        self.assertIn("sha256sum --check SHA256SUMS.txt", self.workflow)

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
            "subject-path: cdda-0g-additive-asketmc-*-windows-x64-tiles-sound.zip", publish
        )

    def test_run_blocks_do_not_interpolate_workflow_context(self) -> None:
        self.assertNotIn("[regex]::Escape('${{", self.workflow)
        self.assertIn("EXPECTED_SHA: ${{ github.sha }}", self.workflow)
        self.assertIn("[regex]::Escape($env:EXPECTED_SHA)", self.workflow)


if __name__ == "__main__":
    unittest.main()
