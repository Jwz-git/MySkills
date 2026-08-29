#!/usr/bin/env python3
"""解析文章归档偏好，并规划不会静默覆盖的输出路径。"""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any


DEFAULTS: dict[str, Any] = {
    "version": 1,
    "output_dir": "articles",
    "assets": {"mode": "download", "directory": "assets"},
}

CONFIG_NAME = ".article-archiver.json"
PERSONAL_CONFIG = Path.home() / ".codex" / "article-archiver.json"
INVALID_FILENAME = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


class ConfigError(RuntimeError):
    pass


def merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = value
    return result


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"无法读取 {path}：{exc}") from exc
    if not isinstance(value, dict):
        raise ConfigError(f"配置根节点必须是对象：{path}")
    return value


def project_config(cwd: Path) -> Path | None:
    current = cwd.resolve()
    for directory in (current, *current.parents):
        candidate = directory / CONFIG_NAME
        if candidate.exists():
            return candidate
    return None


def validate(config: dict[str, Any]) -> None:
    if config.get("version") != 1:
        raise ConfigError("目前只支持版本 1 的配置")
    if not isinstance(config.get("output_dir"), str) or not config["output_dir"].strip():
        raise ConfigError("output_dir 必须是非空字符串")
    asset_directory = config.get("assets", {}).get("directory")
    if not isinstance(asset_directory, str) or not asset_directory.strip():
        raise ConfigError("assets.directory 必须是非空字符串")
    asset_mode = config.get("assets", {}).get("mode")
    if asset_mode not in {"download", "remote", "omit"}:
        raise ConfigError(f"不支持的 assets.mode：{asset_mode}")


def resolve(cwd: Path) -> tuple[dict[str, Any], Path | None]:
    config = merge(DEFAULTS, read_json(PERSONAL_CONFIG))
    found = project_config(cwd)
    if found:
        config = merge(config, read_json(found))
    validate(config)
    return config, found


def atomic_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def target_for_scope(scope: str, cwd: Path) -> Path:
    return PERSONAL_CONFIG if scope == "personal" else cwd.resolve() / CONFIG_NAME


def parse_scalar(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def set_dotted(config: dict[str, Any], dotted: str, value: Any) -> None:
    keys = dotted.split(".")
    if not all(keys):
        raise ConfigError("点号路径配置键无效")
    cursor = config
    for key in keys[:-1]:
        child = cursor.setdefault(key, {})
        if not isinstance(child, dict):
            raise ConfigError(f"无法在非对象配置键下设置子项：{key}")
        cursor = child
    cursor[keys[-1]] = value


def safe_stem(value: str) -> str:
    stem = value[:-3] if value.lower().endswith(".md") else value
    stem = INVALID_FILENAME.sub("-", stem).strip().rstrip(".")
    stem = re.sub(r"\s+", " ", stem)
    if stem in {"", ".", ".."}:
        raise ConfigError("标题无法生成有效文件名")
    return stem


def planned_paths(config: dict[str, Any], cwd: Path, title: str) -> list[Path]:
    stem = safe_stem(title)
    root = Path(config["output_dir"])
    if not root.is_absolute():
        root = cwd.resolve() / root
    paths = [root / f"{stem}.md"]
    asset_root = root / config["assets"]["directory"] / stem
    if config["assets"]["mode"] == "download":
        paths.append(asset_root)
    return paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("resolve", "plan"):
        command = sub.add_parser(name)
        command.add_argument("--cwd", type=Path, default=Path.cwd())
        if name == "plan":
            command.add_argument("--title", required=True)
    init = sub.add_parser("init")
    init.add_argument("--scope", choices=("project", "personal"), required=True)
    init.add_argument("--cwd", type=Path, default=Path.cwd())
    init.add_argument("--output-dir", default="articles")
    init.add_argument("--assets", choices=("download", "remote", "omit"), default="download")
    init.add_argument("--assets-directory", default="assets")
    init.add_argument("--force", action="store_true")
    setting = sub.add_parser("set")
    setting.add_argument("--scope", choices=("project", "personal"), required=True)
    setting.add_argument("--cwd", type=Path, default=Path.cwd())
    setting.add_argument("key")
    setting.add_argument("value")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "resolve":
            config, found = resolve(args.cwd)
            print(json.dumps({"config": config, "personal_config": str(PERSONAL_CONFIG), "project_config": str(found) if found else None}, ensure_ascii=False, indent=2))
        elif args.command == "init":
            path = target_for_scope(args.scope, args.cwd)
            if path.exists() and not args.force:
                raise ConfigError(f"拒绝替换已有配置：{path}")
            config = merge(DEFAULTS, {
                "output_dir": args.output_dir,
                "assets": {"mode": args.assets, "directory": args.assets_directory},
            })
            validate(config)
            atomic_write(path, config)
            print(path)
        elif args.command == "set":
            path = target_for_scope(args.scope, args.cwd)
            config = read_json(path)
            set_dotted(config, args.key, parse_scalar(args.value))
            validate(merge(DEFAULTS, config))
            atomic_write(path, config)
            print(path)
        elif args.command == "plan":
            config, _ = resolve(args.cwd)
            paths = planned_paths(config, args.cwd, args.title)
            conflicts = [str(path) for path in paths if path.exists()]
            print(json.dumps({"paths": [str(path) for path in paths], "conflicts": conflicts, "safe": not conflicts}, ensure_ascii=False, indent=2))
            return 0 if not conflicts else 2
        return 0
    except ConfigError as exc:
        print(f"错误：{exc}", file=os.sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
