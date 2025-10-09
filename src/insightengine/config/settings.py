"""应用配置（基于 pydantic-settings）。

包含应用运行时配置（环境变量优先），以及将配置应用到日志模块的辅助函数。
"""

from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置模型（可通过环境变量注入）。

    环境变量前缀：INSIGHTENGINE_
    例如 INSIGHTENGINE_LOG_LEVEL=DEBUG
    """

    # 日志相关
    log_name: str = "insightengine"
    log_console_level: str = "INFO"
    log_file_level: str = "DEBUG"
    log_dir: Optional[str] = None
    log_rotation: str = "10 MB"
    log_retention: str = "14 days"
    log_compression: str = "zip"
    log_backtrace: bool = True
    log_diagnose: bool = False
    log_serialize: bool = False
    log_intercept_stdlib: bool = True

    model_config = SettingsConfigDict(env_prefix="INSIGHTENGINE_")


# module-level cached settings
_SETTINGS: Optional[Settings] = None


def get_settings(force_reload: bool = False) -> Settings:
    """返回全局 Settings 单例（按需从环境加载）。

    如果 force_reload=True，会从环境/来源重新创建实例。
    """

    global _SETTINGS
    if _SETTINGS is None or force_reload:
        _SETTINGS = Settings()
    return _SETTINGS


__all__ = ["Settings", "get_settings"]
