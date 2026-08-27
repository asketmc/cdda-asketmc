#!/usr/bin/env python3

"""Report pull-request line count without blocking CI."""

from __future__ import annotations

import argparse
import subprocess


WARNING_LINES = 400
OVERSIZE_LINES = 800


def parse_numstat(output: str) -> tuple[int, int, int]:
    changed_lines = 0
    text_files = 0
    binary_files = 0
    for line in output.splitlines():
        additions, deletions, _ = line.split("\t", 2)
        if additions == "-" or deletions == "-":
            binary_files += 1
            continue
        changed_lines += int(additions) + int(deletions)
        text_files += 1
    return changed_lines, text_files, binary_files


def classify(changed_lines: int) -> str:
    if changed_lines >= OVERSIZE_LINES:
        return "oversize"
    if changed_lines > WARNING_LINES:
        return "warning"
    return "ok"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()

    result = subprocess.run(
        ["git", "diff", "--numstat", f"{args.base}...{args.head}"],
        check=True,
        capture_output=True,
        text=True,
    )
    changed_lines, text_files, binary_files = parse_numstat(result.stdout)
    status = classify(changed_lines)
    message = (
        f"PR changes {changed_lines} lines across {text_files} text files; "
        f"{binary_files} binary files are not counted. "
        f"Warning threshold: {WARNING_LINES + 1}; oversize threshold: {OVERSIZE_LINES}."
    )
    print(message)
    if status != "ok":
        print(f"::warning title=PR size {status}::{message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
