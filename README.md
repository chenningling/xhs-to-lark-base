# xhs-to-lark-base

把小红书笔记一键采集到飞书多维表格的本地 Skill。

它面向通用 Agent 环境设计，可用于 Codex、Claude Code、Cursor 等支持本地技能、提示词目录或工作流目录的工具。Skill 会完成短链解析、笔记字段标准化、飞书 Base 自动建表或修表、记录写入，以及图片/视频附件上传。

## 功能实现

- 支持小红书短链和标准笔记链接
- 自动提取标题、内容类型、作者、正文、标签、发布时间、互动数据、内容链接、作者主页链接、图片链接、视频链接
- 自动把 `2.3万`、`1.1亿` 这类互动数字转换为整数
- 自动创建或修复飞书 Base 结构
- 自动把 `内容类型` 写成单选字段，把 `标签` 写成多选字段
- 自动设置默认视图字段顺序
- 自动下载媒体并上传到 `图片附件` / `视频附件`
- 自动保存默认 Base 配置，便于后续重复使用

## 架构说明

核心由 4 部分组成：

1. `SKILL.md`
负责定义技能触发条件、执行流程和行为约束。

2. `scripts/fetch_xhs_note.py`
负责提取小红书链接、调用本地 `XHS-Downloader`、输出标准化 JSON。

3. `references/base-schema.md`
负责定义飞书多维表格的字段规范、默认顺序和数据映射规则。

4. `references/feishu-workflow.md`
负责定义 `lark-cli` 的认证、建表、修表、写记录和附件上传工作流。

完整执行链路：

1. Agent 读取 `SKILL.md`
2. `fetch_xhs_note.py` 解析小红书链接并输出标准化数据
3. Agent 根据 `base-schema.md` 检查或修复目标 Base
4. Agent 用 `lark-cli` 创建或更新记录
5. Agent 下载媒体并上传到附件字段
6. Agent 返回采集结果和飞书 Base 链接

## 运行依赖

需要以下运行条件：

- `lark-cli`
- 一个可用的飞书账号授权
- 本地 `XHS-Downloader` 项目及其 Python 依赖
- Python 3.12+ 推荐

`XHS-Downloader` 的定位优先级：

1. 环境变量 `XHS_DOWNLOADER_PATH`
2. Skill 同级目录下的 `XHS-Downloader/`
3. 当前工作目录下的 `XHS-Downloader/`
4. `vendor/XHS-Downloader/`

## 安装方式

### 方式一：让 Agent 一句话安装

你可以直接对 Agent 说：

```text
请从 GitHub 仓库 https://github.com/chenningling/xhs-to-lark-base.git 安装 xhs-to-lark-base 这个本地 Skill，检查 README 和 SKILL.md，确保 XHS_DOWNLOADER_PATH 指向可用的 XHS-Downloader 目录，并验证 lark-cli 授权是否可用。
```

如果你使用的是支持仓库内本地 Skill 的 Agent，也可以直接说：

```text
请从仓库 https://github.com/chenningling/xhs-to-lark-base.git 拉取并使用其中的 xhs-to-lark-base Skill，按 README 完成依赖检查后执行一次验证。
```

### 方式二：用户手动安装

推荐步骤：

1. 从 GitHub 克隆仓库：

```bash
git clone https://github.com/chenningling/xhs-to-lark-base.git
```

2. 把仓库里的 `xhs-to-lark-base/` 目录复制到你的技能目录或 Agent 可读取的本地工作流目录
3. 准备一份本地 `XHS-Downloader`
4. 设置环境变量 `XHS_DOWNLOADER_PATH`
5. 确保 `lark-cli` 已初始化并已授权
6. 让 Agent 重新扫描或加载本地 Skill

示例：

```bash
git clone https://github.com/chenningling/xhs-to-lark-base.git
export XHS_DOWNLOADER_PATH=/path/to/XHS-Downloader
cp -R xhs-to-lark-base/xhs-to-lark-base /path/to/your/skills/
```

如果你的 Agent 直接支持从 GitHub 仓库读取本地规则或 Skill，也可以直接把仓库作为安装源，不必手动复制目录。

### 适配不同 Agent 的安装思路

- Codex：从仓库拉取后，把 `xhs-to-lark-base/` 放进本地 Skill 目录或当前工作区，让 Agent 能读取 `SKILL.md`
- Claude Code：从仓库拉取后，把 `xhs-to-lark-base/` 放进项目仓库，要求 Agent 直接读取其中的 `SKILL.md` 和 `README.md`
- Cursor：从仓库拉取后，把 `xhs-to-lark-base/` 放进当前工作区，通过仓库提示词或规则文件引导 Agent 使用该 Skill

关键点只有两个：

- Agent 能读取 `SKILL.md`
- 运行环境能访问 `lark-cli`、Python 和 `XHS-Downloader`

## 使用方式

典型请求示例：

```text
把这个小红书链接保存到默认飞书多维表格：http://xhslink.com/xxxx
```

```text
把下面两条小红书笔记归档到这个飞书 Base：https://your.feishu.cn/base/xxxx
```

```text
把这个小红书链接存档，并把默认 Base 切换成这个新链接：https://your.feishu.cn/base/xxxx
```

```text
把这条小红书笔记同步到飞书多维表格，并把图片和视频附件一起上传。
```

## 字段设计

当前默认字段包括：

- 标题
- 内容类型
- 作者
- 正文
- 标签
- 发布日期
- 点赞
- 收藏
- 评论
- 内容链接
- 作者主页链接
- 图片链接
- 图片附件
- 视频链接
- 视频附件
- 采集时间

字段规则：

- `内容类型` 是单选字段
- `标签` 是多选字段
- `点赞`、`收藏`、`评论` 是整数型数字字段
- `内容链接`、`作者主页链接`、`视频链接` 使用超链接显示样式
- `图片链接` 保持普通文本，因为一次可能采集到多张图片 URL
- `图片附件`、`视频附件` 必须是附件字段

## 默认行为

- 优先使用用户消息里显式给出的飞书 Base 链接
- 如果用户没有提供 Base，则读取 `assets/default-base.json`
- 如果默认 Base 也不存在，则自动创建名为 `小红书笔记采集` 的 Base 和同名数据表
- 如果目标表结构不符合规范，则先修表再写记录
- 如果媒体文件能下载到本地，则在同一次执行里完成附件上传
- 如果只有远程链接而没有本地文件，则仍然写入元数据和远程链接

## 注意事项

- 小红书接口和页面结构可能变化，解析逻辑需要持续适配
- 无 cookie 模式不保证所有笔记都可访问
- 飞书 `datetime` 字段格式只稳定支持到分钟，不建议写秒
- 大视频附件会走分片上传，耗时会更久
- 飞书 `attachment` 字段在某些情况下存在更新限制，迁移旧表时可能需要“新建字段并隐藏旧字段”或“删除重建后回填数据”
- 如果用户后续手动调整视图顺序，Skill 默认不再覆盖
- 图片链接字段之所以不用超链接样式，是因为它可能一次写入多条 URL；在飞书表格里保留为多行文本更稳定

## 故障排查

### 1. 找不到 XHS-Downloader

优先检查：

- `XHS_DOWNLOADER_PATH` 是否设置正确
- `XHS-Downloader` 是否真的存在
- 该目录下是否包含 `source/`
- 依赖是否已经按该项目要求安装完成

### 2. 飞书写入失败

优先检查：

- `lark-cli config init --new` 是否完成
- `lark-cli auth login` 是否完成
- 当前账号是否对目标 Base 有权限
- 当前账号是否具有上传附件所需权限

### 3. 附件上传失败

优先检查：

- 文件是否真的下载到了本地
- 上传时使用的是否是本地文件路径
- 文件体积是否过大，是否需要分片上传
- 目标字段是否真的是 `attachment`

### 4. 短链能识别但抓不到笔记

优先检查：

- 小红书当前是否对该内容有限流或访问限制
- `XHS-Downloader` 是否已经跟上最新页面结构
- 当前网络环境是否能正常访问小红书资源

## 其他重要内容

- 这是一个以 Agent 为执行主体的 Skill，不是面向终端用户独立交互的 CLI 工具
- 推荐把它和一份可用的 `XHS-Downloader` 一起分发
- 如果你要面向团队共享，建议附上一个飞书 Base 模板截图和 1 到 2 条真实示例请求
- 如果你的 Agent 不支持原生 Skill 机制，也可以把 `SKILL.md` 内容作为项目规则文件使用，再让 Agent 按 `README.md` 中的依赖和流程执行
