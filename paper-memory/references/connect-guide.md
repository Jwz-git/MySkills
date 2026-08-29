# 论文关联指南

执行 `connect` 模式时使用。本文只定义平台无关的关系语义和决策；链接语法、反向更新与索引位置由 profile 及平台指南决定。

## 1. 关系类型

| 关系键 | 含义 | 成立条件 |
| --- | --- | --- |
| `builds-on` | 直接建立在前作基础上 | 论文明确采用前作的核心范式或方法 |
| `improves` | 针对前作弱点改进 | 能指出被改进的具体限制 |
| `extends-to` | 扩展到新任务、领域或模态 | 核心思想延续但适用范围变化 |
| `uses-as-component` | 使用前作模型、损失、数据或工具 | 能指明实际使用的组件 |
| `same-question` | 研究问题相同 | 问题一致但方法可以不同 |
| `similar-idea` | 思想相似 | 无直接继承证据，不得写成 builds-on |
| `complements` | 能力互补 | 能说明组合后分别弥补什么 |
| `contradicts` | 结论或证据冲突 | 明确冲突命题及实验/理论条件 |
| `evaluates` | 专门评估或复现另一工作 | 评估对象和证据清楚 |
| `provides-resource` | 提供数据集、基准或工具 | 资源被另一工作实际使用或适用 |

`replaces` 不作为常规关系：除非范围、条件和证据足以支持“替代”，否则使用 `improves` 并写明适用边界。

## 2. 建立关系的证据

- 优先依据论文正文、引用上下文、官方代码或可核验的实验设置。
- “都使用 Transformer”“同年发表”或关键词重叠不足以建立关系。
- 相关性不等于继承；没有直接证据时使用 `similar-idea` 或保留为待验证。
- 每条关系写一条解释，使读者知道关系对综述、实验设计或方法选择有什么价值。

## 3. 平台路由

根据 `memory.provider` 和 `links.style` 只读取一个相关指南：

- 本地 Markdown：[platform-markdown.md](platform-markdown.md)
- Obsidian/Wiki Link：[platform-obsidian.md](platform-obsidian.md)
- Notion：[platform-notion.md](platform-notion.md)
- `links.style: none`：只在当前输出中报告关系，不创建链接或反向内容。

`links.backlinks` 的统一语义：

- `maintain`：在已有权限和目标存在时同步更新双方。
- `suggest`：只提供精确更新建议，不写入另一端。
- `none`：不创建反向内容。

## 4. 索引原则

只有 `links.index` 非空时才维护索引。索引用于导航，不复制论文摘要；按问题、方法演进或主题组织，并保留研究挑战和空白。不要擅自创建 `MOCs/` 或其他固定目录。
