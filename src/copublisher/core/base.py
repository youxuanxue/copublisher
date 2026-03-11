"""
发布器抽象基类

Publisher ABC 定义发布器接口，具体实现位于各平台模块（wechat、youtube 等）。
任务类型（PublishTask）来自 domain.tasks，保持领域与实现的分离。
"""

from abc import ABC, abstractmethod
from typing import Callable, Optional, Tuple

from copublisher.domain.tasks import PublishTask


class Publisher(ABC):
    """
    发布器抽象基类

    所有平台的发布器都应继承此类并实现其抽象方法。
    """

    def __init__(self, log_callback: Optional[Callable[[str], None]] = None):
        """
        初始化发布器

        Args:
            log_callback: 日志回调函数，用于在 GUI 中显示日志
        """
        self.log_callback = log_callback

    @abstractmethod
    def authenticate(self) -> None:
        """执行平台认证/登录"""
        pass

    @abstractmethod
    def publish(self, task: PublishTask) -> Tuple[bool, Optional[str]]:
        """
        发布视频到平台

        Args:
            task: 发布任务

        Returns:
            (success: bool, message: Optional[str]) - 成功状态和消息（如视频URL）
        """
        pass

    def _log(self, message: str, level: str = "INFO") -> None:
        """记录日志"""
        import logging

        logger = logging.getLogger(self.__class__.__name__)
        if level == "INFO":
            logger.info(message)
        elif level == "WARNING":
            logger.warning(message)
        elif level == "ERROR":
            logger.error(message)
        if self.log_callback:
            self.log_callback(f"[{level}] {message}")

    def __enter__(self) -> "Publisher":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass
