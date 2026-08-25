import hashlib
import pathlib
import tempfile
import unittest
import zipfile

from tools import package_windows_release


class WindowsReleasePackagingTest(unittest.TestCase):
    def test_packaging_is_deterministic_and_verified(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            source = root / "dist"
            (source / "data").mkdir(parents=True)
            commit = "a" * 40
            version = "0.G-additive-" + commit[:12]
            (source / "cataclysm-tiles.exe").write_bytes(b"PE-test")
            (source / "VERSION.txt").write_text(
                f"version: {version}\ncommit sha: {commit}\n", encoding="utf-8"
            )
            (source / "BUILD_MANIFEST.txt").write_text(
                f"commit sha: {commit}\n", encoding="utf-8"
            )
            (source / "README.md").write_text("readme\n", encoding="utf-8")
            (source / "LICENSE.txt").write_text("license\n", encoding="utf-8")
            (source / "data" / "z.json").write_text("{}\n", encoding="utf-8")
            (source / "data" / "a.json").write_text("[]\n", encoding="utf-8")

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
                ):
                    archive.writestr(name, "present but no provenance")
            with self.assertRaisesRegex(ValueError, "full commit SHA"):
                package_windows_release.verify(archive_path, "b" * 40, "0.G-test")


if __name__ == "__main__":
    unittest.main()
