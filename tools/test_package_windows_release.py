import hashlib
import json
import pathlib
import tempfile
import unittest
import zipfile

from tools import package_windows_release


class WindowsReleasePackagingTest(unittest.TestCase):
    @staticmethod
    def _write_minimum_distribution(source: pathlib.Path, commit: str, version: str) -> None:
        for directory in (
            source / "data" / "core",
            source / "data" / "json" / "items",
            source / "data" / "mods" / "dda",
            source / "gfx" / "UltimateCataclysm",
        ):
            directory.mkdir(parents=True)
        (source / "cataclysm-tiles.exe").write_bytes(b"PE-test")
        (source / "VERSION.txt").write_text(
            f"version: {version}\ncommit sha: {commit}\n", encoding="utf-8"
        )
        (source / "BUILD_MANIFEST.txt").write_text(
            f"commit sha: {commit}\n", encoding="utf-8"
        )
        (source / "README.md").write_text("readme\n", encoding="utf-8")
        (source / "LICENSE.txt").write_text("license\n", encoding="utf-8")
        (source / "data" / "core" / "game_balance.json").write_text("{}\n", encoding="utf-8")
        (source / "data" / "json" / "items" / "ammo.json").write_text("[]\n", encoding="utf-8")
        (source / "data" / "mods" / "dda" / "modinfo.json").write_text("[]\n", encoding="utf-8")
        (source / "gfx" / "UltimateCataclysm" / "tileset.txt").write_text(
            "NAME: UltimateCataclysm\n", encoding="utf-8"
        )

    def test_packaging_is_deterministic_and_verified(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            source = root / "dist"
            commit = "a" * 40
            version = "0.G-additive-" + commit[:12]
            self._write_minimum_distribution(source, commit, version)

            first = root / "first.zip"
            second = root / "second.zip"
            epoch = 1_700_000_000
            package_windows_release.package(source, first, epoch)

            for path in source.rglob("*"):
                if path.is_file():
                    path.touch()
            package_windows_release.package(source, second, epoch)

            self.assertEqual(
                hashlib.sha256(first.read_bytes()).digest(),
                hashlib.sha256(second.read_bytes()).digest(),
            )
            package_windows_release.verify(first, commit, version)

            with zipfile.ZipFile(first) as archive:
                self.assertEqual(archive.namelist(), sorted(archive.namelist()))
                self.assertEqual(len({info.date_time for info in archive.infolist()}), 1)
                self.assertEqual(
                    archive.getinfo("cataclysm-tiles.exe").external_attr >> 16,
                    0o100755,
                )

    def test_release_documents_are_required_and_hash_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            source = root / "dist"
            commit = "d" * 40
            version = "0.G-additive-" + commit[:12]
            tag = "v0.G-additive-2026.08.27"
            self._write_minimum_distribution(source, commit, version)
            documents = {
                "CHANGELOG.md": b"history\n",
                "PATCHNOTES_ADDITIVE_0G.md": b"overview\n",
                "RELEASE_NOTES.md": b"release\n",
            }
            for name, data in documents.items():
                (source / name).write_bytes(data)
            metadata = {
                "tag": tag,
                "commit": commit,
                "documents": {
                    name: hashlib.sha256(data).hexdigest()
                    for name, data in documents.items()
                },
            }
            metadata_path = source / "RELEASE_METADATA.json"
            metadata_path.write_text(
                json.dumps(metadata), encoding="utf-8"
            )
            receipt_lines = [
                f"commit sha: {commit}",
                f"release notes sha256: {metadata['documents']['RELEASE_NOTES.md']}",
                f"release metadata sha256: {hashlib.sha256(metadata_path.read_bytes()).hexdigest()}",
                f"cumulative changelog sha256: {metadata['documents']['CHANGELOG.md']}",
                "cumulative overview sha256: "
                f"{metadata['documents']['PATCHNOTES_ADDITIVE_0G.md']}",
            ]
            (source / "BUILD_MANIFEST.txt").write_text(
                "\n".join(receipt_lines) + "\n", encoding="utf-8"
            )
            archive_path = root / "release.zip"
            package_windows_release.package(source, archive_path, 1_700_000_000)
            package_windows_release.verify(archive_path, commit, version, tag)

            valid_build_manifest = (source / "BUILD_MANIFEST.txt").read_bytes()
            (source / "BUILD_MANIFEST.txt").write_text(
                f"commit sha: {commit}\nrelease notes sha256: {'0' * 64}\n",
                encoding="utf-8",
            )
            package_windows_release.package(source, archive_path, 1_700_000_000)
            with self.assertRaisesRegex(ValueError, "build manifest receipt mismatch"):
                package_windows_release.verify(archive_path, commit, version, tag)

            (source / "BUILD_MANIFEST.txt").write_bytes(valid_build_manifest)
            (source / "RELEASE_NOTES.md").write_bytes(b"tampered\n")
            package_windows_release.package(source, archive_path, 1_700_000_000)
            with self.assertRaisesRegex(ValueError, "document hash mismatch"):
                package_windows_release.verify(archive_path, commit, version, tag)

            (source / "RELEASE_METADATA.json").unlink()
            package_windows_release.package(source, archive_path, 1_700_000_000)
            with self.assertRaisesRegex(ValueError, "missing release documents"):
                package_windows_release.verify(archive_path, commit, version, tag)

    def test_verifier_rejects_missing_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = pathlib.Path(temp_dir) / "bad.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                for name in (
                    "BUILD_MANIFEST.txt",
                    "LICENSE.txt",
                    "README.md",
                    "VERSION.txt",
                    "cataclysm-tiles.exe",
                    "data/core/game_balance.json",
                    "data/json/items/ammo.json",
                    "data/mods/dda/modinfo.json",
                    "gfx/UltimateCataclysm/tileset.txt",
                ):
                    archive.writestr(name, "present but no provenance")
            with self.assertRaisesRegex(ValueError, "full commit SHA"):
                package_windows_release.verify(archive_path, "b" * 40, "0.G-test")

    def test_verifier_rejects_missing_runtime_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = pathlib.Path(temp_dir) / "bad.zip"
            commit = "c" * 40
            with zipfile.ZipFile(archive_path, "w") as archive:
                for name in (
                    "BUILD_MANIFEST.txt",
                    "LICENSE.txt",
                    "README.md",
                    "VERSION.txt",
                    "cataclysm-tiles.exe",
                ):
                    archive.writestr(name, f"{commit}\n0.G-test\n")
            with self.assertRaisesRegex(ValueError, "data/core/game_balance.json"):
                package_windows_release.verify(archive_path, commit, "0.G-test")

    def test_verifier_rejects_unsafe_archive_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = pathlib.Path(temp_dir) / "bad.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("../outside.txt", "unsafe")
            with self.assertRaisesRegex(ValueError, "unsafe entry name"):
                package_windows_release.verify(archive_path, "e" * 40, "0.G-test")


if __name__ == "__main__":
    unittest.main()
