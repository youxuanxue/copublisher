"""
平台枚举与能力定义（单一数据源）

Platform 枚举为领域核心，VIDEO_PLATFORMS、ARTICLE_PLATFORMS、ALL_PLATFORMS
均由此派生，避免 domain、workflows 等多处维护重复列表。
"""

from enum import Enum


class Platform(Enum):
    """支持的平台枚举"""

    WECHAT = "wechat"
    YOUTUBE = "youtube"
    MEDIUM = "medium"
    TWITTER = "twitter"
    DEVTO = "devto"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"


# 由 Platform 枚举派生的平台集合（单一数据源）
VIDEO_PLATFORMS = frozenset(
    {Platform.WECHAT, Platform.YOUTUBE, Platform.TIKTOK, Platform.INSTAGRAM}
)
ARTICLE_PLATFORMS = frozenset(
    {Platform.MEDIUM, Platform.TWITTER, Platform.DEVTO}
)
ALL_PLATFORMS = frozenset(VIDEO_PLATFORMS | ARTICLE_PLATFORMS)

# 字符串形式的平台集合（供 JobSpec、workflows 等使用）
VIDEO_PLATFORM_STRINGS = frozenset(p.value for p in VIDEO_PLATFORMS)
ARTICLE_PLATFORM_STRINGS = frozenset(p.value for p in ARTICLE_PLATFORMS)
ALL_PLATFORM_STRINGS = frozenset(p.value for p in ALL_PLATFORMS)
