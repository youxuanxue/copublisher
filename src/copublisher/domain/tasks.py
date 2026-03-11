"""
发布任务领域模型

PublishTask、ArticlePublishTask 及具体任务类，描述「发布什么」的领域语义。
与 JobSpec 共同构成任务定义层，供 infrastructure 层 Publisher 消费。
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class PublishTask(ABC):
    """
    发布任务基类

    所有视频平台的发布任务都应继承此类。
    """

    video_path: Path
    title: str = ""
    description: str = ""
    cover_path: Optional[Path] = None

    @abstractmethod
    def validate(self) -> None:
        """验证任务参数是否有效"""
        if not self.video_path.exists():
            raise FileNotFoundError(f"视频文件不存在: {self.video_path}")
        if self.cover_path and not self.cover_path.exists():
            raise FileNotFoundError(f"封面文件不存在: {self.cover_path}")

    @classmethod
    @abstractmethod
    def from_json(cls, video_path: Path, json_data: dict) -> "PublishTask":
        """从 JSON 数据创建发布任务"""
        pass


@dataclass
class WeChatPublishTask(PublishTask):
    """微信视频号发布任务"""

    hashtags: List[str] = field(default_factory=list)
    heji: str = ""  # 合集名称（可选）
    huodong: str = ""  # 活动名称（可选）

    def validate(self) -> None:
        """验证微信视频号任务参数"""
        super().validate()
        if len(self.title) > 16:
            raise ValueError(f"微信视频号标题不能超过16字符: {self.title}")

    def get_full_description(self) -> str:
        """获取包含话题标签的完整描述"""
        desc = self.description.strip()
        if self.hashtags:
            hashtags_str = " ".join(self.hashtags)
            if hashtags_str not in desc:
                desc = f"{desc}\n\n{hashtags_str}"
        return desc

    @classmethod
    def from_json(cls, video_path: Path, json_data: dict) -> "WeChatPublishTask":
        """从 JSON 数据创建微信视频号发布任务"""
        import logging

        wechat_data = json_data.get("wechat", {})
        title = wechat_data.get("title", "")
        if len(title) > 16:
            logging.warning(f"标题超过16字符，将被截断: {title}")
            title = title[:16]
        return cls(
            video_path=video_path,
            title=title,
            description=wechat_data.get("description", ""),
            hashtags=wechat_data.get("hashtags", []),
            heji=wechat_data.get("heji", ""),
            huodong=wechat_data.get("huodong", ""),
        )


@dataclass
class YouTubePublishTask(PublishTask):
    """YouTube 发布任务"""

    tags: Optional[List[str]] = None
    category_id: str = "26"  # People & Blogs
    privacy_status: str = "private"  # "public", "unlisted", "private"
    made_for_kids: bool = False
    playlist_title: Optional[str] = None  # 播放列表名称

    def validate(self) -> None:
        """验证 YouTube 任务参数"""
        super().validate()
        if not self.title:
            raise ValueError("YouTube 标题不能为空")
        if not self.description:
            raise ValueError("YouTube 描述不能为空")
        if self.privacy_status not in ["public", "unlisted", "private"]:
            raise ValueError(f"无效的隐私设置: {self.privacy_status}")

    @classmethod
    def from_json(cls, video_path: Path, json_data: dict) -> "YouTubePublishTask":
        """从 JSON 数据创建 YouTube 发布任务"""
        youtube_data = json_data.get("youtube", {})
        if not youtube_data and "wechat" in json_data:
            wechat_data = json_data["wechat"]
            title = wechat_data.get("title", "")
            description = wechat_data.get("description", "")
            hashtags = wechat_data.get("hashtags", [])
            tags = [tag.replace("#", "") for tag in hashtags if tag.startswith("#")]
            playlist_title = None
            privacy_status = "private"
        else:
            title = youtube_data.get("title", "")
            description = youtube_data.get("description", "")
            tags = youtube_data.get("tags", youtube_data.get("hashtags", []))
            tags = [tag.replace("#", "").strip() for tag in tags]
            playlist_title = youtube_data.get("playlists", None)
            privacy_status = youtube_data.get("privacy", "private")
        return cls(
            video_path=video_path,
            title=title,
            description=description,
            tags=tags,
            privacy_status=privacy_status,
            made_for_kids=False,
            playlist_title=playlist_title,
        )


@dataclass
class TikTokPublishTask(PublishTask):
    """TikTok 发布任务"""

    privacy: str = "public"  # "public", "friends", "private"

    def validate(self) -> None:
        """验证 TikTok 任务参数"""
        super().validate()
        if self.privacy not in ["public", "friends", "private"]:
            raise ValueError(f"无效的隐私设置: {self.privacy}")

    @classmethod
    def from_json(cls, video_path: Path, json_data: dict) -> "TikTokPublishTask":
        """从 JSON 数据创建 TikTok 发布任务"""
        tiktok_data = json_data.get("tiktok", {})
        return cls(
            video_path=video_path,
            description=tiktok_data.get("description", ""),
            privacy=tiktok_data.get("privacy", "public"),
        )


@dataclass
class InstagramPublishTask(PublishTask):
    """Instagram Reels 发布任务"""

    caption: str = ""
    video_url: Optional[str] = None  # 公网视频 URL（Graph API 需要）
    privacy: str = "public"

    def validate(self) -> None:
        """验证 Instagram 任务参数"""
        if not self.video_url and not self.video_path.exists():
            raise FileNotFoundError(
                f"视频文件不存在且未提供公网 URL: {self.video_path}"
            )

    @classmethod
    def from_json(cls, video_path: Path, json_data: dict) -> "InstagramPublishTask":
        """从 JSON 数据创建 Instagram 发布任务"""
        ig_data = json_data.get("instagram", {})
        return cls(
            video_path=video_path,
            caption=ig_data.get("caption", ""),
            privacy=ig_data.get("privacy", "public"),
        )


# ============================================================
# 文章发布任务基类（适用于 Medium / Dev.to / Twitter）
# ============================================================


@dataclass
class ArticlePublishTask(ABC):
    """
    文章发布任务基类

    适用于不需要视频的文章类平台（Medium、Dev.to、Twitter）。
    与 PublishTask 并列，不要求 video_path。
    """

    title: str = ""

    @abstractmethod
    def validate(self) -> None:
        """验证任务参数是否有效"""
        pass


@dataclass
class MediumPublishTask(ArticlePublishTask):
    """Medium 发布任务"""

    content: str = ""  # Markdown 正文
    tags: List[str] = field(default_factory=list)  # 最多 5 个
    canonical_url: Optional[str] = None
    publish_status: str = "draft"  # "draft", "public", "unlisted"

    def validate(self) -> None:
        """验证 Medium 任务参数"""
        if not self.title:
            raise ValueError("Medium 标题不能为空")
        if not self.content:
            raise ValueError("Medium 文章内容不能为空")
        if len(self.tags) > 5:
            raise ValueError(f"Medium 标签最多 5 个，当前 {len(self.tags)} 个")
        if self.publish_status not in ["draft", "public", "unlisted"]:
            raise ValueError(f"无效的发布状态: {self.publish_status}")


@dataclass
class DevToPublishTask(ArticlePublishTask):
    """Dev.to 发布任务"""

    body_markdown: str = ""  # Markdown 正文
    tags: List[str] = field(default_factory=list)  # 最多 4 个，全小写
    series: Optional[str] = None  # 系列名称
    canonical_url: Optional[str] = None
    published: bool = False

    def validate(self) -> None:
        """验证 Dev.to 任务参数"""
        if not self.title:
            raise ValueError("Dev.to 标题不能为空")
        if not self.body_markdown:
            raise ValueError("Dev.to 文章内容不能为空")
        if len(self.tags) > 4:
            raise ValueError(f"Dev.to 标签最多 4 个，当前 {len(self.tags)} 个")
        for tag in self.tags:
            if tag != tag.lower():
                raise ValueError(f"Dev.to 标签必须为小写: {tag}")
            if " " in tag:
                raise ValueError(f"Dev.to 标签不能包含空格: {tag}")


@dataclass
class TwitterPublishTask(ArticlePublishTask):
    """Twitter/X Thread 发布任务"""

    tweets: List[str] = field(default_factory=list)
    hashtags: List[str] = field(default_factory=list)

    @staticmethod
    def _twitter_char_count(text: str) -> int:
        """计算 Twitter 实际字符数（URL 按 23 字符计）"""
        url_pattern = re.compile(r"https?://\S+")
        adjusted = url_pattern.sub("x" * 23, text)
        return len(adjusted)

    def validate(self) -> None:
        """验证 Twitter 任务参数（超长仅警告，不阻断）"""
        import logging

        logger = logging.getLogger(__name__)
        if not self.tweets:
            raise ValueError("Twitter Thread 至少需要一条推文")
        for i, tweet in enumerate(self.tweets):
            char_count = self._twitter_char_count(tweet)
            if char_count > 280:
                logger.warning(
                    f"第 {i+1} 条推文超过 280 字符: {char_count} 字符, "
                    f"发布时可能需要缩短"
                )
