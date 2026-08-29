#!/usr/bin/env python3
"""Shared loading, normalization, and validation for paper-memory profiles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROFILE_NAME = ".paper-memory.yaml"
MEMORY_PROVIDERS = {"markdown", "obsidian", "notion", "other"}
LINK_STYLES = {"markdown", "wiki", "notion", "none"}
BACKLINK_MODES = {"maintain", "suggest", "none"}
ATTACHMENT_MODES = {"local", "platform", "none"}
TAG_STRATEGIES = {"preserve", "recommended", "custom"}
REVIEW_MODES = {"body", "metadata", "external", "none"}


class ProfileError(ValueError):
    pass


def _yaml_loader() -> Any:
    try:
        import yaml  # type: ignore
    except ImportError:
        return None
    return yaml


def load_profile(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig")
    yaml = _yaml_loader()
    if yaml is not None:
        data = yaml.safe_load(text)
    else:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            raise ProfileError(
                "Profile requires PyYAML unless it uses JSON-compatible YAML: "
                f"{path}: {error}"
            ) from error
    if not isinstance(data, dict):
        raise ProfileError(f"Profile root must be a mapping: {path}")
    return normalize_profile(data)


def normalize_profile(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize the original v1 draft into the canonical v1 structure."""
    profile = dict(raw)
    if "memory" not in profile and ("platform" in profile or "memory_root" in profile):
        profile["memory"] = {
            "provider": profile.pop("platform", "markdown"),
            "location": profile.pop("memory_root", None),
        }
    if "papers" not in profile and "paper_sources" in profile:
        sources = profile.pop("paper_sources") or []
        if not isinstance(sources, list):
            sources = [sources]
        profile["papers"] = [
            {"provider": "filesystem", "location": source} for source in sources
        ]

    profile.setdefault("version", 1)
    profile.setdefault("memory", {})
    profile.setdefault("papers", [])
    profile.setdefault("naming", {"note": "short-title"})
    profile.setdefault("links", {"style": "none", "backlinks": "none", "index": None})
    profile.setdefault("attachments", {"mode": "none"})
    profile.setdefault(
        "metadata", {"fields": ["title", "date", "tags"], "preserve_unknown_fields": True}
    )
    profile.setdefault(
        "tags",
        {
            "strategy": "preserve",
            "language": None,
            "allowed_namespaces": [],
            "reject_aliases": False,
        },
    )
    profile.setdefault("review", {"persistence": "none"})

    attachments = profile["attachments"]
    if isinstance(attachments, dict) and "mode" not in attachments:
        attachments["mode"] = "local" if attachments.get("root_pattern") else "none"
    tags = profile["tags"]
    if isinstance(tags, dict):
        if "allowed_namespaces" not in tags and "namespaces" in tags:
            tags["allowed_namespaces"] = tags.pop("namespaces")
        tags.setdefault("strategy", "custom" if tags.get("allowed_namespaces") else "preserve")
        tags.setdefault("reject_aliases", False)
    return profile


def validate_profile(profile: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if profile.get("version") != 1:
        errors.append("version must be 1")

    memory = profile.get("memory")
    if not isinstance(memory, dict):
        errors.append("memory must be a mapping")
    else:
        if memory.get("provider") not in MEMORY_PROVIDERS:
            errors.append(f"memory.provider must be one of {sorted(MEMORY_PROVIDERS)}")
        if not memory.get("location"):
            errors.append("memory.location is required")

    papers = profile.get("papers")
    if not isinstance(papers, list) or not papers:
        errors.append("papers must contain at least one source")
    elif any(not isinstance(item, dict) or not item.get("provider") or not item.get("location") for item in papers):
        errors.append("every papers item requires provider and location")

    links = profile.get("links")
    if not isinstance(links, dict):
        errors.append("links must be a mapping")
    else:
        if links.get("style") not in LINK_STYLES:
            errors.append(f"links.style must be one of {sorted(LINK_STYLES)}")
        if links.get("backlinks") not in BACKLINK_MODES:
            errors.append(f"links.backlinks must be one of {sorted(BACKLINK_MODES)}")

    attachments = profile.get("attachments")
    if not isinstance(attachments, dict):
        errors.append("attachments must be a mapping")
    else:
        if attachments.get("mode") not in ATTACHMENT_MODES:
            errors.append(f"attachments.mode must be one of {sorted(ATTACHMENT_MODES)}")
        if attachments.get("mode") == "local" and not attachments.get("root_pattern"):
            errors.append("attachments.root_pattern is required when mode is local")
        if attachments.get("mode") == "local" and attachments.get("link_style") not in {"markdown", "wiki"}:
            errors.append("attachments.link_style must be markdown or wiki when mode is local")
        pattern = str(attachments.get("root_pattern", ""))
        remainder = pattern.replace("${noteFileName}", "").replace("${noteDir}", "")
        if "${" in remainder:
            errors.append("attachments.root_pattern contains an unsupported variable")

    metadata = profile.get("metadata")
    if not isinstance(metadata, dict):
        errors.append("metadata must be a mapping")
    else:
        fields = metadata.get("fields")
        if not isinstance(fields, list) or any(not isinstance(field, str) for field in fields):
            errors.append("metadata.fields must be a list of strings")
        if not isinstance(metadata.get("preserve_unknown_fields"), bool):
            errors.append("metadata.preserve_unknown_fields must be true or false")

    tags = profile.get("tags")
    if not isinstance(tags, dict):
        errors.append("tags must be a mapping")
    else:
        if tags.get("strategy") not in TAG_STRATEGIES:
            errors.append(f"tags.strategy must be one of {sorted(TAG_STRATEGIES)}")
        if tags.get("strategy") in {"recommended", "custom"} and not tags.get("allowed_namespaces"):
            errors.append("tags.allowed_namespaces is required for recommended or custom strategy")

    review = profile.get("review")
    if not isinstance(review, dict) or review.get("persistence") not in REVIEW_MODES:
        errors.append(f"review.persistence must be one of {sorted(REVIEW_MODES)}")
    return errors


def find_profile(start: Path) -> Path | None:
    current = start.expanduser().resolve()
    if current.is_file():
        current = current.parent
    for directory in (current, *current.parents):
        candidate = directory / PROFILE_NAME
        if candidate.is_file():
            return candidate
    return None


def local_memory_root(profile: dict[str, Any], profile_path: Path) -> Path | None:
    memory = profile["memory"]
    if memory.get("provider") not in {"markdown", "obsidian"}:
        return None
    location = Path(str(memory["location"])).expanduser()
    if not location.is_absolute():
        location = profile_path.parent / location
    return location.resolve()


def expand_attachment_parent(pattern: str, note: Path) -> Path:
    value = pattern.replace("${noteFileName}", note.stem).replace("${noteDir}", str(note.parent))
    target = Path(value).expanduser()
    if not target.is_absolute():
        target = note.parent / target
    return target.resolve()
