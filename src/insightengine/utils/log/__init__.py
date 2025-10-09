"""insightengine 的日志工具模块。

提供基于 loguru 的高性能 logger，特性包括：
- 彩色控制台输出
- 日志文件轮转
- 异步 sink 提升性能
- 压缩与保留策略
- 可选的标准库 logging 拦截
"""

from .logger import logger, configure_logger

__all__ = ["logger", "configure_logger"]
