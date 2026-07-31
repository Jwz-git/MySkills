#!/usr/bin/env python3
"""Rank local knowledge-base files and print query-relevant snippets.

The script is deliberately read-only and dependency-free. It searches common
text knowledge formats and reports binary document candidates by filename so
that the caller can inspect them with a format-aware tool.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
from dataclasses import dataclass
from pathlib import Path
import re
import sys
import unicodedata


TEXT_EXTENSIONS = {
    ".md",
    ".mdx",
    ".txt",
    ".rst",
    ".adoc",
    ".org",
    ".tex",
    ".html",
    ".htm",
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".toml",
    ".csv",
    ".tsv",
}
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx", ".xls", ".epub"}
SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "__pycache__",
    "node_modules",
    "vendor",
    ".venv",
    "venv",
    "dist",
    "build",
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
}
WORD_RE = re.compile(r"[a-z0-9][a-z0-9_+#.-]*", re.IGNORECASE)
CJK_RUN_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]+")
MARKDOWN_HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$")


@dataclass
class Snippet:
    score: float
    start: int
    end: int
    heading: str
    text: str


@dataclass
class Result:
    path: Path
    score: float
    snippets: list[Snippet]
    opaque: bool = False


def normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text).casefold()


def tokens(text: str) -> set[str]:
    value = normalize(text)
    found = set(WORD_RE.findall(value))
    for run in CJK_RUN_RE.findall(value):
        if len(run) == 1:
            found.add(run)
        else:
            found.update(run[index : index + 2] for index in range(len(run) - 1))
            if len(run) <= 8:
                found.add(run)
    return found


def query_terms(query: str) -> set[str]:
    terms = tokens(query)
    return {term for term in terms if len(term) > 1 or CJK_RUN_RE.fullmatch(term)}


def path_is_excluded(relative: Path, patterns: list[str]) -> bool:
    path_text = relative.as_posix()
    return any(
        fnmatch.fnmatch(path_text, pattern)
        or fnmatch.fnmatch(relative.name, pattern)
        for pattern in patterns
    )


def iter_candidates(
    root: Path, include_hidden: bool, exclude_patterns: list[str]
):
    for current, directories, filenames in os.walk(root):
        current_path = Path(current)
        kept_directories = []
        for directory in directories:
            relative = (current_path / directory).relative_to(root)
            if directory in SKIP_DIRS:
                continue
            if not include_hidden and directory.startswith("."):
                continue
            if path_is_excluded(relative, exclude_patterns):
                continue
            kept_directories.append(directory)
        directories[:] = kept_directories

        for filename in filenames:
            path = current_path / filename
            relative = path.relative_to(root)
            if not include_hidden and filename.startswith("."):
                continue
            if path.is_symlink() or path_is_excluded(relative, exclude_patterns):
                continue
            suffix = path.suffix.casefold()
            if suffix in TEXT_EXTENSIONS:
                yield path, False
            elif suffix in DOCUMENT_EXTENSIONS:
                yield path, True


def overlap_score(haystack: str, terms: set[str]) -> float:
    if not terms:
        return 0.0
    present = tokens(haystack)
    matched = terms & present
    if not matched:
        return 0.0
    return 8.0 * len(matched) / len(terms) + 0.4 * len(matched)


def select_snippets(
    lines: list[str],
    terms: set[str],
    normalized_query: str,
    context: int,
    snippets_per_file: int,
) -> tuple[list[Snippet], int]:
    heading = ""
    scored_lines: list[tuple[float, int, str]] = []
    hit_count = 0

    for index, line in enumerate(lines):
        heading_match = MARKDOWN_HEADING_RE.match(line)
        if heading_match:
            heading = heading_match.group(2).strip()

        score = overlap_score(f"{heading} {line}", terms)
        normalized_line = normalize(line)
        if normalized_query and normalized_query in normalized_line:
            score += 12.0
        if score > 0:
            hit_count += 1
            if heading_match:
                score += 1.5
            scored_lines.append((score, index, heading))

    snippets: list[Snippet] = []
    for score, index, active_heading in sorted(scored_lines, reverse=True):
        start = max(0, index - context)
        end = min(len(lines), index + context + 1)
        if any(not (end <= item.start or start >= item.end) for item in snippets):
            continue
        snippet_text = "\n".join(lines[start:end]).strip()
        snippets.append(
            Snippet(
                score=score,
                start=start,
                end=end,
                heading=active_heading,
                text=snippet_text,
            )
        )
        if len(snippets) >= snippets_per_file:
            break

    snippets.sort(key=lambda item: item.start)
    return snippets, hit_count


def rank_file(
    path: Path,
    root: Path,
    terms: set[str],
    normalized_query: str,
    max_bytes: int,
    context: int,
    snippets_per_file: int,
    opaque: bool,
) -> Result | None:
    relative = path.relative_to(root)
    path_score = 2.0 * overlap_score(relative.as_posix(), terms)
    if normalized_query and normalized_query in normalize(relative.as_posix()):
        path_score += 18.0

    if opaque:
        if path_score <= 0:
            return None
        return Result(path=relative, score=path_score, snippets=[], opaque=True)

    try:
        if path.stat().st_size > max_bytes:
            return None
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except (OSError, UnicodeError):
        return None

    lines = text.splitlines()
    snippets, hit_count = select_snippets(
        lines, terms, normalized_query, context, snippets_per_file
    )
    if not snippets and path_score <= 0:
        return None

    best_snippet = max((item.score for item in snippets), default=0.0)
    total_score = path_score + best_snippet + min(hit_count, 10) * 0.25
    return Result(path=relative, score=total_score, snippets=snippets)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search a local knowledge base and rank relevant files."
    )
    parser.add_argument("query", help="Natural-language question or search phrase")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Knowledge root")
    parser.add_argument("--limit", type=int, default=10, help="Maximum file results")
    parser.add_argument(
        "--min-score",
        type=float,
        default=2.5,
        help="Discard weak matches below this relevance score",
    )
    parser.add_argument(
        "--context", type=int, default=2, help="Context lines around each hit"
    )
    parser.add_argument(
        "--snippets-per-file",
        type=int,
        default=2,
        help="Maximum snippets shown for each text file",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=2_000_000,
        help="Skip individual text files larger than this size",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Glob to exclude; may be supplied multiple times",
    )
    parser.add_argument(
        "--include-hidden", action="store_true", help="Include hidden files/directories"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.expanduser().resolve()
    if not root.is_dir():
        print(f"error: knowledge root is not a directory: {root}", file=sys.stderr)
        return 2
    if (
        args.limit < 1
        or args.context < 0
        or args.snippets_per_file < 1
        or args.min_score < 0
    ):
        print(
            "error: limit/snippets must be positive; context/min-score non-negative",
            file=sys.stderr,
        )
        return 2

    terms = query_terms(args.query)
    if not terms:
        print("error: query contains no searchable terms", file=sys.stderr)
        return 2

    normalized_query = normalize(args.query).strip()
    results: list[Result] = []
    for path, opaque in iter_candidates(root, args.include_hidden, args.exclude):
        result = rank_file(
            path=path,
            root=root,
            terms=terms,
            normalized_query=normalized_query,
            max_bytes=args.max_bytes,
            context=args.context,
            snippets_per_file=args.snippets_per_file,
            opaque=opaque,
        )
        if result:
            results.append(result)

    results = [result for result in results if result.score >= args.min_score]
    results.sort(key=lambda item: (-item.score, item.path.as_posix()))
    print(f"root: {root}")
    print(f"query: {args.query}")
    print(f"search_terms: {', '.join(sorted(terms))}")
    if not results:
        print("results: none")
        return 1

    print(f"results: {min(len(results), args.limit)}")
    for rank, result in enumerate(results[: args.limit], start=1):
        kind = "document-candidate" if result.opaque else "text"
        print(f"\n{rank}. {result.path.as_posix()} [{kind}, score={result.score:.2f}]")
        if result.opaque:
            print("   Filename matched; inspect with a format-aware tool.")
            continue
        for snippet in result.snippets:
            line_range = (
                str(snippet.start + 1)
                if snippet.end == snippet.start + 1
                else f"{snippet.start + 1}-{snippet.end}"
            )
            heading = f" | {snippet.heading}" if snippet.heading else ""
            print(f"   L{line_range}{heading}")
            for line in snippet.text.splitlines():
                print(f"     {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
