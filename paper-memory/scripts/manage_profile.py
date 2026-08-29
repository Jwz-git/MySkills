#!/usr/bin/env python3
"""Create, locate, show, or validate a paper-memory profile."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from profile_config import PROFILE_NAME, ProfileError, find_profile, load_profile, validate_profile


def parse_source(value: str) -> dict[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("source must use provider=location")
    provider, location = value.split("=", 1)
    if not provider or not location:
        raise argparse.ArgumentTypeError("source must use provider=location")
    return {"provider": provider, "location": location}


def command_init(args: argparse.Namespace) -> int:
    output = args.output.expanduser().resolve()
    if output.name != PROFILE_NAME:
        output = output / PROFILE_NAME
    if output.exists() and not args.force:
        raise SystemExit(f"Profile already exists: {output}")
    profile = {
        "version": 1,
        "memory": {"provider": args.memory_provider, "location": args.memory_location},
        "papers": args.paper_source,
        "naming": {"note": args.note_naming},
        "links": {"style": args.link_style, "backlinks": args.backlinks, "index": None},
        "attachments": {"mode": args.attachment_mode},
        "metadata": {"fields": ["title", "date", "tags"], "preserve_unknown_fields": True},
        "tags": {
            "strategy": args.tag_strategy,
            "language": args.tag_language,
            "allowed_namespaces": (
                args.tag_namespace
                if args.tag_namespace
                else (["论文", "方法", "任务", "模态"] if args.tag_strategy == "recommended" else [])
            ),
            "reject_aliases": args.reject_aliases,
        },
        "review": {"persistence": args.review_persistence},
    }
    if args.attachment_mode == "local":
        profile["attachments"].update(
            {"root_pattern": args.attachment_pattern, "link_style": args.attachment_link_style}
        )
    errors = validate_profile(profile)
    if errors:
        raise SystemExit("Invalid profile:\n- " + "\n- ".join(errors))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)
    return 0


def resolve_profile(value: Path) -> Path:
    value = value.expanduser().resolve()
    if value.is_file():
        return value
    result = find_profile(value)
    if result is None:
        raise SystemExit(f"No {PROFILE_NAME} found from {value}")
    return result


def command_read(args: argparse.Namespace, validate_only: bool) -> int:
    path = resolve_profile(args.path)
    try:
        profile = load_profile(path)
    except ProfileError as error:
        raise SystemExit(str(error)) from error
    errors = validate_profile(profile)
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors))
        return 1
    if validate_only:
        print(f"VALID: {path}")
    else:
        print(json.dumps(profile, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    init = subparsers.add_parser("init")
    init.add_argument("--output", type=Path, required=True)
    init.add_argument("--memory-provider", choices=("markdown", "obsidian", "notion", "other"), required=True)
    init.add_argument("--memory-location", required=True)
    init.add_argument("--paper-source", action="append", type=parse_source, required=True)
    init.add_argument("--note-naming", default="short-title")
    init.add_argument("--link-style", choices=("markdown", "wiki", "notion", "none"), default="none")
    init.add_argument("--backlinks", choices=("maintain", "suggest", "none"), default="none")
    init.add_argument("--attachment-mode", choices=("local", "platform", "none"), default="none")
    init.add_argument("--attachment-pattern", default="./assets/${noteFileName}")
    init.add_argument("--attachment-link-style", choices=("markdown", "wiki"), default="markdown")
    init.add_argument("--tag-strategy", choices=("preserve", "recommended", "custom"), default="preserve")
    init.add_argument("--tag-language")
    init.add_argument("--tag-namespace", action="append", default=[])
    init.add_argument("--reject-aliases", action="store_true")
    init.add_argument("--review-persistence", choices=("body", "metadata", "external", "none"), default="none")
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=lambda args: command_init(args))
    for name, validate_only in (("show", False), ("validate", True)):
        command = subparsers.add_parser(name)
        command.add_argument("path", type=Path)
        command.set_defaults(func=lambda args, value=validate_only: command_read(args, value))
    return parser


if __name__ == "__main__":
    arguments = build_parser().parse_args()
    raise SystemExit(arguments.func(arguments))
