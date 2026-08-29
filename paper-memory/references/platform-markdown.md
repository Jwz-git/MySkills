# 本地 Markdown 平台适配

仅在 `memory.provider: markdown` 时读取。

- 使用 profile 指定的 Memory 根目录和命名规则。
- `links.style: markdown` 时使用相对 Markdown 链接；计算路径时以当前文件目录为基准，并对空格等字符正确编码。
- Markdown 本身没有自动反向链接。`backlinks: maintain` 表示显式编辑另一文件；目标不存在时报告而不创建空壳笔记。
- 元数据可以是 YAML frontmatter，也可以不存在；遵循 `metadata.fields` 并在 `preserve_unknown_fields: true` 时保留未知字段。
- 附件只在 `attachments.mode: local` 时落盘，路径按 `root_pattern` 展开。
- 写入后验证相对链接和本地附件目标存在。
