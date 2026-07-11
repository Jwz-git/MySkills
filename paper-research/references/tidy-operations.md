# 批量重写与格式整理操作规范

本文件同时覆盖 `batch-rewrite` 与 `tidy-only`。两者权限不同：

- `batch-rewrite`：用户授权重建正文，可依据论文原文修正事实、结构与表达。
- `tidy-only`：只改元数据、标签、链接和标题层级，保留正文观点；发现事实问题只报告。

执行前先写明模式，不能把二者混用。

## 1. 事务式批量流程

### 1.1 Inventory

使用 `find`、Python `pathlib` 或本技能脚本枚举目标，不依赖 `rg`。为每个 Markdown 记录：

| 字段 | 说明 |
|---|---|
| `input_md` | 现有笔记绝对路径 |
| `output_md` | 目标路径；重写默认同路径 |
| `pdf` | 本地 PDF；可为空 |
| `official_url` | arXiv/DOI/会议/出版社页 |
| `canonical_id` | DOI 或 arXiv ID |
| `source_version` | 实际阅读版本/日期 |
| `analysis_scope` | full-text / partial / abstract-only |
| `figure_dir` | 最终图片目录 |
| `status` | discovered/mapped/staged/validated/rewritten/failed |
| `notes` | 歧义、缺失、人工决策 |

不要只按 stem 自动认定映射。先用 stem 找候选，再以 PDF 首页标题、作者、canonical ID 核对。文件名与方法简称不一致时保留用户文件名，并在 manifest/笔记中说明。

### 1.2 Snapshot

在本次运行临时目录保存：

- 原始目标文件副本。
- 文件 SHA-256。
- inventory/manifest。
- 已存在图片目录清单。

快照用于回溯和质量比较，不允许覆盖用户的正式目录。临时目录按 run 隔离，只删除本次 manifest 拥有的文件。

### 1.3 Stage

逐篇生成独立的暂存产物与图像清单。一个文件失败时记录 `failed`，继续处理其他文件。不要在内容尚未读取、路径未核验前进行全目录机械替换。

`batch-rewrite` 使用 `analysis-guide.md` 唯一模板；`tidy-only` 只应用第 3 节允许的操作。

### 1.4 Validate

对每个暂存文件执行：

1. 结构/路径自动校验。
2. PDF 身份和版本核对。
3. 一句话总结、证据表、所有高亮数字与强结论的原文抽查。
4. 每张最终图视觉检查。

错误文件不得替换正式目标；警告需汇总并判断是否可接受。

### 1.5 Replace

只把通过验收的文件放入正式目录。保留用户未在范围内的文件与资产；不删除未知文件。若因个别失败导致目录暂时混合新旧版本，在报告中逐项说明，不能声称“全部完成”。

### 1.6 Report

至少报告：

```text
discovered: N
mapped: N
rewritten: N
unchanged: N
failed: N
errors: N
warnings: N
```

逐项列出失败文件、错误和未解决警告。汇总表中的“通过”必须对应实际自动校验和证据抽查。

## 2. Frontmatter 规范

固定字段和顺序：

```yaml
---
title: "论文完整标题"
date: YYYY-MM-DD
tags:
  - paper/topic-one
  - paper/topic-two
aliases:
  - Paper Acronym
---
```

规则：

- `batch-rewrite` 同一 run 使用同一整理日期；`tidy-only` 保留合法的既有日期，除非用户要求更新。
- 标签为唯一的 `paper/<lower-kebab-case>`，通常 2–5 个；不用 `VLM`、`LoRA` 等扁平标签。
- aliases 去重，包含论文简称、常用方法名或用户已有可靠别名。
- 移除 `original_pdf`、`arxiv`、`pdf`、`category` 等与正文原文行重复的冗余字段。
- YAML 中含 `:`、`#`、`&` 或引号的标题优先使用双引号并正确转义。

常用标签示例：

| 概念 | 标签 |
|---|---|
| Vision-Language Model | `paper/vlm` |
| Large Language Model | `paper/llm` |
| LoRA | `paper/lora` |
| NAS | `paper/nas` |
| Retrieval | `paper/retrieval` |
| Localization | `paper/localization` |
| Point cloud | `paper/point-cloud` |
| Multimodal | `paper/multimodal` |
| Embedding | `paper/embedding` |
| Memory | `paper/memory` |
| Benchmark | `paper/benchmark` |

标签表达主题，不把会议、年份或每个方法简称都变成标签。

## 3. 原文链接与路径

原文行是 frontmatter 后第一个非空块：

```markdown
**原文**: [本地](../论文原件/Paper.pdf) [网络](https://arxiv.org/abs/0000.00000)
```

按资源可用性省略本地或网络项。路径必须根据 Markdown 文件实际位置计算，不能假设 vault 根路径会被普通 Markdown 解析。

特殊字符路径：

```markdown
[本地](<../论文原件/Point-Bind & Point-LLM.pdf>)
```

外部链接优先 DOI/正式会议或期刊页；预印本可保留 arXiv。错误 ID 必须先核对标题和 PDF 水印再修正。

## 4. `tidy-only` 允许的操作

1. 补全或规范 frontmatter。
2. 扁平标签映射为 `paper/...` 并去重。
3. 添加/修正本地 PDF 与官方网络链接。
4. 只在不改变语义时调整一级/二级标题和空行。
5. 校验并修复已存在的图片相对路径。
6. 删除明确的模板占位符或冗余字段时，先确认不会丢失用户内容。

`tidy-only` 不应：

- 凭摘要补写方法、实验或局限。
- 删除用户分析或评论。
- 用新的通用模板覆盖整篇正文。
- 把 Mermaid 自动替换成假装来自论文的图。

若用户需要完全统一且现有正文不满足模板，应明确切换到 `batch-rewrite`。

## 5. `batch-rewrite` 内容规则

1. 以完整 PDF/官方材料重建正文，不能只润色旧笔记；旧笔记可作为问题清单或线索。
2. 旧笔记与原文冲突时采用原文，并修复标题、ID、公式方向、指标口径和链接。
3. 去除所有 Mermaid，用原论文关键图或说明无图原因。
4. 所有文件使用同一精确标题层级和证据表格式。
5. 将旧 `[待补充]`、`[推断]` 转换为明确缺失状态或有依据的分析判断。
6. 保留有价值的知识库内部链接，但放入相关小节，不能新增额外一级标题。
7. 对 PDF 缺失或材料受限的文件降级分析依据，不用其他相邻论文替代。

## 6. 映射与命名

- 默认保留已有 Markdown 文件名，避免破坏 Obsidian 链接。
- PDF 同名只是候选映射；使用标题、作者、ID 确认。
- 新建笔记名发生冲突时追加 canonical ID，例如 `Retrieval-2410.00001.md`。
- 图像目录默认使用现有 note stem；manifest 记录 note、PDF、图像目录三者关系。
- 一篇联合论文包含多个方法时保持单一来源，不因方法名拆成多篇。

## 7. 自动校验

```bash
python3 scripts/validate_notes.py /path/to/AI分析 --strict
```

检查范围包括：

- frontmatter 字段、日期、标签和 aliases。
- 原文行位置和本地链接。
- 四个一级标题、五个核心二级标题及顺序。
- 核心证据表、分析依据、定位数量。
- info/abstract callout。
- Mermaid、`[待补充]`、TODO、模板占位符。
- 图片链接、alt 和图号/页码说明。
- 目录内 canonical ID 重复。

脚本的 warning 不代表事实正确。批量完成后仍需按照 `evidence-policy.md` 做人工证据审计。

## 8. 远程与受限环境

- 不假设 `rg` 存在；使用 `find` 或 Python `pathlib`。
- 不假设 PyMuPDF、OCR 或 YAML 库存在；基础清单和校验脚本仅依赖 Python 标准库。
- 依赖缺失时优先降级并报告，不隐式安装到全局环境。
- 网络不可用时使用本地 PDF；需要核验动态事实但无法联网时写 `未核验`。

