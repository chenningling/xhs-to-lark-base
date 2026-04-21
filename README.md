# xhs-to-lark-base

把小红书笔记采集到飞书多维表格的 Agent Skill。

Agent Skill 不是普通脚本说明书，而是一套给 AI Agent 读取和执行的任务手册：它把触发场景、操作顺序、字段规则、失败处理和可复用脚本放在同一个目录里，让 Codex、Claude Code、Cursor 等 Agent 在收到小红书链接后，可以按 `SKILL.md` 自动完成采集和写入。

本 Skill 依赖飞书官方命令行工具 `lark-cli` 完成 Base 创建、字段维护、记录写入和附件上传。请先安装并授权 [larksuite/cli](https://github.com/larksuite/cli)，再使用本 Skill。

## 能做什么

用户提供一条或多条小红书链接后，Agent 会按本 Skill 执行：

1. 从自由文本中提取 `xhslink.com` 短链或 `xiaohongshu.com` 笔记链接。
2. 抓取并标准化标题、类型、作者、正文、标签、发布时间、互动数据、原始链接和媒体链接；正文会去除已拆分到 `标签` 字段的 `#话题#` 内容。
3. 确认目标飞书 Base；没有默认 Base 时创建 `小红书笔记采集`。
4. 校验或补齐多维表字段结构。
5. 直接创建新记录，默认支持同一条笔记重复采集。
6. 下载可访问的图片或视频，并上传到 Base 附件字段。
7. 返回 Base 链接、写入数量、字段结果和附件结果。

如果媒体下载或附件上传失败，Agent 仍会尽量写入已确认的元数据和远程媒体链接，并明确汇报部分成功的原因。

主同步入口：

```bash
python scripts/sync_xhs_to_lark_base.py --text "http://xhslink.com/o/xxxx"
```

这个脚本会一次性完成抓取、标签选项补齐、记录创建、媒体下载和附件上传。默认不查重，因此同一条笔记重复运行会产生多条采集记录。

## 适合谁使用

- 想把小红书笔记批量沉淀到飞书多维表格的用户。
- 想让 Agent 自动维护 Base 字段和附件上传流程的用户。
- 正在构建飞书 CLI 工作流、需要一个可复用示例 Skill 的开发者。

这个项目不是独立桌面应用，也不是无 Agent 的一键同步工具。核心入口是 `SKILL.md`，由 Agent 读取后执行。

## Agent 一键安装

把下面这段发给 Agent：

```text
安装这个技能 https://github.com/chenningling/xhs-to-lark-base.git ，安装后告诉我怎么配置信息。
```

安装完成后，直接把小红书笔记链接发给 Agent 即可：

```text
这篇笔记帮我采集到飞书 Base：http://xhslink.com/o/xxxx
```

也可以指定目标 Base：

```text
把这条小红书链接采集到这个飞书 Base：<Base 链接>
小红书链接：<小红书链接>
```

## 前置依赖

### 1. 安装飞书 CLI

`lark-cli` 是本 Skill 操作飞书 Base 的必要依赖。安装方式以官方项目为准：

```bash
npm install -g @larksuite/cli
lark-cli --version
```

官方项目：[https://github.com/larksuite/cli](https://github.com/larksuite/cli)

首次使用需要初始化配置和登录授权：

```bash
lark-cli config init --new
lark-cli auth login
```

如果写入 Base 时提示缺少 scope，按 `lark-cli` 的报错补充授权，不要臆造权限名。

### 2. 安装 Python 依赖

本 Skill 使用 Python 脚本解析小红书链接和页面数据：

```bash
pip install -r requirements.txt
```

如果不想使用全局 Python 环境：

```bash
python -m venv .venv-xhs
.venv-xhs/bin/pip install -r requirements.txt
```

推荐 Python 3.12+。

## 目录结构

```text
xhs-to-lark-base/
├── SKILL.md                         # Agent 执行入口
├── requirements.txt                 # Python 抓取依赖
├── assets/default-base.json          # 默认 Base 配置
├── scripts/sync_xhs_to_lark_base.py  # 主同步入口
├── scripts/fetch_xhs_note.py         # 从文本提取并抓取小红书笔记
├── scripts/xhs_parser.py             # 短链展开、页面解析、字段标准化
└── references/
    ├── xhs-extraction.md             # 小红书抓取规则
    ├── base-schema.md                # 飞书 Base 字段结构
    └── feishu-workflow.md            # lark-cli 写入流程
```

Agent 的主入口是 `SKILL.md`。`references/` 只在执行到对应步骤时读取，用来避免把过多细节塞进主说明。

## 验证安装

只验证链接提取：

```bash
python scripts/fetch_xhs_note.py --extract-only --text "http://xhslink.com/o/xxxx"
```

验证真实抓取：

```bash
python scripts/fetch_xhs_note.py --text "http://xhslink.com/o/xxxx"
```

如果返回中包含 `note_id`、`title`、`author_name`、`image_urls` 或 `video_urls`，说明小红书解析链路可用。

验证完整同步：

```bash
python scripts/sync_xhs_to_lark_base.py --text "http://xhslink.com/o/xxxx"
```

飞书写入不建议手动拼复杂命令。优先让 Agent 调用 `scripts/sync_xhs_to_lark_base.py`，或按 `SKILL.md` 和 `references/feishu-workflow.md` 处理 Base 创建、字段检查、记录写入和附件上传。

## 默认 Base

默认 Base 配置保存在：

```text
assets/default-base.json
```

Agent 选择目标 Base 的优先级：

1. 用户消息中明确给出的 Base 链接。
2. `assets/default-base.json` 中保存的默认 Base。
3. 自动创建一个新的 `小红书笔记采集` Base，并写回默认配置。

如果用户明确给出新的 Base 链接，Agent 可以把它视为替换默认 Base 的请求。默认配置可能包含真实 Base token 和 table id，发布或分享仓库前请确认是否需要清空。

## Agent 执行要点

- 先读 `SKILL.md`，再按需读取 `references/xhs-extraction.md`、`references/base-schema.md`、`references/feishu-workflow.md`。
- 使用 `scripts/fetch_xhs_note.py` 获取标准化 JSON，不要伪造抓取失败的字段。
- 写入前确认 `lark-cli` 可用、已授权、当前身份对目标 Base 有编辑权限。
- 附件字段只能上传本地文件，不能直接写远程图片或视频 URL。
- 附件上传时 `--file` 必须使用媒体目录中的相对路径，例如 `./image.jpg`。
- 如果附件上传失败，保留远程链接并汇报失败原因。
- 除非用户明确要求，不要删除或覆盖用户已有字段和视图调整。

## 常见问题

### 找不到 `lark-cli`

先安装飞书 CLI：

```bash
npm install -g @larksuite/cli
```

如果安装后仍不可用，检查 npm 全局 bin 目录是否在 `PATH` 中。

### 飞书写入失败

优先检查：

- `lark-cli --version` 是否可用。
- `lark-cli config init --new` 是否完成。
- `lark-cli auth login` 是否完成。
- 当前登录身份是否能编辑目标 Base。
- 是否缺少 `lark-cli` 报错中提示的 scope。

### Python 依赖未安装

运行抓取脚本时如果提示缺少依赖：

```bash
pip install -r requirements.txt
```

或使用虚拟环境安装。

### 小红书短链能识别但抓取失败

可能原因：

- 笔记不是公开可访问。
- 当前网络环境无法访问小红书页面或媒体资源。
- 小红书页面结构变化，需要维护 `scripts/xhs_parser.py`。
- 无 cookie 模式被限制，公开笔记通常可抓，但不保证全部可访问。

### 附件上传失败

优先检查：

- 媒体是否已下载成本地文件。
- 目标字段是否是 `attachment` 类型。
- 上传命令是否在媒体文件所在目录执行，并使用 `./filename` 形式的相对路径。
- 大视频上传可能耗时较久。

## 当前限制

- 无 cookie 模式不保证能抓取所有笔记。
- 小红书页面结构变化时，解析器需要维护。
- 主同步脚本会在补标签选项时去重；如果已有记录依赖重复选项，建议先备份 Base 再批量整理。
- `lark-cli` 的具体 scope 可能随版本变化，以实际报错和官方 CLI 文档为准。
