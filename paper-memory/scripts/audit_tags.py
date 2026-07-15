#!/usr/bin/env python3
"""Audit paper-note frontmatter tags and reject aliases without modifying files."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


ALLOWED_NAMESPACES = {"论文", "方法", "任务", "模态"}
ENGLISH_NAMESPACES = {"paper", "method", "task", "modality"}


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
        raise ValueError("tags 必须是 YAML 列表")
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
                continue
            if following.strip() == "":
                continue
            break
        return tags, None
    return None, None


def audit(root: Path, strict_cross_namespace: bool) -> tuple[dict[str, object], bool]:
    files = sorted(root.rglob("*.md")) if root.is_dir() else [root]
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
            warnings.append(f"{display_path}: 缺少完整 Frontmatter")
            continue

        if any(line.startswith("aliases:") for line in frontmatter):
            alias_fields += 1
            errors.append(f"{display_path}: 禁止使用 aliases 字段")

        tags, parse_error = extract_tags(frontmatter)
        if parse_error:
            errors.append(f"{display_path}: {parse_error}")
            continue
        if tags is None:
            warnings.append(f"{display_path}: 缺少 tags 字段")
            continue

        files_with_tags += 1
        duplicates = sorted({tag for tag in tags if tags.count(tag) > 1})
        if duplicates:
            errors.append(f"{display_path}: 文件内重复标签: {', '.join(duplicates)}")

        for tag in tags:
            all_tags.append(tag)
            if "/" not in tag:
                errors.append(f"{display_path}: 标签缺少命名空间: {tag}")
                continue
            namespace, leaf = tag.split("/", 1)
            if namespace in ENGLISH_NAMESPACES:
                errors.append(f"{display_path}: 残留英文命名空间: {tag}")
            elif namespace not in ALLOWED_NAMESPACES:
                errors.append(f"{display_path}: 未知命名空间: {tag}")
            if not leaf:
                errors.append(f"{display_path}: 标签叶值为空: {tag}")
            leaf_uses[leaf].append({"namespace": namespace, "file": display_path, "tag": tag})

    cross_namespace = {
        leaf: uses
        for leaf, uses in sorted(leaf_uses.items())
        if len({item["namespace"] for item in uses}) > 1
    }
    if cross_namespace:
        message = "跨命名空间同叶标签: " + ", ".join(cross_namespace)
        (errors if strict_cross_namespace else warnings).append(message)

    result: dict[str, object] = {
        "root": str(root),
        "markdown_files": len(files),
        "files_with_tags": files_with_tags,
        "alias_fields": alias_fields,
        "tag_occurrences": len(all_tags),
        "unique_tags": len(set(all_tags)),
        "cross_namespace_leafs": cross_namespace,
        "errors": errors,
        "warnings": warnings,
    }
    return result, not errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="论文 Markdown 文件或目录")
    parser.add_argument(
        "--strict-cross-namespace",
        action="store_true",
        help="将跨命名空间同叶标签视为错误",
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    if not args.path.exists():
        parser.error(f"路径不存在: {args.path}")

    result, passed = audit(args.path, args.strict_cross_namespace)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for key in ("markdown_files", "files_with_tags", "alias_fields", "tag_occurrences", "unique_tags"):
            print(f"{key}={result[key]}")
        print(f"cross_namespace_leafs={len(result['cross_namespace_leafs'])}")
        for warning in result["warnings"]:
            print(f"WARNING: {warning}")
        for error in result["errors"]:
            print(f"ERROR: {error}")
        print(f"checks={'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
