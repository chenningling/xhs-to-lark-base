# xhs-to-lark-base

把小红书笔记采集到飞书多维表格的本地 Agent Skill。

这个 Skill 适合交给 Codex、Claude Code、Cursor 等 Agent 执行：用户只需要发小红书链接，Agent 负责短链解析、笔记抓取、Base 建表或修表、记录写入，以及图片/视频附件上传。

仓库地址：[https://github.com/chenningling/xhs-to-lark-base.git](https://github.com/chenningling/xhs-to-lark-base.git)

## Agent 一句话安装

把下面这段发给 Agent，让它自动完成安装和验证：

```text
请从 GitHub 仓库 https://github.com/chenningling/xhs-to-lark-base.git 安装 xhs-to-lark-base 这个本地 Skill，按 README 完成 lark-cli、飞书授权和 Python 依赖检查，并用一条小红书链接验证解析流程可用。
```

如果你的 Agent 支持把仓库作为本地 Skill 或项目规则直接读取，也可以说：

```text
请使用仓库 https://github.com/chenningling/xhs-to-lark-base.git 中的 xhs-to-lark-base Skill。先检查依赖和飞书授权，再按 SKILL.md 执行小红书到飞书 Base 的采集流程。
```

## 使用方式

安装完成后，通常直接把小红书分享文本或链接发给 Agent 即可：

```text
http://xhslink.com/o/xxxx
```

也可以粘贴完整分享文案：

```text
这篇很有启发 ... http://xhslink.com/o/xxxx
复制后打开【小红书】查看笔记！
```

Agent 会根据 `SKILL.md` 自动完成采集、建表或修表、写入记录和附件上传，不需要用户手动指定字段。

如果要指定目标 Base，把 Base 链接一起发给 Agent：

```text
把这条小红书链接采集到这个飞书 Base：<Base 链接>
小红书链接：<小红书链接>
```

## 功能

- 支持 `xhslink.com` 短链和 `xiaohongshu.com` 标准笔记链接。
- 提取标题、类型、作者、正文、标签、发布时间、点赞、收藏、评论、内容链接、作者主页链接、图片链接、视频链接。
- 自动把 `2.3万`、`1.1亿` 这类互动数转换成整数。
- 优先写入默认 Base；没有默认 Base 时自动创建 `小红书笔记采集`。
- 写入前校验或补齐 Base 字段结构。
- 按 `笔记ID` / `内容链接` 做查重，尽量更新已有记录而不是重复创建。
- 下载图片或视频到本地后上传到 Base 附件字段；如果媒体下载失败，仍保留远程链接和元数据。

## 目录结构

```text
xhs-to-lark-base/
├── SKILL.md                         # Agent 执行入口
├── requirements.txt                 # Python 抓取依赖
├── assets/default-base.json          # 默认 Base 配置
├── scripts/fetch_xhs_note.py         # 从文本提取并抓取小红书笔记
├── scripts/xhs_parser.py             # 短链展开、页面解析、字段标准化
└── references/
    ├── xhs-extraction.md             # 小红书抓取规则
    ├── base-schema.md                # 飞书 Base 字段结构
    └── feishu-workflow.md            # lark-cli 写入流程
```

Agent 的主入口是 `SKILL.md`。README 只负责说明用途、安装和常见问题。

## 运行依赖

- Node.js 与 npm
- `lark-cli`
- Python 3.12+ 推荐
- 飞书账号，并且当前身份对目标 Base 有编辑权限

安装 Python 依赖：

```bash
pip install -r requirements.txt
```

如果你的环境限制全局安装，使用虚拟环境即可：

```bash
python3 -m venv .venv-xhs
.venv-xhs/bin/pip install -r requirements.txt
```

## 手动安装

1. 安装 `lark-cli`：

```bash
npm install -g @larksuite/cli
lark-cli --version
```

2. 初始化飞书配置：

```bash
lark-cli config init --new
```

3. 克隆仓库并安装 Python 依赖：

```bash
git clone https://github.com/chenningling/xhs-to-lark-base.git
cd xhs-to-lark-base/xhs-to-lark-base
pip install -r requirements.txt
```

4. 把 `xhs-to-lark-base/` 放到你的 Agent 可读取的位置。

常见方式：

- Codex：放入本地 skills 目录，或直接在当前工作区使用。
- Claude Code：放入项目目录，让 Agent 读取 `SKILL.md`。
- Cursor：放入工作区，并在规则或提示词中要求 Agent 使用该 Skill。

关键只有两点：

- Agent 能读到 `xhs-to-lark-base/SKILL.md`。
- 运行环境能访问 `lark-cli` 和本 Skill 的 Python 依赖。

## 验证安装

只验证链接提取：

```bash
python3 scripts/fetch_xhs_note.py --extract-only --text "http://xhslink.com/o/xxxx"
```

验证真实抓取：

```bash
python3 scripts/fetch_xhs_note.py --text "http://xhslink.com/o/xxxx"
```

如果返回里包含 `note_id`、`title`、`author_name`、`image_urls` 或 `video_urls`，说明小红书解析链路可用。

飞书写入由 Agent 按 `SKILL.md` 和 `references/feishu-workflow.md` 执行，不建议用户手动拼复杂命令。

## Base 字段

默认表名：`小红书笔记采集`

默认字段：

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

字段规则：

- `内容类型` 是单选字段，默认包含 `图文`、`图集`、`视频`。
- `标签` 是多选字段，写入前应补齐缺失选项。
- `点赞`、`收藏`、`评论` 是整数数字字段。
- `内容链接`、`作者主页链接`、`视频链接` 使用超链接样式。
- `图片链接` 使用普通文本，因为一条笔记可能包含多张图片 URL。
- `图片附件`、`视频附件` 是附件字段，只能上传本地文件，不能直接写远程 URL。

## 默认 Base

默认 Base 配置保存在：

```text
assets/default-base.json
```

Agent 选择目标 Base 的优先级：

1. 用户消息中明确给出的 Base 链接。
2. `assets/default-base.json` 中保存的默认 Base。
3. 自动创建一个新的 `小红书笔记采集` Base，并写回默认配置。

如果用户明确给出新的 Base 链接，可以把它视为替换默认 Base 的请求。

## Agent 执行要点

Agent 使用本 Skill 时应按这个顺序执行：

1. 读取 `SKILL.md`。
2. 读取 `references/xhs-extraction.md`、`references/base-schema.md`、`references/feishu-workflow.md`。
3. 用 `scripts/fetch_xhs_note.py` 抓取标准化笔记 JSON。
4. 确认目标 Base 和数据表。
5. 校验或补齐字段结构。
6. 按 `笔记ID` 或 `内容链接` 查重。
7. 创建或更新记录。
8. 下载媒体到本地临时目录。
9. 上传本地媒体到附件字段。
10. 返回 Base 链接、写入数量、字段结果和附件结果。

注意：

- 不要伪造抓取失败的字段。
- 不要把远程图片或视频 URL 直接写入附件字段。
- 如果附件上传失败，也要保留元数据和远程媒体链接。
- 如果飞书权限不足，按 `lark-cli` 返回的缺失 scope 或权限提示引导用户授权。
- 如果用户手动调整过视图顺序，除非明确要求，不要主动覆盖。

## 常见问题

### Python 依赖未安装

现象：运行抓取脚本时提示缺少依赖。

处理：

```bash
pip install -r requirements.txt
```

如果当前环境不允许全局安装，可以让 Agent 改用虚拟环境安装依赖。

### 小红书短链能识别但抓取失败

可能原因：

- 笔记不是公开可访问。
- 当前网络环境无法访问小红书页面或媒体资源。
- 小红书页面结构变化，需要更新 `scripts/xhs_parser.py`。
- 无 cookie 模式被限制，公开笔记通常可抓，但不保证全部可访问。

### 飞书写入失败

优先检查：

- `lark-cli --version` 是否可用。
- `lark-cli config init --new` 是否完成。
- 当前登录身份是否能编辑目标 Base。
- 是否缺少 `lark-cli` 报错里提示的 scope。

### 附件上传失败

优先检查：

- 媒体是否已下载成本地文件。
- 目标字段是否是 `attachment` 类型。
- 上传命令是否使用本地路径，而不是远程 URL。
- 大视频上传可能耗时较久。

## 当前限制

- 无 cookie 模式不保证能抓取所有笔记。
- 小红书页面结构变化时，解析器需要维护。
- Base 的多选字段如果已有重复选项，写入时可能出现不稳定行为，建议后续清理重复标签选项。
- `lark-cli` 的具体 scope 可能随版本变化，README 不硬编码固定 scope，以实际报错提示为准。
