---
name: paper-memory
description: 处理学术论文的长期记忆工作流，包括结构化总结、主动回忆、论文对比、知识关联、理解更新和核心图表提取；也用于创建或维护该技能生成的论文 Memory。支持本地 Markdown、Obsidian、Notion 等不同存储环境，并在首次使用时建立本地配置。通用编程、普通文件整理或非论文任务不要调用。
---

# 论文记忆 Skill

将论文压缩为结构稳定、可长期复习的 Memory，并支持主动回忆、论文对比、知识关联和非破坏性理解更新。Memory 的正文结构由 [templates/](templates/) 定义；存储平台、目录、链接、元数据、标签和附件规则由用户的本地 profile 决定。

## 1. 首次使用与本地 profile

任何会读取、创建或修改持久化论文资料的任务，开始前先执行 [首次配置与本地化规范](references/setup-profile.md)：

1. 使用 `scripts/manage_profile.py show <目标路径>` 查找并读取当前资料库的 `.paper-memory.yaml`。
2. 找到后读取并遵循，不重复询问已配置且与本次任务无冲突的信息。
3. 找不到时，在执行持久化操作前一次确认：Memory 存储及位置、论文来源、本次只读/创建/更新范围；远程存储还要确认 profile 的本地保存目录。
4. 根据平台和任务继续确认真正影响结果的链接、附件、元数据及标签策略；不得擅自套用 Obsidian 或当前示例中的约定。
5. 向用户复述配置并获得确认后，使用 `scripts/manage_profile.py init` 写入 profile，再运行 `validate`。本地 Memory 默认写在 Memory 根目录；远程 Memory 写在用户确认的本地配置目录。不要为了本地化改写本 Skill 的 `SKILL.md` 或共享 references。

纯对话式解释或用户明确只要临时输出、不落盘时，可以跳过 profile，但不得臆造目录或平台功能。

## 2. 模式路由

根据用户意图选择内容模式；图片附件是可单独执行或与内容模式组合的横切流程。详细规则见 [references/routing.md](references/routing.md)：

- **compress**：生成 Flash Card、Standard Memory 或 Deep Memory。
- **review**：进行交互式主动回忆。
- **connect**：建立论文关系，并按平台能力维护链接或索引。
- **compare**：按一致维度比较多篇论文。
- **update**：透明、非破坏性地更新已有理解。
- **attachment**：提取、引用、审计或迁移论文图片；纯附件维护不追加理解更新记录。

## 3. 执行流程

1. 加载本地 profile；首次持久化使用时先完成配置。
2. 判断用户意图、论文类型、所需粒度和必要的讲解深度。非计算论文或混合论文加载 [references/paper-types.md](references/paper-types.md)；只有用户表达不足以选择输出深度时，才参考 [references/user-levels.md](references/user-levels.md)。
3. 按模式加载对应指南：
   - compress：[references/compress-guide.md](references/compress-guide.md)
   - review：[references/review-guide.md](references/review-guide.md)
   - connect：[references/connect-guide.md](references/connect-guide.md)，并只加载 profile 对应的平台指南
   - compare：[references/compare-guide.md](references/compare-guide.md)
   - update：[references/update-guide.md](references/update-guide.md)
   - 标签生成或整理：[references/tag-taxonomy.md](references/tag-taxonomy.md)
   - 图片操作：[references/attachment-guide.md](references/attachment-guide.md)
4. 始终应用 [references/evidence-rules.md](references/evidence-rules.md)。
5. 使用 [templates/](templates/) 中的目标模板；保持模板正文的章节结构，不因平台不同删改核心章节。
6. 写入前确认目标位于 profile 指定范围内；写入后验证链接、附件和受影响文件。

## 4. 通用约束

- **证据边界**：明确区分论文事实、用户理解、AI 分析和待验证假设。缺失信息使用“当前材料无法确认”“论文未报告”或“尚未核验”，不得补造。
- **尊重已有系统**：已有知识库的命名、链接、元数据、标签和附件约定优先于默认建议。发现配置与实际内容不一致时，先报告，不静默迁移或重写。
- **平台能力边界**：只使用目标平台实际支持的功能。Obsidian Wiki Link、Notion database property、Markdown frontmatter 等不能互相假定等价。
- **Memory 结构稳定**：Flash、Standard 和 Deep Memory 的正文结构保持与模板一致；平台差异只影响存储、链接、元数据和附件表达。
- **非破坏性维护**：既有未引用附件只报告，不自动删除；只可清理本次任务明确生成且已确认无用的临时文件。
- **图片质量**：需要展示架构或模块流向时优先采用能准确表达论文内容的原图；提取后视觉复核完整性和可读性。

## 5. 完成标准

- **Compress**：遵循目标模板，突出研究问题、核心方法、作用、证据边界和局限。
- **Review**：不先泄露答案；根据 Memory 进行主动回忆、反馈和分维度评分。
- **Connect**：关系语义准确，并使用 profile 规定的平台链接或索引方式。
- **Compare**：使用适合论文类型的一致维度，明确不可直接比较的实验条件，并给出有前提的选择建议。
- **Update**：保留历史语义；正文变化有可追踪的理解更新记录，纯元数据或附件维护除外。
- **Attachment**：所有已引用本地图片可解析、无错误归属；论文原件及既有未引用文件未被误迁移或误删。
