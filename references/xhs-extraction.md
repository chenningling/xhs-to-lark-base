# 小红书抓取参考

当任务从小红书笔记链接开始时，使用这份参考。

## 支持的输入

接受包含下列任意一种或多种链接的自由文本：

- `https://www.xiaohongshu.com/explore/<note_id>`
- `https://www.xiaohongshu.com/discovery/item/<note_id>`
- `https://www.xiaohongshu.com/user/profile/<user_id>/<note_id>`
- `https://xhslink.com/<code>`

辅助脚本可以从混合文本中提取出有效链接。

## 抓取策略

优先使用本技能自带的辅助脚本：

```bash
python3 ./scripts/fetch_xhs_note.py --text "<用户消息>"
```

脚本会封装调用本地 `XHS-Downloader` 项目。

优先定位顺序：

1. 环境变量 `XHS_DOWNLOADER_PATH`
2. skill 同级目录下的 `XHS-Downloader/`
3. 当前工作目录下的 `XHS-Downloader/`
4. `vendor/XHS-Downloader/`

它只把这个项目作为本地依赖来源使用。除非在排障，否则不要要求操作者手动研究那个仓库。

## 标准化输出

每条笔记标准化后包含：

- `note_id`
- `note_url`
- `note_type`
- `title`
- `author_name`
- `author_id`
- `author_url`
- `content`
- `tags`
- `published_at`
- `like_count`
- `collect_count`
- `comment_count`
- `share_count`
- `image_urls`
- `video_urls`
- `live_photo_urls`
- `raw`

## 本地提取器中的字段来源

本地提取器可以提供这些小红书字段：

- title: `作品标题`
- author: `作者昵称`
- body: `作品描述`
- tags: `作品标签`
- publish time: `发布时间`
- like count: `点赞数量`
- collect count: `收藏数量`
- comment count: `评论数量`
- source link: `作品链接`
- author link: `作者链接`
- media download URLs: `下载地址`
- live photo URLs: `动图地址`

## 媒体处理规则

- `图文` 和 `图集` 笔记通常会把 `下载地址` 映射为图片 URL
- `视频` 笔记通常会把 `下载地址` 映射为视频 URL
- `动图地址` 在部分图文笔记中可能包含 live photo 风格的 URL
- 远程媒体 URL 足够用于保存元数据，但不足以直接完成 Base 附件上传

## Cookie 策略

默认不使用 cookie。

这意味着：

- 公开笔记通常仍可抓取
- 部分笔记可能无法访问
- 未认证状态下拿到的视频链接可能画质较低
- 不要声称“无 cookie 流程一定能访问所有笔记”

## 失败处理

- 如果链接提取阶段没有找到有效的小红书链接，要明确报告
- 如果某个 URL 解析失败，在可能的情况下继续处理其他 URL
- 如果提取结果缺少某个字段，直接省略，不要伪造值
