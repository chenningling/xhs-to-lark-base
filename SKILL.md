---
name: xhs-to-lark-base
description: 将 Xiaohongshu（小红书 / RedNote）笔记链接采集到飞书 Base（多维表格）中。当用户提供一个或多个小红书链接，并希望把笔记标题、内容类型、作者、正文、标签、发布时间、互动数据、原始链接以及图片/视频素材保存到飞书多维表格时使用；当用户希望创建、校验、修复或替换这条采集流程默认使用的 Base 链接时，也使用此技能。
---

# 小红书同步到飞书多维表格

通过可重复执行的流程把小红书笔记采集到飞书 Base：从用户文本中提取笔记链接，抓取标准化后的笔记数据，确保目标 Base 存在且字段结构符合要求，自动创建或修复字段与默认视图顺序，写入记录，并在同一次 Skill 执行中完成媒体下载与附件上传，最后带上 Base 链接汇报成功和失败结果。

保持本技能自包含。运行时不要依赖其他 Skill 目录，优先复用本技能附带的参考文档和脚本，并直接使用 `lark-cli` 处理飞书操作。

## 快速开始

1. 先阅读 [`references/xhs-extraction.md`](references/xhs-extraction.md)，了解支持的链接类型、字段标准化方式和媒体处理限制。
2. 再阅读 [`references/base-schema.md`](references/base-schema.md)，确认所需的 Base 表结构和默认字段顺序。
3. 任何 `lark-cli` 写操作前，都先阅读 [`references/feishu-workflow.md`](references/feishu-workflow.md)。
4. 优先使用 [`scripts/sync_xhs_to_lark_base.py`](scripts/sync_xhs_to_lark_base.py) 完成抓取、写入、媒体下载和附件上传；仅在排障时单独使用 [`scripts/fetch_xhs_note.py`](scripts/fetch_xhs_note.py) 查看标准化后的笔记 JSON。
5. 按以下顺序确定目标 Base：
   - 当前用户消息中显式提供的 Base 链接
   - 保存于 [`assets/default-base.json`](assets/default-base.json) 的默认配置
   - 如果前两者都没有，则新建一个 Base
6. 写入记录前先校验或修复 Base 的字段结构。
7. 在同一次 Skill 执行中，自动完成“下载媒体 -> 创建记录 -> 上传附件”。
8. 最终返回 Base 链接，并按字段给出简明的成功/失败摘要。

## 必要行为

- 接受混合文本输入，并从中提取小红书链接。
- 支持 `xhslink.com` 短链和常规 `xiaohongshu.com` 笔记链接。
- 默认在不提供 cookie 的情况下工作。
- 即使无法上传媒体附件，也优先完成元数据采集。
- 如果用户提供新的 Base 链接，将其视为“替换默认目标 Base”的明确请求。
- 如果新的 Base 缺少字段，先补齐或修复字段结构，再继续使用。
- 除非用户明确要求，否则不要删除用户已有字段。
- 先创建记录，拿到 `record_id` 后再处理附件上传。
- 清楚汇报部分成功的情况，尤其是元数据写入成功但附件上传失败时。
- 默认新建的 Base 文档名使用 `小红书笔记采集`。
- 默认视图字段顺序按 [`references/base-schema.md`](references/base-schema.md) 中的阅读顺序设置；如果用户后续自己调整，不再主动干预。
- 支持重复采集同一条笔记：默认每次执行都新建记录，不按 `笔记ID` 或 `内容链接` 查重更新。
- `正文` 字段只保存笔记正文内容，不重复写入已经拆分到 `标签` 字段的 `#话题#` 内容。

## 工作流

### 1. 提取并抓取小红书数据

优先运行主同步脚本：

```bash
python ./scripts/sync_xhs_to_lark_base.py --text "<用户消息>"
```

主同步脚本会：

- 从自由文本中提取支持的小红书链接
- 抓取标准化后的笔记字段
- 读取默认 Base 配置并校验目标字段
- 批量补齐 `标签` 多选字段缺失选项，避免每条记录重复更新字段结构
- 默认不查重，每条笔记创建一条新记录
- 下载媒体到本地临时目录，并使用相对路径上传附件
- 对媒体下载和附件上传执行有限重试

如果只需要排查抓取结果，可运行辅助抓取脚本：

```bash
python ./scripts/fetch_xhs_note.py --text "<用户消息>"
```

抓取脚本会：

- 从自由文本中提取支持的小红书链接
- 使用本技能内置解析器展开 `xhslink.com` 短链并抓取页面状态
- 返回标准化后的笔记字段
- 自动把 `2.3万`、`1.1亿` 这类互动数文本转换成整数
- 在 JSON 中保留原始数据，便于排障

如果辅助脚本缺少本仓库自己的 Python 依赖，要明确说明当前元数据抓取被环境阻塞，需先安装 `requirements.txt` 后才能继续。不要虚构任何笔记数据。

### 2. 确定目标 Base

使用以下优先级：

1. 当前请求中显式提供的 Base 链接
2. [`assets/default-base.json`](assets/default-base.json) 中保存的默认配置
3. 新建一个 Base，并将其保存为后续默认值

当用户提供新的 Base 链接时，在校验成功后更新 [`assets/default-base.json`](assets/default-base.json)。

如果当前还没有 Base：

- 新建一个名为 `小红书笔记采集` 的 Base
- 创建名为 `小红书笔记采集` 的数据表
- 创建 [`references/base-schema.md`](references/base-schema.md) 中列出的字段
- 将得到的 Base URL、token 和 table ID 保存到 [`assets/default-base.json`](assets/default-base.json)

### 3. 校验或修复 Base 结构

写入记录前：

1. 读取当前数据表和字段列表。
2. 确认采集表存在。
3. 确认必须字段存在且类型兼容。
4. 补齐缺失字段。
5. 如果已有字段类型不兼容：
   - 优先在确有必要时，以规范字段名加安全后缀的方式创建兼容字段
   - 或者在安全且支持的前提下更新原字段
   - 不要静默破坏用户已有数据

统一以 [`references/base-schema.md`](references/base-schema.md) 中定义的规范结构为准。

推荐策略：

- 文本类数据：使用 `text` 或 `url`
- 计数类数据：使用 `number`
- 发布时间：使用 `datetime`
- 内容类型：使用 `select` 单选，默认选项至少包含 `图文 / 图集 / 视频`
- 标签：使用 `select` 多选，并在写入前动态补齐选项
- `内容链接`、`作者主页链接`、`视频链接`：使用带超链接显示样式的 `text`
- `图片链接`：使用普通 `text`，因为可能一次写入多条 URL
- 已上传媒体：使用 `attachment`

### 4. 写入 Base 记录

每条小红书笔记写入一条记录。使用标准化后的 JSON，并按 [`references/base-schema.md`](references/base-schema.md) 中定义的字段映射进行写入。

这些字段只要有值，就优先写入：

- `标题`
- `内容类型`
- `作者`
- `正文`
- `标签`
- `发布日期`
- `点赞`
- `收藏`
- `评论`
- `内容链接`
- `作者主页链接`
- `图片链接`
- `图片附件`
- `视频链接`
- `视频附件`
- `采集时间`

写入前还要做两步标准化：

- 把 `2.3万`、`1.1亿` 这类互动数文本转换成整数
- 把标签同步为多选字段的选项，再按多选值写入

重复采集策略：

- 默认不查重，不搜索已有记录。
- 每次采集同一条笔记都创建一条新记录，便于保留多次采集快照。
- 只有用户明确要求“更新已有记录”或“去重采集”时，才额外按 `笔记ID` 或 `内容链接` 查找并更新。

### 5. 上传媒体附件

只有拿到本地文件时，附件上传才可行。Base 的附件字段不能直接写入小红书远程 URL；附件上传必须使用本地文件。

使用以下决策规则：

- 如果只有远程 URL，仍然要把它们存入 `图片链接` / `视频链接`，并将附件上传标记为已跳过
- 如果本地文件可用，在记录创建后把它们上传到 `图片附件` 和 `视频附件`

推荐顺序：

1. 抓取元数据和远程媒体 URL
2. 下载媒体到本地临时目录
3. 创建 Base 记录
4. 在媒体文件所在目录中使用 `./filename` 形式的相对路径调用 `lark-cli base +record-upload-attachment`

这是一次 Skill 执行内的自动编排，不要把这四步拆成要求用户手动执行的多个步骤。

除非上传命令确实成功，否则不要声称附件上传成功。

### 6. 返回结构化结果

每次执行结束时都要返回：

- Base 链接
- 识别到的小红书链接数量
- 成功写入的笔记数量
- 成功写入的字段
- 被跳过或失败的字段
- 附件上传结果

如果是部分成功，要明确说明。示例：

- 元数据写入成功
- `视频附件` 因只有远程 URL 而跳过
- `图片附件` 因本地上传文件缺失而失败

## 常用命令

以下仅为示例。执行写操作前，先阅读本技能附带的参考文档。

创建 Base：

```bash
lark-cli base +base-create --name "小红书笔记采集" --time-zone Asia/Shanghai
```

创建字段：

```bash
lark-cli base +field-create \
  --base-token app_xxx \
  --table-id tbl_xxx \
  --json '{"name":"标题","type":"text"}'
```

创建记录：

```bash
lark-cli base +record-upsert \
  --base-token app_xxx \
  --table-id tbl_xxx \
  --json '{"标题":"示例笔记","内容类型":"图文","作者":"示例作者","内容链接":"https://www.xiaohongshu.com/explore/xxx"}'
```

上传附件：

```bash
cd /path/to/downloaded-media
lark-cli base +record-upload-attachment \
  --base-token app_xxx \
  --table-id tbl_xxx \
  --record-id rec_xxx \
  --field-id "图片附件" \
  --file "./image.jpg"
```

## 配置文件

使用 [`assets/default-base.json`](assets/default-base.json) 作为本技能本地保存的默认目标 Base 配置。

预期结构：

```json
{
  "base_url": "",
  "base_token": "",
  "table_id": "",
  "table_name": "小红书笔记采集",
  "updated_at": ""
}
```

规则：

- 如果文件为空或缺少关键标识，就视为尚未配置
- 当用户明确更换默认 Base 时，更新此文件
- 路径和 token 必须真实，不要在真实配置文件中伪造占位值

## 安全与失败处理

- 只有当用户明确要求采集或重新配置 Base 时，才将 `lark-cli base` 写操作视为已获授权
- 如果飞书认证或 scope 缺失，暂停执行，并明确告诉用户需要完成哪个命令
- 如果小红书抓取结果不完整，只写入已确认字段
- 如果某条笔记无法解析，不要创建伪造记录，直接报告失败 URL
- 如果 Base 链接最终解析到的不是 bitable 资源，停止执行并要求用户提供有效的飞书 Base 链接

## 附带资源

- [`scripts/sync_xhs_to_lark_base.py`](scripts/sync_xhs_to_lark_base.py)：主同步入口，负责编排抓取、记录创建、标签选项维护、媒体下载和附件上传
- [`scripts/fetch_xhs_note.py`](scripts/fetch_xhs_note.py)：提取小红书链接并输出标准化后的笔记 JSON，主要用于排障
- [`references/xhs-extraction.md`](references/xhs-extraction.md)：支持的链接类型、字段映射和媒体处理限制
- [`references/base-schema.md`](references/base-schema.md)：规范的 Base 结构和字段映射
- [`references/feishu-workflow.md`](references/feishu-workflow.md)：`lark-cli` 认证、建表、修表、写记录和上传附件的操作流程
- [`assets/default-base.json`](assets/default-base.json)：保存默认 Base 配置
