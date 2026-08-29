# 首次配置与本地化规范

首次对某个论文资料库执行持久化读取或写入时使用。目标是生成可复用的 `.paper-memory.yaml`，不是修改共享 Skill。

## 1. 查找与读取

使用：

```bash
python3 scripts/manage_profile.py show <Memory 文件、Memory 根目录或其子目录>
```

工具从目标位置向上查找最近的 `.paper-memory.yaml`，兼容早期的 `platform`、`memory_root`、`paper_sources` 字段。若找到多个候选，使用与目标路径最近的 profile；不得跨资料库复用。

如果用户只说“启用”而没有提供任何目标位置，不进行无边界的全盘搜索，直接询问下述必要配置。

## 2. 首次必须确认

找不到 profile 且任务需要持久化资料时，一次集中询问：

1. **Memory 存储**：本地 Markdown、Obsidian、Notion 或其他系统，以及目录、database/page 等稳定位置。远程存储还要确认 `.paper-memory.yaml` 放在哪个本地配置目录。
2. **论文来源**：PDF、HTML、补充材料或代码位于本地目录、URL、Zotero 或其他来源；允许多个来源。
3. **本次权限范围**：只读、允许创建 Memory，或允许更新既有 Memory。不要把配置确认视为额外写入授权。

只有影响当前任务时才继续确认：文件/页面命名、内部链接、反向链接、索引、附件、元数据、标签和复习记录策略。先检查一致的既有样本；可可靠推断时展示推断并请求一次确认。

## 3. Canonical profile

Profile 使用以下结构。工具生成 JSON-compatible YAML，以便没有 PyYAML 时仍能可靠读取；普通 YAML 也受支持，但运行环境需要 PyYAML。

```yaml
version: 1
memory:
  provider: obsidian       # markdown | obsidian | notion | other
  location: /vault/papers  # 本地路径或稳定的 database/page 标识
papers:
  - provider: filesystem
    location: /library/pdfs
naming:
  note: short-title
links:
  style: wiki              # markdown | wiki | notion | none
  backlinks: suggest       # maintain | suggest | none
  index: MOCs/
attachments:
  mode: local              # local | platform | none
  root_pattern: "./assets/${noteFileName}"
  link_style: markdown
metadata:
  fields: [title, date, tags]
  preserve_unknown_fields: true
tags:
  strategy: recommended    # preserve | recommended | custom
  language: zh
  allowed_namespaces: [论文, 方法, 任务, 模态]
  reject_aliases: false
review:
  persistence: body        # body | metadata | external | none
```

`memory` 与 `papers` 分开建模，以支持“PDF 在本地、Memory 在 Notion”等混合环境。Notion 或其他远程系统使用稳定标识，不保存访问令牌。

## 4. 初始化与验证

向用户展示摘要并取得确认后，调用初始化工具。`--output` 是 profile 的本地保存目录，不一定等于远程 Memory 的 location。示例：

```bash
python3 scripts/manage_profile.py init \
  --output /vault/papers \
  --memory-provider obsidian \
  --memory-location /vault/papers \
  --paper-source filesystem=/library/pdfs \
  --link-style wiki \
  --backlinks suggest \
  --attachment-mode local \
  --tag-strategy recommended \
  --tag-language zh \
  --review-persistence body
python3 scripts/manage_profile.py validate /vault/papers
```

不得使用 `--force` 覆盖现有 profile，除非用户明确要求覆盖且已展示差异。后续变更只编辑用户确认的字段，并再次运行 `validate`。

## 5. 冲突和失败

- 实际资料库与 profile 冲突时停止批量写入，让用户选择以哪一方为准。
- Profile 只保存工作流配置，不保存密钥、访问令牌或账号凭据。
- 无法写入本地 profile 时，在会话中保留已确认配置并给出可复制内容，不声称已经持久化。
- Profile 配置的是行为，不代替执行权限；外部系统写入仍遵循当前授权边界。
