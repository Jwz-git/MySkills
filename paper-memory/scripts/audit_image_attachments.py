#!/usr/bin/env python3
"""Read-only audit for image attachments referenced by Markdown notes."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


IMAGE_EXTENSIONS = {
    ".avif",
    ".bmp",
    ".gif",
    ".jpeg",
    ".jpg",
    ".png",
    ".svg",
    ".webp",
}
IGNORED_PARTS = {".git", ".obsidian", ".agents", ".claude"}
MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
WIKI_IMAGE_RE = re.compile(
    r"!\[\[([^\]|]+\.(?:avif|bmp|gif|jpe?g|png|svg|webp))(?:\|[^\]]+)?\]\]",
    re.IGNORECASE,
)


def is_ignored(path: Path) -> bool:
    return any(part in IGNORED_PARTS for part in path.parts)


def clean_markdown_target(raw_target: str) -> str:
    target = raw_target.strip().strip("<>")
    if target.startswith(("http://", "https://", "data:")):
        return ""
    # Obsidian may append a size after a pipe. Standard Markdown titles are
    # intentionally not interpreted here because this audit targets vault links.
    return target.split("|", 1)[0].strip()


def resolve_target(
    vault: Path,
    note: Path,
    target: str,
    images_by_name: dict[str, list[Path]],
) -> tuple[Path | None, list[Path]]:
    relative = (note.parent / target).resolve()
    if relative.is_file():
        return relative, []

    vault_relative = (vault / target).resolve()
    if vault_relative.is_file():
        return vault_relative, []

    candidates = images_by_name.get(Path(target).name, [])
    if len(candidates) == 1:
        return candidates[0], []
    if len(candidates) > 1:
        return None, candidates
    return None, []


def audit(vault: Path, scopes: list[str]) -> dict[str, object]:
    scope_roots = [(vault / scope).resolve() for scope in scopes] if scopes else [vault]
    notes = sorted(
        path.resolve()
        for scope in scope_roots
        for path in scope.rglob("*.md")
        if path.is_file() and not is_ignored(path.relative_to(vault))
    )
    notes = list(dict.fromkeys(notes))

    image_files = sorted(
        path.resolve()
        for path in vault.rglob("*")
        if path.is_file()
        and path.suffix.lower() in IMAGE_EXTENSIONS
        and not is_ignored(path.relative_to(vault))
    )
    images_by_name: dict[str, list[Path]] = defaultdict(list)
    for image in image_files:
        images_by_name[image.name].append(image)

    references: dict[Path, set[Path]] = defaultdict(set)
    broken: list[dict[str, str]] = []
    ambiguous: list[dict[str, object]] = []
    legacy: list[dict[str, str]] = []
    reference_count = 0

    for note in notes:
        text = note.read_text(encoding="utf-8")
        occurrences: list[tuple[str, str]] = []

        for match in MARKDOWN_IMAGE_RE.finditer(text):
            target = clean_markdown_target(match.group(2))
            if target:
                occurrences.append(("markdown", target))

        for match in WIKI_IMAGE_RE.finditer(text):
            target = match.group(1).strip()
            occurrences.append(("wiki", target))
            legacy.append(
                {
                    "note": str(note.relative_to(vault)),
                    "target": target,
                }
            )

        for syntax, target in occurrences:
            reference_count += 1
            resolved, candidates = resolve_target(vault, note, target, images_by_name)
            if resolved is not None:
                references[resolved].add(note)
            elif candidates:
                ambiguous.append(
                    {
                        "note": str(note.relative_to(vault)),
                        "target": target,
                        "syntax": syntax,
                        "candidates": [
                            str(path.relative_to(vault)) for path in candidates
                        ],
                    }
                )
            else:
                broken.append(
                    {
                        "note": str(note.relative_to(vault)),
                        "target": target,
                        "syntax": syntax,
                    }
                )

    shared = []
    misplaced = []
    for image, referencing_notes in references.items():
        if len(referencing_notes) > 1:
            shared.append(
                {
                    "image": str(image.relative_to(vault)),
                    "notes": sorted(
                        str(note.relative_to(vault)) for note in referencing_notes
                    ),
                }
            )
            continue

        note = next(iter(referencing_notes))
        expected_parent = (note.parent / "assets" / note.stem).resolve()
        if image.parent != expected_parent:
            misplaced.append(
                {
                    "image": str(image.relative_to(vault)),
                    "note": str(note.relative_to(vault)),
                    "expected_parent": str(expected_parent.relative_to(vault)),
                }
            )

    referenced_images = set(references)
    unreferenced = sorted(set(image_files) - referenced_images)

    return {
        "vault": str(vault),
        "scopes": scopes,
        "notes_scanned": len(notes),
        "notes_with_images": len(
            {note for referencing_notes in references.values() for note in referencing_notes}
        ),
        "image_files": len(image_files),
        "image_references": reference_count,
        "unique_referenced_images": len(referenced_images),
        "broken_references": broken,
        "ambiguous_references": ambiguous,
        "legacy_wiki_embeds": legacy,
        "shared_images": shared,
        "misplaced_images": misplaced,
        "unreferenced_images": [
            str(path.relative_to(vault)) for path in unreferenced
        ],
    }


def print_text(report: dict[str, object]) -> None:
    scalar_keys = (
        "vault",
        "notes_scanned",
        "notes_with_images",
        "image_files",
        "image_references",
        "unique_referenced_images",
    )
    for key in scalar_keys:
        print(f"{key}: {report[key]}")

    list_keys = (
        "broken_references",
        "ambiguous_references",
        "legacy_wiki_embeds",
        "shared_images",
        "misplaced_images",
        "unreferenced_images",
    )
    for key in list_keys:
        items = report[key]
        print(f"{key}: {len(items)}")
        for item in items:
            print(f"  - {json.dumps(item, ensure_ascii=False, sort_keys=True)}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit paper-note image links and note-local attachment placement."
    )
    parser.add_argument("vault", type=Path, help="Obsidian vault root")
    parser.add_argument(
        "--scope",
        action="append",
        default=[],
        help="Vault-relative directory to scan for notes; repeatable",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON")
    args = parser.parse_args()

    vault = args.vault.expanduser().resolve()
    if not vault.is_dir():
        parser.error(f"vault is not a directory: {vault}")
    for scope in args.scope:
        scope_path = (vault / scope).resolve()
        if not scope_path.is_dir() or vault not in (scope_path, *scope_path.parents):
            parser.error(f"invalid scope: {scope}")

    report = audit(vault, args.scope)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print_text(report)

    return int(
        bool(
            report["broken_references"]
            or report["ambiguous_references"]
            or report["legacy_wiki_embeds"]
            or report["misplaced_images"]
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
