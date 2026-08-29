---
name: article-archiver
description: 从 URL 提取公开文章或帖子串，去除页面噪声后以原文和原标题归档为 Markdown，并下载关联资源。适用于单篇或批量归档 X、个人博客、知乎及类似页面；也支持用户明确要求的总结、翻译或其他转换，不得用于绕过访问控制。
---

# 文章归档

将一个或多个文章 URL 保存为可追溯的 Markdown。默认只去除页面噪声和规范格式，不改写正文。

## 配置

抓取前运行：

```bash
python3 <skill目录>/scripts/archive_config.py resolve --cwd "$PWD"
```

脚本路径相对本 `SKILL.md` 解析。配置由个人默认值 `~/.codex/article-archiver.json` 与最近的项目 `.article-archiver.json` 合并，项目配置优先。

首次使用且没有配置时，只询问当前请求尚未明确的项目：Markdown 输出目录、资源下载方式、配置保存为项目还是个人范围。用 `archive_config.py init` 持久化；修改个人配置前必须确认。配置操作详见 [configuration.md](references/configuration.md)。

## 获取原文

先直接读取规范 URL；失败或正文不完整时，再读取浏览器中的可见页面。处理 X、知乎、登录页面或帖子串时，阅读 [acquisition.md](references/acquisition.md)。可以使用用户已有登录状态，但不得绕过登录、付费墙、验证码、robots 或其他访问控制。

提取标题、作者、原始发布时间、正文、图片、图注、代码、表格、公式、引用和脚注；排除导航、广告、推荐、评论及其他页面噪声。检查开头、结尾、折叠内容、分页和帖子串连续性。无法确认完整时，停下来询问是否以“不完整”状态保存。

批量处理中，各 URL 独立标记为 `saved`、`incomplete`、`failed` 或 `conflict`；单篇失败不阻塞其他独立项目。

## 保存规则

默认使用经核验的原标题，不另拟标题；正文保持原有措辞、顺序和结构，只修正 Markdown 层级、空白、列表、代码块等格式。除非用户明确要求，不添加摘要、不翻译、不重排、不改写。

使用以下 frontmatter。无法核验的值留空；`tags` 根据文章主题提取少量明确标签，无法判断时使用空数组：

```yaml
---
title: ""
author: ""
published: ""
source_url: ""
language: ""
tags: []
---
```

`published` 只能使用来源明确标注的原始发布时间。不得添加抓取时间、内容哈希或 `mode`。

用户未指定文件名时，保存为 `<输出目录>/<原标题>.md`，只替换文件系统不允许的字符。下载的资源放入 `<输出目录>/assets/<归档文件名>/`，其中归档文件名不含 `.md`；Markdown 使用正确的相对路径引用。

写入前运行：

```bash
python3 <skill目录>/scripts/archive_config.py plan --cwd <目标项目> --title <标题或文件名>
```

任何目标存在时必须停下来询问，不得静默覆盖。完成后报告准确文件路径、失败或不完整的 URL，以及无法核验的元数据。
