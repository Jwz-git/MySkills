#!/usr/bin/env python3
"""Read-only audit for local image attachments using a paper-memory profile."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from profile_config import (
    ProfileError, expand_attachment_parent, find_profile, load_profile,
    local_memory_root, validate_profile,
)


IMAGE_EXTENSIONS = {".avif", ".bmp", ".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"}
IGNORED_PARTS = {".git", ".obsidian", ".agents", ".claude"}
MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
WIKI_IMAGE_RE = re.compile(r"!\[\[([^\]|]+\.(?:avif|bmp|gif|jpe?g|png|svg|webp))(?:\|[^\]]+)?\]\]", re.IGNORECASE)


def is_ignored(path: Path) -> bool:
    return any(part in IGNORED_PARTS for part in path.parts)


def clean_target(raw: str) -> str:
    target = raw.strip().strip("<>")
    if target.startswith(("http://", "https://", "data:")):
        return ""
    return target.split("|", 1)[0].strip()


def resolve_target(root: Path, note: Path, target: str, by_name: dict[str, list[Path]]) -> tuple[Path | None, list[Path]]:
    for candidate in ((note.parent / target).resolve(), (root / target).resolve()):
        if candidate.is_file() and root in (candidate, *candidate.parents):
            return candidate, []
    candidates = by_name.get(Path(target).name, [])
    return (candidates[0], []) if len(candidates) == 1 else (None, candidates)


def audit(root: Path, scopes: list[str], profile: dict[str, object]) -> dict[str, object]:
    scope_roots = [(root / scope).resolve() for scope in scopes] if scopes else [root]
    notes = sorted({
        path.resolve() for scope in scope_roots for path in scope.rglob("*.md")
        if path.is_file() and not is_ignored(path.relative_to(root))
    })
    image_files = sorted(
        path.resolve() for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        and not is_ignored(path.relative_to(root))
    )
    by_name: dict[str, list[Path]] = defaultdict(list)
    for image in image_files:
        by_name[image.name].append(image)

    references: dict[Path, set[Path]] = defaultdict(set)
    broken: list[dict[str, str]] = []
    ambiguous: list[dict[str, object]] = []
    wiki_embeds: list[dict[str, str]] = []
    reference_count = 0
    for note in notes:
        text = note.read_text(encoding="utf-8-sig")
        occurrences: list[tuple[str, str]] = []
        for match in MARKDOWN_IMAGE_RE.finditer(text):
            target = clean_target(match.group(2))
            if target:
                occurrences.append(("markdown", target))
        for match in WIKI_IMAGE_RE.finditer(text):
            target = match.group(1).strip()
            occurrences.append(("wiki", target))
            wiki_embeds.append({"note": str(note.relative_to(root)), "target": target})
        for syntax, target in occurrences:
            reference_count += 1
            resolved, candidates = resolve_target(root, note, target, by_name)
            if resolved:
                references[resolved].add(note)
            elif candidates:
                ambiguous.append({
                    "note": str(note.relative_to(root)), "target": target, "syntax": syntax,
                    "candidates": [str(path.relative_to(root)) for path in candidates],
                })
            else:
                broken.append({"note": str(note.relative_to(root)), "target": target, "syntax": syntax})

    attachments = profile["attachments"]
    assert isinstance(attachments, dict)
    pattern = str(attachments.get("root_pattern", ""))
    shared: list[dict[str, object]] = []
    misplaced: list[dict[str, str]] = []
    for image, referencing_notes in references.items():
        if len(referencing_notes) > 1:
            shared.append({
                "image": str(image.relative_to(root)),
                "notes": sorted(str(note.relative_to(root)) for note in referencing_notes),
            })
            continue
        if pattern:
            note = next(iter(referencing_notes))
            expected = expand_attachment_parent(pattern, note)
            if image.parent != expected:
                try:
                    display_expected = str(expected.relative_to(root))
                except ValueError:
                    display_expected = str(expected)
                misplaced.append({
                    "image": str(image.relative_to(root)), "note": str(note.relative_to(root)),
                    "expected_parent": display_expected,
                })
    referenced = set(references)
    return {
        "memory_root": str(root), "scopes": scopes, "notes_scanned": len(notes),
        "notes_with_images": len({note for value in references.values() for note in value}),
        "image_files": len(image_files), "image_references": reference_count,
        "unique_referenced_images": len(referenced), "broken_references": broken,
        "ambiguous_references": ambiguous, "wiki_embeds": wiki_embeds,
        "shared_images": shared, "misplaced_images": misplaced,
        "unreferenced_images": [str(path.relative_to(root)) for path in sorted(set(image_files) - referenced)],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Memory root or a path below it")
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--scope", action="append", default=[])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    start = args.path.expanduser().resolve()
    profile_path = args.profile.expanduser().resolve() if args.profile else find_profile(start)
    if profile_path is None:
        parser.error("no .paper-memory.yaml found; pass --profile")
    try:
        profile = load_profile(profile_path)
    except ProfileError as error:
        parser.error(str(error))
    profile_errors = validate_profile(profile)
    if profile_errors:
        parser.error("invalid profile: " + "; ".join(profile_errors))
    root = local_memory_root(profile, profile_path)
    if root is None:
        parser.error("local audit requires memory.provider markdown or obsidian")
    attachments = profile["attachments"]
    assert isinstance(attachments, dict)
    if attachments.get("mode") != "local":
        parser.error("local audit requires attachments.mode=local")
    if not root.is_dir():
        parser.error(f"memory root is not a directory: {root}")
    for scope in args.scope:
        scope_path = (root / scope).resolve()
        if not scope_path.is_dir() or root not in (scope_path, *scope_path.parents):
            parser.error(f"invalid scope: {scope}")
    report = audit(root, args.scope, profile)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for key, value in report.items():
            if isinstance(value, list):
                print(f"{key}: {len(value)}")
                for item in value:
                    print(f"  - {json.dumps(item, ensure_ascii=False, sort_keys=True)}")
            else:
                print(f"{key}: {value}")
    fails = bool(report["broken_references"] or report["ambiguous_references"] or report["misplaced_images"])
    if attachments.get("link_style") == "markdown" and report["wiki_embeds"]:
        fails = True
    return int(fails)


if __name__ == "__main__":
    raise SystemExit(main())
