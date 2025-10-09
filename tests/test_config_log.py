"""测试 insightengine.config.log 模块。"""

import os
from unittest.mock import patch, MagicMock

from insightengine.config.settings import Settings
from insightengine.config.log import (
    map_settings_to_logger_kwargs,
    apply_logging_from_settings,
)


class TestMapSettingsToLoggerKwargs:
    """测试 map_settings_to_logger_kwargs 函数。"""

    def test_default_settings_mapping(self):
        """测试默认 Settings 到 logger kwargs 的映射。"""
        settings = Settings()
        kwargs = map_settings_to_logger_kwargs(settings)

        assert kwargs["name"] == "insightengine"
        assert kwargs["console_level"] == "INFO"
        assert kwargs["file_level"] == "DEBUG"
        assert kwargs["log_dir"] is None
        assert kwargs["rotation"] == "10 MB"
        assert kwargs["retention"] == "14 days"
        assert kwargs["compression"] == "zip"
        assert kwargs["backtrace"] is True
        assert kwargs["diagnose"] is False
        assert kwargs["serialize"] is False
        assert kwargs["intercept_stdlib"] is True

    def test_custom_settings_mapping(self):
        """测试自定义 Settings 到 logger kwargs 的映射。"""
        settings = Settings(
            log_name="custom_app",
            log_console_level="WARNING",
            log_file_level="ERROR",
            log_dir="/custom/logs",
            log_rotation="50 MB",
            log_retention="30 days",
            log_compression="gz",
            log_backtrace=False,
            log_diagnose=True,
            log_serialize=True,
            log_intercept_stdlib=False,
        )
        kwargs = map_settings_to_logger_kwargs(settings)

        assert kwargs["name"] == "custom_app"
        assert kwargs["console_level"] == "WARNING"
        assert kwargs["file_level"] == "ERROR"
        assert kwargs["log_dir"] == "/custom/logs"
        assert kwargs["rotation"] == "50 MB"
        assert kwargs["retention"] == "30 days"
        assert kwargs["compression"] == "gz"
        assert kwargs["backtrace"] is False
        assert kwargs["diagnose"] is True
        assert kwargs["serialize"] is True
        assert kwargs["intercept_stdlib"] is False

    def test_all_required_keys_present(self):
        """测试返回的字典包含所有必需的键。"""
        settings = Settings()
        kwargs = map_settings_to_logger_kwargs(settings)

        required_keys = {
            "name",
            "console_level",
            "file_level",
            "log_dir",
            "rotation",
            "retention",
            "compression",
            "backtrace",
            "diagnose",
            "serialize",
            "intercept_stdlib",
        }

        assert set(kwargs.keys()) == required_keys

    def test_mapping_preserves_types(self):
        """测试映射保持正确的数据类型。"""
        settings = Settings(
            log_name="test",
            log_console_level="DEBUG",
            log_dir="/tmp/logs",
            log_backtrace=True,
        )
        kwargs = map_settings_to_logger_kwargs(settings)

        assert isinstance(kwargs["name"], str)
        assert isinstance(kwargs["console_level"], str)
        assert isinstance(kwargs["backtrace"], bool)
        assert isinstance(kwargs["diagnose"], bool)
        assert isinstance(kwargs["serialize"], bool)
        assert isinstance(kwargs["intercept_stdlib"], bool)


class TestApplyLoggingFromSettings:
    """测试 apply_logging_from_settings 函数。"""

    @patch("insightengine.utils.log.configure_logger")
    def test_apply_with_default_settings(self, mock_configure):
        """测试使用默认 settings 应用日志配置。"""
        apply_logging_from_settings()

        # 验证 configure_logger 被调用了一次
        assert mock_configure.call_count == 1

        # 获取传递给 configure_logger 的参数
        call_kwargs = mock_configure.call_args[1]

        # 验证参数符合默认 settings
        assert call_kwargs["name"] == "insightengine"
        assert call_kwargs["console_level"] == "INFO"
        assert call_kwargs["file_level"] == "DEBUG"

    @patch("insightengine.utils.log.configure_logger")
    def test_apply_with_custom_settings(self, mock_configure):
        """测试使用自定义 settings 应用日志配置。"""
        custom_settings = Settings(
            log_name="test_app",
            log_console_level="WARNING",
            log_file_level="ERROR",
            log_dir="/test/logs",
        )

        apply_logging_from_settings(custom_settings)

        # 验证 configure_logger 被调用了一次
        assert mock_configure.call_count == 1

        # 获取传递给 configure_logger 的参数
        call_kwargs = mock_configure.call_args[1]

        # 验证参数符合自定义 settings
        assert call_kwargs["name"] == "test_app"
        assert call_kwargs["console_level"] == "WARNING"
        assert call_kwargs["file_level"] == "ERROR"
        assert call_kwargs["log_dir"] == "/test/logs"

    @patch("insightengine.utils.log.configure_logger")
    @patch("insightengine.config.log.get_settings")
    def test_apply_calls_get_settings_when_none(
        self, mock_get_settings, mock_configure
    ):
        """测试当 settings=None 时调用 get_settings()。"""
        mock_settings = MagicMock()
        mock_get_settings.return_value = mock_settings

        apply_logging_from_settings(settings=None)

        # 验证 get_settings 被调用
        mock_get_settings.assert_called_once()
        # 验证 configure_logger 被调用
        mock_configure.assert_called_once()

    @patch("insightengine.utils.log.configure_logger")
    @patch("insightengine.config.log.get_settings")
    def test_apply_does_not_call_get_settings_when_provided(
        self, mock_get_settings, mock_configure
    ):
        """测试当提供 settings 时不调用 get_settings()。"""
        custom_settings = Settings(log_name="provided_app")

        apply_logging_from_settings(settings=custom_settings)

        # 验证 get_settings 没有被调用
        mock_get_settings.assert_not_called()
        # 验证 configure_logger 被调用
        mock_configure.assert_called_once()

    @patch("insightengine.utils.log.configure_logger")
    def test_apply_passes_all_settings_to_configure_logger(self, mock_configure):
        """测试所有 settings 字段都传递给 configure_logger。"""
        settings = Settings(
            log_name="full_test",
            log_console_level="DEBUG",
            log_file_level="INFO",
            log_dir="/full/logs",
            log_rotation="100 MB",
            log_retention="60 days",
            log_compression="tar.gz",
            log_backtrace=False,
            log_diagnose=True,
            log_serialize=True,
            log_intercept_stdlib=False,
        )

        apply_logging_from_settings(settings)

        call_kwargs = mock_configure.call_args[1]

        assert call_kwargs["name"] == "full_test"
        assert call_kwargs["console_level"] == "DEBUG"
        assert call_kwargs["file_level"] == "INFO"
        assert call_kwargs["log_dir"] == "/full/logs"
        assert call_kwargs["rotation"] == "100 MB"
        assert call_kwargs["retention"] == "60 days"
        assert call_kwargs["compression"] == "tar.gz"
        assert call_kwargs["backtrace"] is False
        assert call_kwargs["diagnose"] is True
        assert call_kwargs["serialize"] is True
        assert call_kwargs["intercept_stdlib"] is False


class TestLogConfigIntegration:
    """config.log 模块的集成测试。"""

    @patch("insightengine.utils.log.configure_logger")
    def test_end_to_end_flow(self, mock_configure):
        """测试从环境变量到日志配置的完整流程。"""
        with patch.dict(
            os.environ,
            {
                "INSIGHTENGINE_LOG_NAME": "e2e_test",
                "INSIGHTENGINE_LOG_CONSOLE_LEVEL": "ERROR",
                "INSIGHTENGINE_LOG_FILE_LEVEL": "WARNING",
                "INSIGHTENGINE_LOG_DIR": "/e2e/logs",
            },
        ):
            # 创建带环境变量的 settings
            settings = Settings()

            # 应用日志配置
            apply_logging_from_settings(settings)

            # 验证配置正确传递
            call_kwargs = mock_configure.call_args[1]
            assert call_kwargs["name"] == "e2e_test"
            assert call_kwargs["console_level"] == "ERROR"
            assert call_kwargs["file_level"] == "WARNING"
            assert call_kwargs["log_dir"] == "/e2e/logs"

    @patch("insightengine.utils.log.configure_logger")
    def test_idempotent_configuration(self, mock_configure):
        """测试配置可以多次调用（幂等性）。"""
        settings = Settings(log_name="idempotent_test")

        # 多次调用
        apply_logging_from_settings(settings)
        apply_logging_from_settings(settings)
        apply_logging_from_settings(settings)

        # 验证每次都调用了 configure_logger
        assert mock_configure.call_count == 3

        # 验证每次调用的参数都相同
        for call_obj in mock_configure.call_args_list:
            assert call_obj[1]["name"] == "idempotent_test"
