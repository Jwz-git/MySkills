#!/usr/bin/env python3
"""Validate paper-research Markdown notes using only the Python standard library."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote


REQUIRED_KEYS = ["title", "date", "tags", "aliases"]
EXPECTED_H1 = [
    "一句话总结",
    "论文基本信息",
    "核心内容详解",
    "关键原图与图解",
    "总结",
]
EXPECTED_CORE_H2 = [
    "1. 研究背景与问题",
    "2. 方法或论证框架",
    "3. 证据与结果",
    "4. 合理性与可行性评估",
    "5. 局限、改进与展望",
]
TAG_RE = re.compile(r"^paper/[a-z0-9][a-z0-9-]*$")
KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(?:\s*(.*))?$")
H1_RE = re.compile(r"^# ([^#].*)$")
H2_RE = re.compile(r"^## ([^#].*)$")
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\((<[^>]+>|[^)]+)\)")
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\((<[^>]+>|[^)]+)\)")
SCOPE_RE = re.compile(
    r"\|\s*\*\*分析依据\*\*\s*\|\s*(full-text|partial|abstract-only)\s*\|"
)
CANONICAL_RE = re.compile(r"\|\s*\*\*Canonical ID\*\*\s*\|\s*([^|]+?)\s*\|")
LOCATOR_RE = re.compile(
    r"(?:原文\s*(?:pp?\.|§|Table|Figure|Fig\.|Eq\.|Appendix|表|图|公式|附录)|"
    r"[（(]Abstract[）)])",
    re.IGNORECASE,
)
STRONG_RE = re.compile(
    r"(?:SOTA|state[- ]of[- ]the[- ]art|首次|最高|最佳|显著|证明|导致|泛化|"
    r"鲁棒|可扩展|零额外|提升|降低|超过|优于)",
    re.IGNORECASE,
)
HIGHLIGHT_NUMBER_RE = re.compile(r"==[^=\n]*\d[^=\n]*==")
FORBIDDEN_RE = [
    ("content.pending", re.compile(r"\[待补充\]"), "存在含义模糊的 [待补充]"),
    ("content.inference_tag", re.compile(r"\[推断(?:[:：]|\])"), "存在 [推断] 免责标签"),
    ("content.todo", re.compile(r"\b(?:TODO|TBD)\b", re.IGNORECASE), "存在 TODO/TBD"),
    ("content.template", re.compile(r"\[(?:论文完整标题|官方页面|note-stem|文件名)\]"), "存在模板占位符"),
]


@dataclass
class Issue:
    level: str
    code: str
    message: str
    line: int | None = None


@dataclass
class FileResult:
    path: str
    issues: list[Issue]
    canonical_id: str | None = None

    @property
    def errors(self) -> int:
        return sum(i.level == "ERROR" for i in self.issues)

    @property
    def warnings(self) -> int:
        return sum(i.level == "WARN" for i in self.issues)


def add(
    issues: list[Issue],
    level: str,
    code: str,
    message: str,
    line: int | None = None,
) -> None:
    issues.append(Issue(level=level, code=code, message=message, line=line))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="Markdown file or directory")
    parser.add_argument("--strict", action="store_true", help="Promote quality warnings to errors")
    parser.add_argument("--json", type=Path, dest="json_path", help="Write machine-readable report")
    return parser.parse_args()


def discover(paths: Iterable[Path]) -> list[Path]:
    found: set[Path] = set()
    for raw in paths:
        path = raw.expanduser().resolve()
        if path.is_file() and path.suffix.lower() == ".md":
            found.add(path)
        elif path.is_dir():
            found.update(p.resolve() for p in path.rglob("*.md") if p.is_file())
        else:
            raise FileNotFoundError(f"Markdown path does not exist: {raw}")
    return sorted(found)


def parse_frontmatter(lines: list[str], issues: list[Issue]) -> tuple[int, dict[str, object]]:
    if not lines or lines[0].strip() != "---":
        add(issues, "ERROR", "frontmatter.missing", "文件必须以 YAML frontmatter 开始", 1)
        return -1, {}

    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        add(issues, "ERROR", "frontmatter.unclosed", "frontmatter 缺少结束分隔线", 1)
        return -1, {}

    data: dict[str, object] = {}
    current: str | None = None
    for index in range(1, end):
        line = lines[index]
        match = KEY_RE.match(line)
        if match and not line.startswith((" ", "\t")):
            key, value = match.group(1), (match.group(2) or "").strip()
            if key in data:
                add(issues, "ERROR", "frontmatter.duplicate", f"字段 {key} 重复", index + 1)
            data[key] = value if value else []
            current = key
            continue

        item = re.match(r"^\s+-\s+(.+?)\s*$", line)
        if item and current:
            if not isinstance(data.get(current), list):
                add(issues, "ERROR", "frontmatter.invalid_list", f"字段 {current} 不能同时是标量和列表", index + 1)
            else:
                data[current].append(item.group(1).strip().strip('"\''))
        elif line.strip() and not line.lstrip().startswith("#"):
            add(issues, "ERROR", "frontmatter.syntax", "无法解析的 frontmatter 行", index + 1)

    keys = list(data)
    if keys != REQUIRED_KEYS:
        add(
            issues,
            "ERROR",
            "frontmatter.keys",
            f"字段及顺序应为 {REQUIRED_KEYS}，实际为 {keys}",
            2,
        )

    title = data.get("title")
    if not isinstance(title, str) or not title.strip().strip('"\''):
        add(issues, "ERROR", "frontmatter.title", "title 必须是非空标量")

    date_value = data.get("date")
    if not isinstance(date_value, str):
        add(issues, "ERROR", "frontmatter.date", "date 必须是 YYYY-MM-DD")
    else:
        try:
            dt.date.fromisoformat(date_value.strip('"\''))
        except ValueError:
            add(issues, "ERROR", "frontmatter.date", "date 必须是有效的 YYYY-MM-DD")

    tags = data.get("tags")
    if not isinstance(tags, list) or not tags:
        add(issues, "ERROR", "frontmatter.tags", "tags 必须是非空列表")
    else:
        if len(tags) != len(set(tags)):
            add(issues, "ERROR", "frontmatter.tags_duplicate", "tags 存在重复项")
        for tag in tags:
            if not TAG_RE.fullmatch(tag):
                add(issues, "ERROR", "frontmatter.tag_format", f"非法标签: {tag}")
        if not 2 <= len(tags) <= 5:
            add(issues, "WARN", "frontmatter.tag_count", "建议使用 2–5 个主题标签")

    aliases = data.get("aliases")
    if not isinstance(aliases, list) or not aliases:
        add(issues, "ERROR", "frontmatter.aliases", "aliases 必须是非空列表")
    elif len(aliases) != len(set(aliases)):
        add(issues, "ERROR", "frontmatter.aliases_duplicate", "aliases 存在重复项")

    return end, data


def first_nonempty(lines: list[str], start: int) -> tuple[int, str] | None:
    for index in range(start, len(lines)):
        if lines[index].strip():
            return index, lines[index].strip()
    return None


def strip_destination(raw: str) -> str:
    value = raw.strip()
    if value.startswith("<") and value.endswith(">"):
        value = value[1:-1]
    value = value.split("#", 1)[0]
    return unquote(value)


def is_remote(destination: str) -> bool:
    return bool(re.match(r"^(?:https?://|mailto:|data:)", destination, re.IGNORECASE))


def resolve_local(note: Path, raw: str) -> Path | None:
    destination = strip_destination(raw)
    if not destination or is_remote(destination):
        return None
    return (note.parent / destination).resolve()


def paragraphs(lines: list[str], start: int = 0) -> Iterable[tuple[int, str]]:
    buffer: list[str] = []
    first = start
    for index in range(start, len(lines) + 1):
        line = lines[index] if index < len(lines) else ""
        if line.strip():
            if not buffer:
                first = index
            buffer.append(line)
        elif buffer:
            yield first, "\n".join(buffer)
            buffer = []


def validate_file(path: Path, strict: bool) -> FileResult:
    issues: list[Issue] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return FileResult(str(path), [Issue("ERROR", "encoding", "文件不是 UTF-8")])
    lines = text.splitlines()
    fm_end, _ = parse_frontmatter(lines, issues)

    if fm_end >= 0:
        first = first_nonempty(lines, fm_end + 1)
        if not first or not first[1].startswith("**原文**:"):
            add(issues, "ERROR", "source.position", "frontmatter 后首个非空块必须是 **原文**:", (first[0] + 1) if first else None)
        elif not LINK_RE.search(first[1]):
            add(issues, "ERROR", "source.link", "原文行至少需要一个 Markdown 链接", first[0] + 1)

    h1 = [(i + 1, m.group(1).strip()) for i, line in enumerate(lines) if (m := H1_RE.match(line))]
    actual_h1 = [title for _, title in h1]
    if actual_h1 != EXPECTED_H1:
        add(issues, "ERROR", "structure.h1", f"一级标题应为 {EXPECTED_H1}，实际为 {actual_h1}")

    try:
        core_start = next(i for i, line in enumerate(lines) if line == "# 核心内容详解")
        figure_start = next(i for i, line in enumerate(lines) if line == "# 关键原图与图解")
        core_h2 = [m.group(1).strip() for line in lines[core_start + 1 : figure_start] if (m := H2_RE.match(line))]
        if core_h2 != EXPECTED_CORE_H2:
            add(issues, "ERROR", "structure.core_h2", f"核心二级标题应为 {EXPECTED_CORE_H2}，实际为 {core_h2}")
    except StopIteration:
        core_start, figure_start = 0, len(lines)

    if "> [!info] 论文定位" not in text:
        add(issues, "ERROR", "callout.info", "缺少 > [!info] 论文定位")
    if "> [!abstract] 论文总结" not in text:
        add(issues, "ERROR", "callout.abstract", "缺少 > [!abstract] 论文总结")
    if "```mermaid" in text.lower():
        add(issues, "ERROR", "content.mermaid", "禁止使用 Mermaid 替代原论文图")

    for code, pattern, message in FORBIDDEN_RE:
        match = pattern.search(text)
        if match:
            add(issues, "ERROR", code, message, text[: match.start()].count("\n") + 1)

    scope_match = SCOPE_RE.search(text)
    scope = scope_match.group(1) if scope_match else None
    if not scope:
        add(issues, "ERROR", "evidence.scope", "基本信息表缺少合法的分析依据")

    canonical_match = CANONICAL_RE.search(text)
    canonical = canonical_match.group(1).strip() if canonical_match else None
    if not canonical:
        add(issues, "ERROR", "identity.canonical", "基本信息表缺少 Canonical ID")

    normalized = re.sub(r"\s+", "", text)
    evidence_header = "|结论|证据|原文定位|适用边界|"
    if evidence_header not in normalized:
        add(issues, "ERROR", "evidence.table", "缺少固定四列的核心证据表")
        evidence_rows = 0
    else:
        header_index = next(i for i, line in enumerate(lines) if re.sub(r"\s+", "", line) == evidence_header)
        evidence_rows = 0
        for line in lines[header_index + 2 :]:
            if not line.lstrip().startswith("|"):
                break
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) == 4 and all(cells):
                evidence_rows += 1
        if evidence_rows < 3:
            add(issues, "ERROR" if strict else "WARN", "evidence.row_count", "核心证据表建议至少有 3 条非空证据")

    locator_count = len(LOCATOR_RE.findall(text))
    minimum_locators = max(3, evidence_rows)
    if locator_count < minimum_locators:
        add(issues, "ERROR" if strict else "WARN", "evidence.locator_count", f"原文定位过少：{locator_count}，建议至少 {minimum_locators}")

    for start, paragraph in paragraphs(lines, fm_end + 1 if fm_end >= 0 else 0):
        if paragraph.startswith("#") or paragraph.startswith("**原文**:"):
            continue
        strong = STRONG_RE.search(paragraph) or HIGHLIGHT_NUMBER_RE.search(paragraph)
        if strong and not LOCATOR_RE.search(paragraph):
            add(
                issues,
                "ERROR" if strict else "WARN",
                "evidence.strong_claim_without_locator",
                "强比较词或高亮数字所在段落缺少原文定位",
                start + 1,
            )

    for match in LINK_RE.finditer(text):
        resolved = resolve_local(path, match.group(1))
        if resolved is not None and not resolved.exists():
            add(
                issues,
                "ERROR",
                "link.missing",
                f"本地链接不存在: {strip_destination(match.group(1))}",
                text[: match.start()].count("\n") + 1,
            )

    image_matches = list(IMAGE_RE.finditer(text))
    if scope == "full-text" and not image_matches:
        add(issues, "ERROR" if strict else "WARN", "figure.missing", "full-text 笔记没有原论文图片")

    for match in image_matches:
        alt, raw_destination = match.group(1).strip(), match.group(2)
        line_number = text[: match.start()].count("\n") + 1
        if not alt:
            add(issues, "ERROR", "figure.alt", "图片 alt 文本不能为空", line_number)
        resolved = resolve_local(path, raw_destination)
        if resolved is not None and not resolved.exists():
            add(issues, "ERROR", "figure.path", f"图片不存在: {strip_destination(raw_destination)}", line_number)
        following = "\n".join(lines[line_number : line_number + 7])
        if not (re.search(r"原文\s*(?:Figure|Fig\.|图)\s*\S+", following, re.IGNORECASE) and re.search(r"PDF\s*p\.", following, re.IGNORECASE)):
            add(
                issues,
                "ERROR" if strict else "WARN",
                "figure.caption",
                "图片后需注明原文图号和 PDF 页码",
                line_number,
            )

    return FileResult(path=str(path), issues=issues, canonical_id=canonical)


def apply_directory_checks(results: list[FileResult]) -> None:
    by_id: dict[str, list[FileResult]] = {}
    for result in results:
        if result.canonical_id and result.canonical_id not in {"未报告", "当前材料无法确认", "不适用"}:
            key = re.sub(r"\s+", "", result.canonical_id).lower()
            by_id.setdefault(key, []).append(result)
    for canonical_id, duplicates in by_id.items():
        if len(duplicates) > 1:
            paths = ", ".join(Path(item.path).name for item in duplicates)
            for item in duplicates:
                add(item.issues, "ERROR", "identity.duplicate", f"Canonical ID {canonical_id} 重复: {paths}")


def report_dict(results: list[FileResult], strict: bool) -> dict[str, object]:
    errors = sum(item.errors for item in results)
    warnings = sum(item.warnings for item in results)
    passed = sum(item.errors == 0 for item in results)
    return {
        "strict": strict,
        "summary": {
            "files": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "errors": errors,
            "warnings": warnings,
        },
        "files": [
            {
                "path": item.path,
                "canonical_id": item.canonical_id,
                "errors": item.errors,
                "warnings": item.warnings,
                "issues": [asdict(issue) for issue in item.issues],
            }
            for item in results
        ],
    }


def main() -> int:
    args = parse_args()
    try:
        files = discover(args.paths)
    except FileNotFoundError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    if not files:
        print("ERROR: no Markdown files found", file=sys.stderr)
        return 2

    results = [validate_file(path, args.strict) for path in files]
    apply_directory_checks(results)
    payload = report_dict(results, args.strict)

    for result in results:
        status = "PASS" if result.errors == 0 else "FAIL"
        print(f"{status}\t{result.path}")
        for issue in result.issues:
            location = f":{issue.line}" if issue.line else ""
            print(f"  {issue.level}\t{issue.code}{location}\t{issue.message}")

    summary = payload["summary"]
    print(
        "SUMMARY\t"
        f"files={summary['files']}\tpassed={summary['passed']}\tfailed={summary['failed']}\t"
        f"errors={summary['errors']}\twarnings={summary['warnings']}"
    )

    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

