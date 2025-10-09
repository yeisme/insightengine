"""日志配置适配器。

本模块负责把 `Settings` 中与日志相关的字段映射为 `insightengine.utils.log.configure_logger` 可接受的参数，
并提供 `apply_logging_from_settings` 做一次性或幂等的配置调用。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from insightengine.config.settings import Settings, get_settings


def map_settings_to_logger_kwargs(settings: Settings) -> Dict[str, Any]:
    """把 Settings 映射为传给 configure_logger 的关键字参数字典。"""
    return {
        "name": settings.log_name,
        "console_level": settings.log_console_level,
        "file_level": settings.log_file_level,
        "log_dir": settings.log_dir,
        "rotation": settings.log_rotation,
        "retention": settings.log_retention,
        "compression": settings.log_compression,
        "backtrace": settings.log_backtrace,
        "diagnose": settings.log_diagnose,
        "serialize": settings.log_serialize,
        "intercept_stdlib": settings.log_intercept_stdlib,
    }


def apply_logging_from_settings(settings: Optional[Settings] = None) -> None:
    """从 settings 加载并应用日志配置。

    如果未传入 settings，会使用 `get_settings()` 获取单例。
    """
    if settings is None:
        settings = get_settings()

    kwargs = map_settings_to_logger_kwargs(settings)

    # 延迟导入日志模块以避免循环依赖
    from insightengine.utils.log import configure_logger

    configure_logger(**kwargs)


__all__ = ["map_settings_to_logger_kwargs", "apply_logging_from_settings"]
