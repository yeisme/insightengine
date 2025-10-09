"""测试 insightengine.config.settings 模块。"""

import os
import pytest
from unittest.mock import patch

from insightengine.config.settings import Settings, get_settings


class TestSettings:
    """测试 Settings 配置类。"""

    def test_default_values(self):
        """测试默认配置值。"""
        settings = Settings()

        assert settings.log_name == "insightengine"
        assert settings.log_console_level == "INFO"
        assert settings.log_file_level == "DEBUG"
        assert settings.log_dir is None
        assert settings.log_rotation == "10 MB"
        assert settings.log_retention == "14 days"
        assert settings.log_compression == "zip"
        assert settings.log_backtrace is True
        assert settings.log_diagnose is False
        assert settings.log_serialize is False
        assert settings.log_intercept_stdlib is True

    def test_env_prefix(self):
        """测试环境变量前缀 INSIGHTENGINE_ 是否正确工作。"""
        with patch.dict(
            os.environ,
            {
                "INSIGHTENGINE_LOG_NAME": "test_app",
                "INSIGHTENGINE_LOG_CONSOLE_LEVEL": "DEBUG",
                "INSIGHTENGINE_LOG_FILE_LEVEL": "WARNING",
            },
        ):
            settings = Settings()

            assert settings.log_name == "test_app"
            assert settings.log_console_level == "DEBUG"
            assert settings.log_file_level == "WARNING"

    def test_log_dir_from_env(self):
        """测试从环境变量设置 log_dir。"""
        test_log_dir = "/tmp/test_logs"
        with patch.dict(os.environ, {"INSIGHTENGINE_LOG_DIR": test_log_dir}):
            settings = Settings()
            assert settings.log_dir == test_log_dir

    def test_boolean_fields_from_env(self):
        """测试布尔类型字段的环境变量解析。"""
        with patch.dict(
            os.environ,
            {
                "INSIGHTENGINE_LOG_BACKTRACE": "false",
                "INSIGHTENGINE_LOG_DIAGNOSE": "true",
                "INSIGHTENGINE_LOG_SERIALIZE": "1",
                "INSIGHTENGINE_LOG_INTERCEPT_STDLIB": "0",
            },
        ):
            settings = Settings()

            assert settings.log_backtrace is False
            assert settings.log_diagnose is True
            assert settings.log_serialize is True
            assert settings.log_intercept_stdlib is False

    def test_custom_rotation_and_retention(self):
        """测试自定义日志轮转和保留策略。"""
        with patch.dict(
            os.environ,
            {
                "INSIGHTENGINE_LOG_ROTATION": "100 MB",
                "INSIGHTENGINE_LOG_RETENTION": "30 days",
                "INSIGHTENGINE_LOG_COMPRESSION": "gz",
            },
        ):
            settings = Settings()

            assert settings.log_rotation == "100 MB"
            assert settings.log_retention == "30 days"
            assert settings.log_compression == "gz"


class TestGetSettings:
    """测试 get_settings 单例函数。"""

    def test_singleton_behavior(self):
        """测试 get_settings 返回相同的实例（单例模式）。"""
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_force_reload(self):
        """测试 force_reload 参数强制重新加载配置。"""
        # 获取初始设置
        get_settings()

        # 修改环境变量并强制重载
        with patch.dict(os.environ, {"INSIGHTENGINE_LOG_NAME": "reloaded_app"}):
            settings2 = get_settings(force_reload=True)

            # 应该是新的实例，且配置已更新
            assert settings2.log_name == "reloaded_app"

            # 再次获取应该返回重载后的实例
            settings3 = get_settings()
            assert settings3 is settings2
            assert settings3.log_name == "reloaded_app"

    def test_settings_cached_after_first_call(self):
        """测试设置在首次调用后被缓存。"""
        # 清空缓存（通过 force_reload）
        settings1 = get_settings(force_reload=True)

        # 修改环境变量
        with patch.dict(os.environ, {"INSIGHTENGINE_LOG_NAME": "cached_test"}):
            # 不使用 force_reload，应该返回缓存的实例
            settings2 = get_settings(force_reload=False)

            # 由于是缓存的，不应该反映新的环境变量
            assert settings2 is settings1
            assert settings2.log_name == settings1.log_name

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """每个测试后清理全局缓存。"""
        yield
        # 测试后重置为默认配置
        get_settings(force_reload=True)


class TestSettingsIntegration:
    """Settings 集成测试。"""

    def test_all_log_settings_can_be_configured(self):
        """测试所有日志相关设置都可以通过环境变量配置。"""
        env_vars = {
            "INSIGHTENGINE_LOG_NAME": "integration_test",
            "INSIGHTENGINE_LOG_CONSOLE_LEVEL": "WARNING",
            "INSIGHTENGINE_LOG_FILE_LEVEL": "ERROR",
            "INSIGHTENGINE_LOG_DIR": "/var/log/test",
            "INSIGHTENGINE_LOG_ROTATION": "50 MB",
            "INSIGHTENGINE_LOG_RETENTION": "7 days",
            "INSIGHTENGINE_LOG_COMPRESSION": "tar.gz",
            "INSIGHTENGINE_LOG_BACKTRACE": "false",
            "INSIGHTENGINE_LOG_DIAGNOSE": "true",
            "INSIGHTENGINE_LOG_SERIALIZE": "true",
            "INSIGHTENGINE_LOG_INTERCEPT_STDLIB": "false",
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()

            assert settings.log_name == "integration_test"
            assert settings.log_console_level == "WARNING"
            assert settings.log_file_level == "ERROR"
            assert settings.log_dir == "/var/log/test"
            assert settings.log_rotation == "50 MB"
            assert settings.log_retention == "7 days"
            assert settings.log_compression == "tar.gz"
            assert settings.log_backtrace is False
            assert settings.log_diagnose is True
            assert settings.log_serialize is True
            assert settings.log_intercept_stdlib is False
