# 飞书流程参考

使用这份参考来代替对外部 Skill 的依赖。这里收录了本技能所需的最小 `lark-cli` 工作流。

## 1. 认证与权限检查

如果 `lark-cli` 还未初始化：

```bash
lark-cli config init --new
```

如果缺少用户身份授权：

```bash
lark-cli auth login --scope "base:app:write"
```

根据实际报错补充所需 scope，不要凭空猜测 scope 名称。

## 2. 解析 Base 链接

### 直接 Base 链接

如果用户给出 `/base/` 风格的链接，从 URL 中提取 Base token，并用下面的命令检查：

```bash
lark-cli base +base-get --base-token app_xxx
```

### Wiki 链接

如果用户给出 `/wiki/` 链接，先解析：

```bash
lark-cli wiki spaces get_node --params '{"token":"wiki_xxx"}'
```

规则：

- `obj_type` 必须是 `bitable`
- 使用 `obj_token` 作为真实 Base token

如果解析结果不是 `bitable`，停止并要求用户提供真实的 Base 链接。

## 3. 创建新的 Base

```bash
lark-cli base +base-create --name "小红书笔记采集" --time-zone Asia/Shanghai
```

创建后：

- 如果返回中有 `base.url`，记录下来
- 记录 Base token
- 把它们保存到 `assets/default-base.json`

## 4. 检查数据表、字段与视图

列出数据表：

```bash
lark-cli base +table-list --base-token app_xxx
```

查看字段：

```bash
lark-cli base +field-list --base-token app_xxx --table-id tbl_xxx
```

查看视图：

```bash
lark-cli base +view-list --base-token app_xxx --table-id tbl_xxx
```

## 5. 创建或修复归档表

```bash
lark-cli base +table-create --base-token app_xxx --name "小红书笔记采集"
```

然后按照 [`base-schema.md`](base-schema.md) 中的定义逐个创建或修复字段。

关键规则：

- `标签` 字段必须是 `select` 且 `multiple=true`
- `点赞 / 收藏 / 评论` 必须是整数样式的 `number`
- `图片附件 / 视频附件` 必须是 `attachment`
- 如果用户明确要求，可删除 `单选`、`采集结果`、`失败原因`
- 默认视图顺序要按 [`base-schema.md`](base-schema.md) 设置

## 6. 按内容链接搜索已有记录

优先按 `内容链接` 搜索，避免重复记录；如果旧表历史上用过 `笔记ID`，可同时兼容。

```bash
lark-cli base +record-search \
  --base-token app_xxx \
  --table-id tbl_xxx \
  --json '{"keyword":"https://www.xiaohongshu.com/explore/abc","search_fields":["内容链接"],"select_fields":["内容链接"]}'
```

如果存在匹配记录，使用它的 `record_id`，并通过 `+record-upsert --record-id` 更新。

## 7. 创建或更新记录

创建：

```bash
lark-cli base +record-upsert \
  --base-token app_xxx \
  --table-id tbl_xxx \
  --json '{"标题":"示例","内容类型":"图文","内容链接":"https://www.xiaohongshu.com/explore/abc"}'
```

更新：

```bash
lark-cli base +record-upsert \
  --base-token app_xxx \
  --table-id tbl_xxx \
  --record-id rec_xxx \
  --json '{"采集时间":"2026-04-20 20:00"}'
```

写记录前的字段准备规则：

- `标签` 写入前，先把当前笔记标签补齐为字段选项，再写入多选值
- `点赞 / 收藏 / 评论` 必须转换成整数；若原始文本为 `2.3万`、`1.1亿` 等，先换算成整数
- 时间格式使用飞书允许的 `yyyy-MM-dd HH:mm`

## 8. 自动上传附件

对用户而言，这一步必须被 Skill 自动编排完成。虽然底层仍需要多次 API 调用，但用户不应被要求手动分步执行。

标准编排顺序：

1. 抓取元数据与远程媒体链接
2. 下载图片或视频到本地临时目录
3. 创建或更新 Base 记录
4. 调用 `+record-upload-attachment` 上传图片和视频附件
5. 返回完整结果

只有在记录已存在且拿到本地文件后，才上传附件：

```bash
lark-cli base +record-upload-attachment \
  --base-token app_xxx \
  --table-id tbl_xxx \
  --record-id rec_xxx \
  --field-id "图片附件" \
  --file "/absolute/path/to/file.jpg"
```

常见坑点：

- 目标字段必须是 `attachment`
- 远程 URL 不能直接写成附件值
- 如果上传失败，保留记录中的远程 URL，并单独汇报附件上传失败
- `lark-base` 已足够完成记录创建与附件上传的编排；只有当需要查找未封装的飞书原生接口时，才转到 `lark-openapi-explorer`

## 9. 更新保存的默认配置

当用户更换默认 Base 时，更新：

`/Users/chennl/Desktop/Skills/feishu/Redbook_Sync/xhs-to-lark-base/assets/default-base.json`

推荐结构：

```json
{
  "base_url": "https://example.feishu.cn/base/...",
  "base_token": "app_xxx",
  "table_id": "tbl_xxx",
  "table_name": "小红书笔记采集",
  "updated_at": "2026-04-20 20:00:00"
}
```
