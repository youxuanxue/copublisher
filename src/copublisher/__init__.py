"""
媒体发布工具

多平台内容发布工具，支持微信视频号、YouTube Shorts、Medium、Twitter/X、
Dev.to、TikTok、Instagram Reels。支持从 ep*.json 素材文件直接发布。
"""

__version__ = "3.0.0"

from importlib import import_module

_EXPORTS = {
    "Platform": ("copublisher.core.base", "Platform"),
    "Publisher": ("copublisher.core.base", "Publisher"),
    "PublishTask": ("copublisher.core.base", "PublishTask"),
    "ArticlePublishTask": ("copublisher.core.base", "ArticlePublishTask"),
    "WeChatPublishTask": ("copublisher.core.base", "WeChatPublishTask"),
    "YouTubePublishTask": ("copublisher.core.base", "YouTubePublishTask"),
    "MediumPublishTask": ("copublisher.core.base", "MediumPublishTask"),
    "TwitterPublishTask": ("copublisher.core.base", "TwitterPublishTask"),
    "DevToPublishTask": ("copublisher.core.base", "DevToPublishTask"),
    "TikTokPublishTask": ("copublisher.core.base", "TikTokPublishTask"),
    "InstagramPublishTask": ("copublisher.core.base", "InstagramPublishTask"),
    "EpisodeAdapter": ("copublisher.core.adapter", "EpisodeAdapter"),
    "WeChatPublisher": ("copublisher.core.wechat", "WeChatPublisher"),
    "YouTubePublisher": ("copublisher.core.youtube", "YouTubePublisher"),
    "MediumPublisher": ("copublisher.core.medium", "MediumPublisher"),
    "TwitterPublisher": ("copublisher.core.twitter", "TwitterPublisher"),
    "DevToPublisher": ("copublisher.core.devto", "DevToPublisher"),
    "TikTokPublisher": ("copublisher.core.tiktok", "TikTokPublisher"),
    "InstagramPublisher": ("copublisher.core.instagram", "InstagramPublisher"),
}


def __getattr__(name):
    """Lazy export heavy symbols to avoid module-level side effects."""
    if name in _EXPORTS:
        module_name, symbol_name = _EXPORTS[name]
        module = import_module(module_name)
        value = getattr(module, symbol_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "__version__",
    "Platform",
    "Publisher",
    "PublishTask",
    "ArticlePublishTask",
    "EpisodeAdapter",
    "WeChatPublisher",
    "YouTubePublisher",
    "MediumPublisher",
    "TwitterPublisher",
    "DevToPublisher",
    "TikTokPublisher",
    "InstagramPublisher",
    "WeChatPublishTask",
    "YouTubePublishTask",
    "MediumPublishTask",
    "TwitterPublishTask",
    "DevToPublishTask",
    "TikTokPublishTask",
    "InstagramPublishTask",
]
