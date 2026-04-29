# xhs-to-lark-base

把小红书 / RedNote 笔记链接采集到飞书多维表格（Base）的 Agent Skill。


## 项目背景

小红书内容常常分散在聊天记录、运营选题、竞品观察和素材收藏里。人工整理时，需要反复打开链接、复制标题和正文、拆标签、记录互动数据、下载图片或视频，再把这些信息填进飞书多维表格。这个过程机械、耗时，也很容易漏字段。

`xhs-to-lark-base` 的目标是把这条链路封装成一个可以被 Agent 调用的技能：用户只需要把一条或多条小红书链接发给 Agent，Agent 就能按技能说明抓取笔记信息，并写入指定或自动创建的飞书 Base。

## 解决痛点

- 降低人工录入成本：从自由文本中提取小红书链接，自动抓取标题、作者、正文、标签、发布时间和互动数据。
- 统一内容沉淀格式：使用固定 Base 字段结构，让运营、研究、素材归档结果可复盘、可筛选、可协作。
- 保留媒体素材线索：保存图片 / 视频远程链接，并在可行时下载本地媒体后上传为飞书附件。
- 减少重复配置：支持本地默认 Base 配置，后续采集可以复用同一个目标表。
- 对 Agent 友好：`SKILL.md`、参考文档和脚本都放在项目内，Agent 不需要依赖额外的 Skill 目录。

## 功能框架

```text
xhs-to-lark-base
├── SKILL.md                         # Agent 技能入口与行为规范
├── scripts/
│   ├── fetch_xhs_note.py             # 抓取并标准化小红书笔记数据
│   ├── sync_xhs_to_lark_base.py      # 抓取、写入 Base、下载并上传附件
│   └── xhs_parser.py                 # 小红书链接解析与页面数据提取
├── references/
│   ├── xhs-extraction.md             # 支持的链接格式、字段来源、失败处理
│   ├── base-schema.md                # 飞书 Base 字段结构
│   └── feishu-workflow.md            # lark-cli 操作流程
├── assets/
│   └── default-base.example.json     # 默认 Base 配置模板
├── agents/
│   └── openai.yaml                   # Agent 展示信息示例
├── requirements.txt                  # Python 运行依赖
└── LICENSE
```

核心流程：

1. 用户发送包含小红书链接的自然语言请求。
2. Agent 根据 `SKILL.md` 调用脚本提取链接并抓取笔记信息。
3. Skill 检查目标飞书 Base 和字段结构。
4. Skill 写入笔记记录，默认允许重复采集，便于保留多次采集快照。
5. Skill 尝试下载媒体并上传到附件字段。
6. Agent 返回 Base 链接、成功数量、失败字段和附件上传结果。

## 安装前准备

安装本 Skill 前，请先安装并配置飞书 CLI：

[https://github.com/larksuite/cli.git](https://github.com/larksuite/cli.git)

安装完成后，确认本地可以运行：

```bash
lark-cli --help
```

如果还没有初始化飞书 CLI，可以按需执行：

```bash
lark-cli config init --new
lark-cli auth login --scope "base:app:write"
```

实际 scope 以 `lark-cli` 报错提示和飞书开放平台权限要求为准。

## 安装方式

### 方式一：让 Agent 自主安装

如果你的 Agent 支持从 GitHub 安装 Skill，可以直接打开本项目并发送类似下面的一句话：

```text
请先确认本机已安装 lark-cli，然后从 https://github.com/chenningling/xhs-to-lark-base.git 安装 xhs-to-lark-base 这个技能到你的技能目录中，并读取 SKILL.md 完成配置。
```

安装完成后，可以继续对 Agent 说：

```text
把这条小红书链接采集到飞书多维表格：https://www.xiaohongshu.com/explore/xxxx
```

### 方式二：手动 clone 到 Agent 技能目录

先克隆仓库：

```bash
git clone https://github.com/chenningling/xhs-to-lark-base.git
```

然后把整个 `xhs-to-lark-base` 目录放到你的 Agent 指定技能安装目录中。不同 Agent 的目录约定可能不同，请以对应 Agent 文档为准。常见形式如下：

```text
~/.codex/skills/xhs-to-lark-base
~/.agents/skills/xhs-to-lark-base
<your-agent-home>/skills/xhs-to-lark-base
```

放置完成后，让 Agent 重新加载技能，或重启 Agent 会话。

## Python 依赖

进入项目目录后安装脚本依赖：

```bash
python -m pip install -r requirements.txt
```

当前依赖包括：

- `httpx`：请求小红书页面和媒体资源
- `PyYAML`：读取 Agent 展示配置

## 配置默认飞书 Base

如果你希望 Skill 每次都写入同一个 Base，可以复制配置模板：

```bash
cp assets/default-base.example.json assets/default-base.json
```

然后填入真实配置：

```json
{
  "base_url": "https://your-domain.feishu.cn/base/xxx",
  "base_token": "app_xxx",
  "table_id": "tbl_xxx",
  "table_name": "小红书笔记采集",
  "updated_at": "2026-04-29 12:00:00"
}
```

如果没有默认 Base，Agent 也可以根据 `SKILL.md` 中的规则创建一个名为 `小红书笔记采集` 的新 Base，并保存为后续默认配置。

## 使用示例

让 Agent 采集一条链接：

```text
请把这个小红书链接采集到飞书 Base：https://www.xiaohongshu.com/explore/xxxx
```

一次采集多条链接：

```text
请归档这些小红书笔记：
https://www.xiaohongshu.com/explore/xxxx
https://xhslink.com/xxxx
```

仅调试抓取结果：

```bash
python scripts/fetch_xhs_note.py --text "https://www.xiaohongshu.com/explore/xxxx"
```

直接运行同步脚本：

```bash
python scripts/sync_xhs_to_lark_base.py --text "https://www.xiaohongshu.com/explore/xxxx"
```

## Base 字段

默认采集表名为 `小红书笔记采集`，主要字段包括：

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

完整字段类型和修复规则见 [`references/base-schema.md`](references/base-schema.md)。

## 注意事项

- 请在安装 Skill 前先安装并配置 `lark-cli`，否则 Agent 无法创建 Base、写入记录或上传附件。
- 默认不使用小红书 cookie，因此公开笔记通常可抓取，但不保证所有笔记都能访问。
- 远程媒体 URL 会写入链接字段；附件上传需要先下载到本地文件，上传失败时元数据仍会优先保留。
- 默认允许重复采集同一条笔记，每次执行会创建新记录。
- 不要把包含真实 token 的 `assets/default-base.json` 提交到公开仓库。

## 开源许可

本项目使用仓库内 [`LICENSE`](LICENSE) 文件声明的许可证。
