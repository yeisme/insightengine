"""基于 loguru 的高性能日志模块。

设计目标：
- 快速的异步文件写入
- 支持按大小/时间轮转日志
- 彩色、易读的控制台输出
- 捕获标准库 logging（stdlib logging）
"""

from __future__ import annotations

from typing import Optional, Any
import sys
import os

from loguru import logger as _logger


def _ensure_log_dir(path: str) -> None:
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        # 尽力创建日志目录（遇到错误则静默处理）
        pass


def configure_logger(
    *,
    name: str = "insightengine",
    console_level: str = "INFO",
    file_level: str = "DEBUG",
    log_dir: str | None = None,
    rotation: str = "10 MB",
    retention: str = "14 days",
    compression: str = "zip",
    backtrace: bool = True,
    diagnose: bool = False,
    serialize: bool = False,
    intercept_stdlib: bool = True,
) -> Any:
    """配置并返回一个已设置好的 loguru logger 实例。

    返回应用程序使用的 loguru logger 实例。
    """

    # 移除已存在的处理器以避免重复输出
    _logger.remove()

    # 控制台 sink：彩色显示，包含时间/等级/名称/函数/行号/消息
    _logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=console_level,
        enqueue=True,
        backtrace=backtrace,
        diagnose=diagnose,
    )

    # 如果指定了日志目录，则添加文件 sink
    if log_dir:
        _ensure_log_dir(log_dir)
        file_path = os.path.join(log_dir, f"{name}.log")
        # loguru 通过 enqueue=True 支持异步写入
        _logger.add(
            file_path,
            rotation=rotation,
            retention=retention,
            compression=compression,
            level=file_level,
            serialize=serialize,
            enqueue=True,
            backtrace=backtrace,
            diagnose=diagnose,
        )

    # 可选：拦截并重定向标准库 logging 到 loguru
    if intercept_stdlib:
        try:
            import logging

            class InterceptHandler(logging.Handler):
                def emit(
                    self, record: logging.LogRecord
                ) -> None:  # pragma: no cover - 简单透传
                    try:
                        level = _logger.level(record.levelname).name
                    except Exception:
                        level = record.levelno
                    frame, depth = logging.currentframe(), 2
                    # 跳过 logging 内部帧以定位调用者
                    while frame and frame.f_code.co_filename == logging.__file__:
                        frame = frame.f_back
                        depth += 1
                    # 将原始日志信息转发给 loguru
                    _logger.opt(depth=depth, exception=record.exc_info).log(
                        level, record.getMessage()
                    )

            logging.root.handlers = [InterceptHandler()]
            logging.root.setLevel(0)
        except Exception:
            # 静默失败，非关键功能
            pass

    return _logger


# 默认配置好的 logger 实例
_DEFAULT_LOG_DIR = os.getenv("INSIGHTENGINE_LOG_DIR", os.path.join(os.getcwd(), "logs"))
logger = configure_logger(log_dir=_DEFAULT_LOG_DIR)


def get_logger(name: Optional[str] = None):
    """返回带有指定名称绑定（name）的子 logger。"""
    if name:
        return logger.bind(name=name)
    return logger
