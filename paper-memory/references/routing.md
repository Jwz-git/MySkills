# 模式路由指南

根据用户请求分析其意图，将请求映射到正确的内容模式（`compress`、`review`、`connect`、`compare`、`update`）。图片附件处理是横切子流程，可单独执行，也可与 `compress` 或 `update` 组合。

## 1. 触发模式

### compress（压缩）
当用户希望将论文整理、总结、压缩为记忆卡片或长期 Memory 时触发。
- **触发示例**：
  - 帮我整理成复习笔记
  - 生成论文记忆卡片
  - 把这篇论文压缩一下
  - 整理成 Obsidian 笔记
  - 我以后想快速复习这篇论文
  - Summarize this paper for long-term memory

### review（复习）
当用户希望测试记忆、进行主动回忆或被考核论文内容时触发。
- **触发示例**：
  - 复习 CLIP
  - 考考我这篇论文
  - 帮我回忆这篇论文
  - 检查我还记得多少
  - Start an active recall session for DINOv2

### connect（关联）
当用户希望建立论文关系，或更新目标平台中的链接、relation、MOC/索引时触发。
- **触发示例**：
  - 这篇论文和哪些论文有关
  - 加入我的 Obsidian 知识图谱
  - 建立论文之间的关系
  - 它和 CLIP、DINOv2 有什么联系
  - 帮我补双向链接
  - Link this paper to the vision-language graph

### compare（对比）
当用户希望对多篇论文进行并列对比、评估或选择时触发。
- **触发示例**：
  - 对比 CLIP 和 DINOv2
  - 这两篇论文有什么区别
  - 比较 Text2Loc、VLM-Loc
  - 哪个方法更适合我的任务

### update（更新）
当用户希望修改已有理解、补充讨论或实验内容、纠正旧笔记时触发。
- **触发示例**：
  - 更新我对这篇论文的理解
  - 我以前理解错了
  - 把今天讨论的内容加到笔记
  - 根据实验结果修改论文笔记
  - Add update log to CLIP note

### attachment（图片附件子流程）
当用户希望提取论文图表、修复图片链接、转换图片嵌入语法或迁移论文图片时，加载 [attachment-guide.md](attachment-guide.md)。

- **触发示例**：
  - 把论文架构图裁剪出来并插入笔记
  - 将论文图片改成标准 Markdown 链接
  - 按 Custom Attachment Location 整理论文图片
  - 把已引用图片迁移到每篇笔记自己的 assets 目录
  - 检查论文笔记有没有断裂的图片链接

如果请求只涉及图片文件和链接，不改论文事实、理解或正文语义，则只执行 attachment 子流程，不追加“理解更新记录”。

---

## 2. 多模式冲突解决

当用户请求同时匹配多个模式时，按以下优先级规则处理：

1. **顺序执行**：如果用户说"先压缩论文 X，再和 Y 对比"，先执行 `compress`，再执行 `compare`。
2. **compress + connect**：如果用户说"压缩这篇新论文并和 CLIP 关联起来"，路由到 `compress`，但确保「与其他论文的关系」章节完整填写，并给出反向链接建议。
3. **compare + connect**：先执行 `compare`，再按 profile 的平台和 backlink 策略记录关系。
4. **compress + attachment**：生成新 Memory 时，在内容结构完成后按 profile 保存或上传核心图，并验证引用。
5. **update + attachment**：正文理解和图片都变化时，分别执行内容更新规则与附件规则；仅附件路径变化不属于理解更新。
6. **意图不明时询问**：只有不同模式会显著改变产物时，列出检测到的可能模式并请用户选择。
