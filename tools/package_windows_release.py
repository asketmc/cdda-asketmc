#!/usr/bin/env python3

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import shutil
import sys
import tempfile
import zipfile


def zip_timestamp(source_date_epoch: int) -> tuple[int, int, int, int, int, int]:
    timestamp = dt.datetime.fromtimestamp(source_date_epoch, tz=dt.timezone.utc)
    if timestamp.year < 1980:
        timestamp = timestamp.replace(year=1980, month=1, day=1, hour=0, minute=0, second=0)
    return (
        timestamp.year,
        timestamp.month,
        timestamp.day,
        timestamp.hour,
        timestamp.minute,
        timestamp.second,
    )


def package(source_dir: pathlib.Path, output: pathlib.Path, source_date_epoch: int) -> None:
    source_dir = source_dir.resolve(strict=True)
    if not source_dir.is_dir():
        raise ValueError(f"distribution source is not a directory: {source_dir}")

    files = sorted(
        (path for path in source_dir.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(source_dir).as_posix(),
    )
    if not files:
        raise ValueError("distribution source contains no files")

    output.parent.mkdir(parents=True, exist_ok=True)
    timestamp = zip_timestamp(source_date_epoch)
    with tempfile.NamedTemporaryFile(
        prefix=output.name + ".", suffix=".tmp", dir=output.parent, delete=False
    ) as temp_file:
        temp_path = pathlib.Path(temp_file.name)

    try:
        # Stored entries avoid zlib-version-dependent bytes on hosted-runner reruns.
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_STORED) as archive:
            for path in files:
                relative = path.relative_to(source_dir).as_posix()
                info = zipfile.ZipInfo(relative, date_time=timestamp)
                info.compress_type = zipfile.ZIP_STORED
                info.create_system = 3
                mode = 0o755 if path.name.lower().endswith(".exe") else 0o644
                info.external_attr = (0o100000 | mode) << 16
                info.extra = b""
                info.comment = b""
                with path.open("rb") as source, archive.open(info, "w", force_zip64=True) as target:
                    shutil.copyfileobj(source, target, length=1024 * 1024)
        temp_path.replace(output)
    finally:
        temp_path.unlink(missing_ok=True)


def verify(
    archive_path: pathlib.Path,
    commit_sha: str,
    version: str,
    release_tag: str | None = None,
) -> None:
    with zipfile.ZipFile(archive_path, "r") as archive:
        names = archive.namelist()
        if names != sorted(names):
            raise ValueError("archive entries are not sorted")
        if len(names) != len(set(names)):
            raise ValueError("archive contains duplicate entries")

        required = {
            "cataclysm-tiles.exe",
            "VERSION.txt",
            "BUILD_MANIFEST.txt",
            "README.md",
            "LICENSE.txt",
            "data/core/game_balance.json",
            "data/json/items/ammo.json",
            "data/mods/dda/modinfo.json",
            "gfx/UltimateCataclysm/tileset.txt",
        }
        missing = sorted(required - set(names))
        if missing:
            raise ValueError(f"archive is missing required entries: {', '.join(missing)}")

        version_text = archive.read("VERSION.txt").decode("utf-8")
        manifest_text = archive.read("BUILD_MANIFEST.txt").decode("utf-8")
        if commit_sha not in version_text or commit_sha not in manifest_text:
            raise ValueError("archive provenance does not contain the full commit SHA")
        if version not in version_text:
            raise ValueError("archive VERSION.txt does not contain the requested version")
        if archive.getinfo("cataclysm-tiles.exe").file_size <= 0:
            raise ValueError("archive executable is empty")

        if release_tag is not None:
            release_documents = {
                "CHANGELOG.md",
                "PATCHNOTES_ADDITIVE_0G.md",
                "RELEASE_METADATA.json",
                "RELEASE_NOTES.md",
            }
            missing_documents = sorted(release_documents - set(names))
            if missing_documents:
                raise ValueError(
                    "archive is missing release documents: " + ", ".join(missing_documents)
                )
            try:
                metadata = json.loads(archive.read("RELEASE_METADATA.json").decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ValueError("archive release metadata is invalid JSON") from error
            if not isinstance(metadata, dict):
                raise ValueError("archive release metadata is not an object")
            if metadata.get("tag") != release_tag or metadata.get("commit") != commit_sha:
                raise ValueError("archive release metadata tag or commit mismatch")
            documents = metadata.get("documents")
            if not isinstance(documents, dict) or set(documents) != {
                "CHANGELOG.md",
                "PATCHNOTES_ADDITIVE_0G.md",
                "RELEASE_NOTES.md",
            }:
                raise ValueError("archive release metadata has the wrong document set")
            for name, expected_hash in documents.items():
                actual_hash = hashlib.sha256(archive.read(name)).hexdigest()
                if actual_hash != expected_hash:
                    raise ValueError(f"archive release document hash mismatch: {name}")

        timestamps = {entry.date_time for entry in archive.infolist()}
        if len(timestamps) != 1:
            raise ValueError("archive entries do not share one normalized timestamp")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--release-tag")
    parser.add_argument("first")
    parser.add_argument("second")
    parser.add_argument("third")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.verify:
        verify(pathlib.Path(args.first), args.second, args.third, args.release_tag)
    elif args.release_tag is not None:
        raise ValueError("--release-tag is only valid with --verify")
    else:
        package(pathlib.Path(args.first), pathlib.Path(args.second), int(args.third))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
