#!/usr/bin/env python3
"""Read-only audit of local Markdown tags using a paper-memory profile."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from profile_config import ProfileError, find_profile, load_profile, validate_profile


def frontmatter_lines(path: Path) -> list[str] | None:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines[1:index]
    return None


def clean_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_inline_list(value: str) -> list[str]:
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        raise ValueError("tags must be a YAML list")
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [clean_scalar(item) for item in next(csv.reader([inner], skipinitialspace=True))]


def extract_tags(lines: list[str]) -> tuple[list[str] | None, str | None]:
    for index, line in enumerate(lines):
        if not line.startswith("tags:"):
            continue
        value = line.split(":", 1)[1].strip()
        if value:
            try:
                return parse_inline_list(value), None
            except ValueError as error:
                return None, str(error)
        tags: list[str] = []
        for following in lines[index + 1 :]:
            if following.startswith("  - "):
                tags.append(clean_scalar(following[4:]))
            elif following.strip():
                break
        return tags, None
    return None, None


def audit(root: Path, profile: dict[str, object], strict_cross_namespace: bool) -> tuple[dict[str, object], bool]:
    files = sorted(root.rglob("*.md")) if root.is_dir() else [root]
    tag_policy = profile["tags"]
    assert isinstance(tag_policy, dict)
    strategy = str(tag_policy.get("strategy", "preserve"))
    allowed = {str(item) for item in tag_policy.get("allowed_namespaces", [])}
    reject_aliases = bool(tag_policy.get("reject_aliases", False))
    errors: list[str] = []
    warnings: list[str] = []
    all_tags: list[str] = []
    files_with_tags = 0
    alias_fields = 0
    leaf_uses: dict[str, list[dict[str, str]]] = defaultdict(list)

    for path in files:
        frontmatter = frontmatter_lines(path)
        display_path = str(path)
        if frontmatter is None:
            warnings.append(f"{display_path}: no complete frontmatter")
            continue
        if any(line.startswith("aliases:") for line in frontmatter):
            alias_fields += 1
            if reject_aliases:
                errors.append(f"{display_path}: aliases forbidden by profile")
        tags, parse_error = extract_tags(frontmatter)
        if parse_error:
            errors.append(f"{display_path}: {parse_error}")
            continue
        if tags is None:
            warnings.append(f"{display_path}: no tags field")
            continue
        files_with_tags += 1
        duplicates = sorted({tag for tag in tags if tags.count(tag) > 1})
        if duplicates:
            errors.append(f"{display_path}: duplicate tags: {', '.join(duplicates)}")
        for tag in tags:
            all_tags.append(tag)
            if "/" not in tag:
                if strategy in {"recommended", "custom"} and allowed:
                    errors.append(f"{display_path}: tag lacks namespace: {tag}")
                continue
            namespace, leaf = tag.split("/", 1)
            if strategy in {"recommended", "custom"} and allowed and namespace not in allowed:
                errors.append(f"{display_path}: namespace not allowed by profile: {tag}")
            if not leaf:
                errors.append(f"{display_path}: empty tag leaf: {tag}")
            leaf_uses[leaf].append({"namespace": namespace, "file": display_path, "tag": tag})

    cross_namespace = {
        leaf: uses for leaf, uses in sorted(leaf_uses.items())
        if len({item["namespace"] for item in uses}) > 1
    }
    if cross_namespace:
        message = "same leaf in multiple namespaces: " + ", ".join(cross_namespace)
        if strict_cross_namespace and strategy in {"recommended", "custom"}:
            errors.append(message)
        else:
            warnings.append(message)
    result: dict[str, object] = {
        "root": str(root), "tag_strategy": strategy, "markdown_files": len(files),
        "files_with_tags": files_with_tags, "alias_fields": alias_fields,
        "tag_occurrences": len(all_tags), "unique_tags": len(set(all_tags)),
        "cross_namespace_leafs": cross_namespace, "errors": errors, "warnings": warnings,
    }
    return result, not errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Markdown file or directory")
    parser.add_argument("--profile", type=Path, help="Profile path; defaults to nearest profile")
    parser.add_argument("--strict-cross-namespace", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = args.path.expanduser().resolve()
    if not root.exists():
        parser.error(f"path does not exist: {root}")
    profile_path = args.profile.expanduser().resolve() if args.profile else find_profile(root)
    if profile_path is None:
        parser.error("no .paper-memory.yaml found; pass --profile")
    try:
        profile = load_profile(profile_path)
    except ProfileError as error:
        parser.error(str(error))
    errors = validate_profile(profile)
    if errors:
        parser.error("invalid profile: " + "; ".join(errors))
    result, passed = audit(root, profile, args.strict_cross_namespace)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for key in ("tag_strategy", "markdown_files", "files_with_tags", "alias_fields", "tag_occurrences", "unique_tags"):
            print(f"{key}={result[key]}")
        for warning in result["warnings"]:
            print(f"WARNING: {warning}")
        for error in result["errors"]:
            print(f"ERROR: {error}")
        print(f"checks={'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
