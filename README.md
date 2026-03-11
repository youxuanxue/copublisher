# 📹 Copublisher

多平台内容一键发布：视频（微信视频号、YouTube Shorts、TikTok、Instagram Reels）+ 文章（Medium、Twitter/X、Dev.to）。

## ✨ 功能特性

- 🎯 **多平台**: 视频 4（微信、YouTube、TikTok、Instagram）+ 文章 3（Medium、Twitter、Dev.to）
- 🎨 **GUI**: Gradio 界面，传统模式与 Episode 模式（ep*.json）
- 📄 **多种用法**: 传统（--video + --script）、批量（--batch-dir）、Episode（--episode）、Job 模式（调度系统）
- 🔐 **登录记忆**: 自动保存登录状态，无需重复认证
- 📦 **合集/播放列表**: 微信视频号合集、YouTube 播放列表
- 💻 **CLI + SDK**: 命令行与 Python API，支持 `copublisher job run` 与 Blue Ocean 集成

**适用场景**：个人/团队多平台发布、课程/系列批量发布、与调度系统（如 Blue Ocean）集成。

## 🚀 快速开始

### 1. 安装

```bash
cd copublisher

# 使用 uv 安装（推荐）
uv pip install -e .

# 安装 Playwright 浏览器（用于微信视频号发布）
uv run playwright install chromium
```

### 2. 验证安装

```bash
python -m copublisher verify
# 或（向后兼容）: python verify_install.py
```

更多示例与运行方式见 [examples/README.md](examples/README.md)。

### 3. 配置 YouTube API（可选）

如果需要发布到 YouTube Shorts，需要先配置 YouTube API：

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建或选择项目
3. 启用 YouTube Data API v3
4. 创建 OAuth 2.0 凭据（桌面应用）
5. **重要**: 添加授权重定向 URI: `http://localhost:8080/`
6. 下载凭据文件并保存为 `config/youtube_credentials.json`

## 📖 使用方法

### 方式 1: GUI 界面

```bash
# 启动 GUI（默认端口 7860）
copublisher
# 或
python -m copublisher

# 指定端口（例如 8080）
copublisher --port 8080

# 如遇 localhost 问题，使用 share 模式
copublisher --share
```

启动后访问 `http://localhost:7860`（或所指定端口）。

### 方式 2: 命令行

**传统模式**（单视频 + script.json）：

```bash
copublisher --video /path/to/video.mp4 --platform wechat --script /path/to/script.json
copublisher --video /path/to/video.mp4 --platform youtube --script /path/to/script.json
copublisher --video /path/to/video.mp4 --platform both --script /path/to/script.json
copublisher --video /path/to/video.mp4 --platform youtube --privacy public --script /path/to/script.json
```

**批量模式**（系列目录，自动匹配 output/*-Clip.mp4 与 config/*-Strategy.json）：

```bash
copublisher --batch-dir /path/to/series/yingxiongernv --platform wechat --account 奶奶讲故事
```

**Episode 模式**（从 ep*.json 发布到多平台）：

```bash
copublisher --episode ep01.json --platform medium,twitter
copublisher --episode ep01.json --platform all-articles   # Medium + Twitter + Dev.to
copublisher --episode ep01.json --platform all-videos     # 微信 + YouTube + TikTok + Instagram
```

### 方式 3: 子命令

```bash
# 验证安装
copublisher verify

# 公众号草稿批量发布（Markdown → 图文草稿）
copublisher gzh-drafts /path/to/md-folder [--skip N]

# 结构化 Job 模式（用于调度系统）
copublisher job run --job-file job.json --json
```

**Job 文件 (job.json) 最小示例**（用于调度/集成）：

```json
{
  "job_id": "run1",
  "mode": "legacy",
  "platforms": ["wechat", "youtube"],
  "video": "/path/to/video.mp4",
  "script": "/path/to/script.json",
  "privacy": "private"
}
```

输出为 JSON（`--json`），字段含 `status`、`platforms`、`retryable` 等；完整 schema 与错误码见 [ARCHITECTURE.md](ARCHITECTURE.md)。

### 方式 4: Python 代码

```python
from copublisher import (
    WeChatPublisher,
    YouTubePublisher,
    WeChatPublishTask,
    YouTubePublishTask,
)

# 微信视频号
with WeChatPublisher(headless=False) as publisher:
    publisher.authenticate()
    task = WeChatPublishTask.from_json(video_path, script_data)
    success, message = publisher.publish(task)

# YouTube Shorts
with YouTubePublisher() as publisher:
    task = YouTubePublishTask.from_json(video_path, script_data)
    success, video_url = publisher.publish(task)
```

## 📋 JSON 脚本格式

```json
{
    "wechat": {
        "title": "视频标题（最多16字）",
        "description": "视频描述内容",
        "hashtags": ["#标签1", "#标签2", "#标签3"],
        "heji": "合集名称",
        "huodong": "活动名称"
    },
    "youtube": {
        "title": "YouTube 视频标题",
        "description": "YouTube 视频描述",
        "tags": ["标签1", "标签2"],
        "playlists": "播放列表名称",
        "privacy": "private"
    }
}
```

### 字段说明

#### 微信视频号 (wechat)

| 字段 | 必需 | 说明 |
|------|------|------|
| `title` | 否 | 视频短标题，最多16个字符 |
| `description` | 否 | 视频描述 |
| `hashtags` | 否 | 话题标签数组，会自动拼接到描述末尾 |
| `heji` | 否 | 合集名称，程序会自动选择对应合集 |
| `huodong` | 否 | 活动名称，程序会自动搜索并参加活动 |

#### YouTube Shorts (youtube)

| 字段 | 必需 | 说明 |
|------|------|------|
| `title` | 是 | 视频标题 |
| `description` | 是 | 视频描述 |
| `tags` | 否 | 标签数组 |
| `playlists` | 否 | 播放列表名称（不存在会自动创建）|
| `privacy` | 否 | 隐私设置：`public`、`unlisted`、`private`（默认）|

其他平台（Medium、Twitter、Dev.to、TikTok、Instagram）的 script 结构见 [examples/README.md](examples/README.md) 或各平台对应字段（如 `medium`、`twitter`、`devto` 等）。

## 🔐 认证状态保存

### 微信视频号

登录状态保存在用户主目录下：

```
~/.copublisher/wechat_auth.json
```

首次使用需要扫码登录，之后会自动使用保存的登录状态。

### YouTube

OAuth2 认证信息保存在：

```
config/youtube_credentials.json  # OAuth2 客户端凭据（需手动配置）
config/youtube_token.json        # 访问令牌（自动生成）
```

## 🛠️ 代码与集成

- **目录与架构约定**（依赖规则、Job schema）：[ARCHITECTURE.md](ARCHITECTURE.md)
- **示例**：[examples/README.md](examples/README.md)
- **集成**：`uv pip install -e .` 后 `from copublisher import WeChatPublisher, YouTubePublisher, WeChatPublishTask, YouTubePublishTask`
- **旧版迁移**：`WeChatChannelPublisher`→`WeChatPublisher`，`VideoPublishTask`→`WeChatPublishTask`，`login()`→`authenticate()`

## ❓ 常见问题

### 导入错误

```
ModuleNotFoundError: No module named 'copublisher'
```

**解决**: 完成上方「安装」步骤后，在项目根目录执行 `uv pip install -e .`。

### Playwright 浏览器无法启动

**解决**: 重新安装浏览器：
```bash
uv run playwright install chromium
```

### YouTube API 认证失败

检查以下几点：
1. `config/youtube_credentials.json` 文件是否存在
2. Google Cloud Console 中是否添加了重定向 URI: `http://localhost:8080/`
3. 是否启用了 YouTube Data API v3

### GUI localhost 访问问题

**解决**: 使用 share 模式：
```bash
copublisher --share
```

### 微信视频号需要手动点击发布

是的，出于安全考虑需人工点击「发布」。详见下方「注意事项」。

## ⚠️ 注意事项

### 微信视频号

1. 发布过程中会打开 Chrome 浏览器窗口，请勿关闭
2. 视频上传完成后，需要在浏览器中手动点击「发布」按钮
3. 需要稳定的网络连接

### YouTube Shorts

1. YouTube API 每日有使用配额限制
2. 竖屏视频（9:16）会自动识别为 Shorts
3. 首次授权需要在浏览器中完成 OAuth2 授权

### 通用

- 支持的视频格式: MP4、MOV、AVI
- 建议视频分辨率: 1080x1920 (9:16 竖屏)

## 📄 License

MIT License
