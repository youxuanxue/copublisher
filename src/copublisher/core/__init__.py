"""核心发布模块."""

from importlib import import_module

_EXPORTS = {
    # 枚举（domain 单一数据源）
    "Platform": ("copublisher.domain.platform", "Platform"),
    # 任务类（domain 领域模型）
    "PublishTask": ("copublisher.domain.tasks", "PublishTask"),
    "ArticlePublishTask": ("copublisher.domain.tasks", "ArticlePublishTask"),
    "WeChatPublishTask": ("copublisher.domain.tasks", "WeChatPublishTask"),
    "YouTubePublishTask": ("copublisher.domain.tasks", "YouTubePublishTask"),
    "MediumPublishTask": ("copublisher.domain.tasks", "MediumPublishTask"),
    "TwitterPublishTask": ("copublisher.domain.tasks", "TwitterPublishTask"),
    "DevToPublishTask": ("copublisher.domain.tasks", "DevToPublishTask"),
    "TikTokPublishTask": ("copublisher.domain.tasks", "TikTokPublishTask"),
    "InstagramPublishTask": ("copublisher.domain.tasks", "InstagramPublishTask"),
    # 发布器基类（core）
    "Publisher": ("copublisher.core.base", "Publisher"),
    # 适配层
    "EpisodeAdapter": ("copublisher.core.adapter", "EpisodeAdapter"),
    # 公众号草稿发布
    "GzhDraftPublisher": ("copublisher.core.gzh_drafts", "GzhDraftPublisher"),
    # 发布器
    "WeChatPublisher": ("copublisher.core.wechat", "WeChatPublisher"),
    "YouTubePublisher": ("copublisher.core.youtube", "YouTubePublisher"),
    "MediumPublisher": ("copublisher.core.medium", "MediumPublisher"),
    "TwitterPublisher": ("copublisher.core.twitter", "TwitterPublisher"),
    "DevToPublisher": ("copublisher.core.devto", "DevToPublisher"),
    "TikTokPublisher": ("copublisher.core.tiktok", "TikTokPublisher"),
    "InstagramPublisher": ("copublisher.core.instagram", "InstagramPublisher"),
}


def __getattr__(name):
    if name in _EXPORTS:
        module_name, symbol_name = _EXPORTS[name]
        module = import_module(module_name)
        value = getattr(module, symbol_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    # 枚举与基类
    "Platform",
    "PublishTask",
    "ArticlePublishTask",
    "Publisher",
    # 适配层
    "EpisodeAdapter",
    # 任务类
    "WeChatPublishTask",
    "YouTubePublishTask",
    "MediumPublishTask",
    "TwitterPublishTask",
    "DevToPublishTask",
    "TikTokPublishTask",
    "InstagramPublishTask",
    # 公众号草稿发布
    "GzhDraftPublisher",
    # 发布器
    "WeChatPublisher",
    "YouTubePublisher",
    "MediumPublisher",
    "TwitterPublisher",
    "DevToPublisher",
    "TikTokPublisher",
    "InstagramPublisher",
]
