#!/usr/bin/env python3
"""将已经隔离出的文章正文 HTML 片段转换为基础 Markdown。"""

from __future__ import annotations

import argparse
import html
import re
import sys
from html.parser import HTMLParser
from pathlib import Path


BLOCKS = {"article", "div", "main", "p", "section"}
SKIP = {"script", "style", "noscript", "svg"}


class MarkdownParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0
        self.pre_depth = 0
        self.list_stack: list[str] = []
        self.link_stack: list[str | None] = []

    def emit(self, value: str) -> None:
        if not self.skip_depth:
            self.parts.append(value)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        values = dict(attrs)
        if tag in SKIP:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag in BLOCKS:
            self.emit("\n\n")
        elif re.fullmatch(r"h[1-6]", tag):
            self.emit(f"\n\n{'#' * int(tag[1])} ")
        elif tag == "br":
            self.emit("\n")
        elif tag in {"strong", "b"}:
            self.emit("**")
        elif tag in {"em", "i"}:
            self.emit("*")
        elif tag == "blockquote":
            self.emit("\n\n> ")
        elif tag in {"ul", "ol"}:
            self.list_stack.append(tag)
            self.emit("\n")
        elif tag == "li":
            marker = "1. " if self.list_stack and self.list_stack[-1] == "ol" else "- "
            self.emit(f"\n{marker}")
        elif tag == "a":
            self.emit("[")
            self.link_stack.append(values.get("href"))
        elif tag == "img":
            src = values.get("src") or ""
            alt = values.get("alt") or ""
            if src:
                self.emit(f"![{alt}]({src})")
        elif tag == "pre":
            self.pre_depth += 1
            self.emit("\n\n```\n")
        elif tag == "code" and not self.pre_depth:
            self.emit("`")
        elif tag == "hr":
            self.emit("\n\n---\n\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in SKIP:
            if self.skip_depth:
                self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        if tag in BLOCKS or re.fullmatch(r"h[1-6]", tag):
            self.emit("\n\n")
        elif tag in {"strong", "b"}:
            self.emit("**")
        elif tag in {"em", "i"}:
            self.emit("*")
        elif tag == "blockquote":
            self.emit("\n\n")
        elif tag in {"ul", "ol"}:
            if self.list_stack:
                self.list_stack.pop()
            self.emit("\n")
        elif tag == "a":
            href = self.link_stack.pop() if self.link_stack else None
            self.emit(f"]({href})" if href else "]")
        elif tag == "pre":
            self.emit("\n```\n\n")
            self.pre_depth = max(0, self.pre_depth - 1)
        elif tag == "code" and not self.pre_depth:
            self.emit("`")

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        self.emit(data if self.pre_depth else re.sub(r"\s+", " ", data))

    def markdown(self) -> str:
        value = html.unescape("".join(self.parts))
        value = re.sub(r"[ \t]+\n", "\n", value)
        value = re.sub(r"\n[ \t]+", "\n", value)
        value = re.sub(r"\n{3,}", "\n\n", value)
        return value.strip() + "\n"


def convert(fragment: str) -> str:
    parser = MarkdownParser()
    parser.feed(fragment)
    parser.close()
    return parser.markdown()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, help="HTML 片段文件；省略时从标准输入读取")
    args = parser.parse_args()
    source = args.input.read_text(encoding="utf-8") if args.input else sys.stdin.read()
    sys.stdout.write(convert(source))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
