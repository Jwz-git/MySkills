# 配置

个人配置位于 `~/.codex/article-archiver.json`；项目配置是从当前目录向上找到的最近一个 `.article-archiver.json`，并覆盖个人配置。修改个人配置前必须取得确认；不要自动修改 `.gitignore`。

默认配置：

```json
{
  "version": 1,
  "output_dir": "articles",
  "assets": {
    "mode": "download",
    "directory": "assets"
  }
}
```

输出为 `<output_dir>/<原标题>.md`；下载资源时保存到 `<output_dir>/<assets.directory>/<原标题>/`。`assets.mode` 支持 `download`、`remote` 和 `omit`。下载失败时保留远程 URL 并报告失败。

初始化项目配置：

```bash
python3 <skill目录>/scripts/archive_config.py init --scope project --cwd /path/to/project \
  --output-dir articles --assets download --assets-directory assets
```

将 `project` 换成 `personal` 可初始化个人配置。更新单项配置：

```bash
python3 <skill目录>/scripts/archive_config.py set --scope project --cwd /path/to/project \
  assets.mode remote
```

脚本原子写入 JSON。`init` 默认拒绝替换已有配置；只有用户明确确认后才能使用 `--force`。
