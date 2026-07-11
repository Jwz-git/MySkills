#!/usr/bin/env python3
"""Render selected PDF pages to stable PNG files with Poppler's pdftoppm."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


def parse_pages(spec: str) -> list[int]:
    pages: set[int] = set()
    for part in spec.split(","):
        token = part.strip()
        if not token:
            continue
        if re.fullmatch(r"\d+", token):
            pages.add(int(token))
            continue
        match = re.fullmatch(r"(\d+)-(\d+)", token)
        if not match:
            raise argparse.ArgumentTypeError(f"invalid page token: {token}")
        start, end = map(int, match.groups())
        if start > end:
            raise argparse.ArgumentTypeError(f"page range is reversed: {token}")
        pages.update(range(start, end + 1))
    if not pages or min(pages) < 1:
        raise argparse.ArgumentTypeError("pages must contain positive PDF page numbers")
    return sorted(pages)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--pages", required=True, type=parse_pages, help="e.g. 1,3-5,9")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--dpi", type=int, default=180)
    parser.add_argument("--pdftoppm", help="explicit pdftoppm executable")
    args = parser.parse_args()

    pdf = args.pdf.expanduser().resolve()
    if not pdf.is_file():
        parser.error(f"PDF does not exist: {pdf}")
    if args.dpi < 72 or args.dpi > 600:
        parser.error("--dpi must be between 72 and 600")

    executable = args.pdftoppm or shutil.which("pdftoppm")
    if not executable:
        print("ERROR: pdftoppm was not found; install Poppler or pass --pdftoppm", file=sys.stderr)
        return 2

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    for page in args.pages:
        prefix = output_dir / f"page-{page:03d}"
        command = [
            executable,
            "-f",
            str(page),
            "-l",
            str(page),
            "-r",
            str(args.dpi),
            "-png",
            "-singlefile",
            str(pdf),
            str(prefix),
        ]
        completed = subprocess.run(command, text=True, capture_output=True)
        if completed.returncode:
            print(f"ERROR: failed to render PDF page {page}", file=sys.stderr)
            if completed.stderr:
                print(completed.stderr.strip(), file=sys.stderr)
            return completed.returncode
        output = prefix.with_suffix(".png")
        if not output.is_file():
            print(f"ERROR: pdftoppm did not create {output}", file=sys.stderr)
            return 1
        created.append(output)

    for output in created:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

