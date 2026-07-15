---
name: paper-memory
description: 只有在处理学术论文（包括总结、复习、对比、主动回忆学术文献等），或者修改/更新由该技能生成的 markdown 文档（如论文笔记、记忆卡片、Obsidian 双链笔记及其 frontmatter/tags）时才调用此技能。在进行通用编程开发、系统配置或其它不相关的任务时，请勿调用此技能。
---

# 论文记忆 Skill

一个专为研究者和学习者设计的 Skill，用于在兼容 Obsidian 双向链接的知识网络中对科学论文进行压缩、复习、关联、比较和更新。

## 1. 核心定位
`paper-memory` 的目标并非从头阅读一篇论文或生成冗长的摘要报告，而是：
- 将已读/已讨论的论文压缩为可长期复习的记忆卡片。
- 帮助用户进行主动回忆练习，而非被动阅读。
- 将论文无缝集成到 Obsidian 知识图谱中，保持清晰的双向链接。
- 比较论文并安全地更新用户的理解。
- 区分论文事实、用户理解、AI 分析和假说。

## 2. 模式路由概览
根据用户意图，路由到以下五种模式之一。详细触发条件请参阅 [references/routing.md](references/routing.md)：
- **compress**：将论文细节压缩为 Flash Card、Standard Memory 或 Deep Memory 格式。
- **review**：进行交互式主动回忆复习。
- **connect**：构建 Obsidian 双向 Wiki 链接并更新 Map of Content（MOC）。
- **compare**：按照标准化维度比较多篇论文。
- **update**：对已有论文笔记进行安全的、非破坏性的更新。

## 3. 工作流程
当此 Skill 被触发时：
1. **检测水平与意图**：
   - 评估用户的专业水平：Beginner、Intermediate 或 Advanced。参见 [references/user-levels.md](references/user-levels.md)。
   - 确定目标模式和所需粒度（Flash Card、Standard Memory、Deep Memory）。
2. **查阅参考指南**：
   - **compress** 模式：加载 [references/compress-guide.md](references/compress-guide.md)。
   - **review** 模式：加载 [references/review-guide.md](references/review-guide.md)。
   - **connect** 模式：加载 [references/connect-obsidian.md](references/connect-obsidian.md)。
   - **compare** 模式：加载 [references/compare-guide.md](references/compare-guide.md)。
   - **update** 模式：加载 [references/update-guide.md](references/update-guide.md)。
   - **生成或整理标签**：加载 [references/tag-taxonomy.md](references/tag-taxonomy.md)；批量修改后运行 `scripts/audit_tags.py`。
   - 始终应用 [references/evidence-rules.md](references/evidence-rules.md) 以确保事实完整性。
3. **执行模式特定操作**：
   - 使用 [templates/](templates/) 中的模板渲染相应布局。
   - 确保 Obsidian 文件使用简洁命名：`CLIP.md`、`DINOv2.md` 或 `ALIGN-2021.md`。
4. **确保双向链接与 MOC 链接**：
   - 提供"反向更新建议"，或在获得权限后直接更新文件。

## 4. Obsidian Vault 路径配置
首次使用时，询问用户的 Obsidian Vault 路径（例如 `~/Documents/Research-Vault/`）。在整个对话过程中记住该路径。在 `connect` 或 `update` 模式下拥有文件写入权限时，使用该路径定位并修改已有笔记。如果用户未指定路径，则以 Markdown 代码块形式输出笔记，供用户手动复制。

## 5. 约束与规则
- **禁止幻觉**：明确标注论文事实、用户理解、AI 分析和假说。使用"当前材料无法确认"/"论文未报告"/"尚未核验"来替代猜测。
- **Obsidian 风格**：引用时禁止使用纯文本命名，必须使用 Wiki 链接（如 `[[CLIP]]` 或 `[[CLIP|CLIP contrastive learning]]`）。**注意：Wiki 链接（内部链接）禁止在其两侧包裹反引号（Backticks），且链接目标中绝对不能包含 `.md` 后缀。**
- **Frontmatter**：论文笔记只保留 `title`、`date`、`tags`，不创建或保留 `aliases`。简称直接使用简洁文件名和 Wiki 链接表达，避免别名自动解析造成链接歧义。
- **图片与可视化优先级**：在展示架构与模块流向时，必须优先使用论文中的原始示意图。注意 LaTeX 编译的流程图多由矢量元素和文本组成，单纯使用 API 提取图片对象会漏掉它们。应先使用 `pypdfium2` 等工具将页面高分辨率（scale=3）渲染为 PNG，然后根据图题（如 "Figure 2"）进行裁剪（需包含图题文字），并保存到 `images/论文短名/` 下进行关联引用。**整理完毕后，必须彻底删除所有在 Markdown 笔记中未被引用的、非核心的无用图片（如实验对比散点图、卡通说明图等），只保留实际关联引用的核心图表，以防止知识库文件膨胀**。仅在完全无法获取时才可用简短的文本流向说明兜底。
- **水平自适应**：根据用户水平动态调整技术词汇和内容结构。
- **标签规范**：默认使用中文命名空间 `论文/...`、`方法/...`、`任务/...`、`模态/...`，专名可保留英文。标签必须表示不同分类维度，不能仅把旧标签逐字翻译后留下同义项。生成或批量整理标签时，完整执行 [标签分类与语义去重规范](references/tag-taxonomy.md)。

## 6. 完成标准
- **Compress**：一份遵循目标模板的结构化记忆文件，侧重于"为什么"和主要流程，而非样板细节。
- **Review**：一次交互式主动回忆会话，测试用户记忆，对回答进行 10 分制评分，并识别知识空白。
- **Connect**：正确的双向链接、清晰的关系分类以及 MOC 集成。
- **Compare**：使用一致维度进行的并排分析，并附带选择建议。
- **Update**：以日志形式追加到"理解更新记录"部分的变更记录，不擦除历史内容。
