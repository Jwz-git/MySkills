# 模式路由指南

根据用户请求分析其意图，将请求映射到正确的操作模式（`compress`、`review`、`connect`、`compare`、`update`）。

## 1. 触发模式

### compress（压缩）
当用户希望将论文整理、总结、压缩为记忆卡片或 Obsidian 笔记时触发。
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
当用户希望建立论文关系、构建 Obsidian 双向链接或更新 MOC（Map of Content）时触发。
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

---

## 2. 多模式冲突解决

当用户请求同时匹配多个模式时，按以下优先级规则处理：

1. **顺序执行**：如果用户说"先压缩论文 X，再和 Y 对比"，先执行 `compress`，再执行 `compare`。
2. **compress + connect**：如果用户说"压缩这篇新论文并和 CLIP 关联起来"，路由到 `compress`，但确保「与其他论文的关系」章节完整填写，并给出反向链接建议。
3. **compare + connect**：如果用户说"对比 CLIP 和 DINOv2 并在我的 Obsidian 图谱里连接起来"，先执行 `compare`，再输出双向链接建议。
4. **意图不明时询问**：如果意图完全无法判断，列出检测到的可能模式并请用户选择。
