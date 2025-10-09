"""
insightengine.utils 包

通用工具集合（字符串处理、时间工具、序列化助手、重试/限速装饰器等），供全局复用。
"""

# 便捷导出
from .log import logger as logger

__all__ = ["logger"]
