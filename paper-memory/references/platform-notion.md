# Notion 平台适配

仅在 `memory.provider: notion` 时读取。执行读写需要当前环境中可用且已授权的 Notion 连接能力；没有时输出可复制内容和属性映射，不声称已写入。

- `memory.location` 保存稳定的 database/page 标识，不保存访问令牌。
- Memory 模板的正文标题映射为页面中的 heading/block，不能把 YAML frontmatter 当作正文写入。
- `metadata.fields` 映射到 database properties；先读取现有 property 名称和类型，不擅自新建或改变 schema。
- `links.style: notion` 时使用 page mention 或 relation property。relation property 不存在时先报告需要的 schema 变化，不自动创建。
- `backlinks: maintain` 只在 relation 天然双向或双方页面可安全更新时执行；否则降为精确建议并说明原因。
- `attachments.mode: platform` 时使用 Notion 的文件/图片 block；验证上传或外链在目标页面可访问。不得把本地路径字符串当作已上传附件。
- `links.index` 可以指向索引页面或 database view；不假定存在 MOC 目录。
