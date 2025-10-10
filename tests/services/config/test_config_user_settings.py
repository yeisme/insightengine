"""测试用户配置模块。

测试 UserLLMConfig 和 UserConfig 的基本功能。
"""

import pytest
from pydantic import ValidationError, SecretStr

from insightengine.config.user_settings import UserConfig, UserLLMConfig


class TestUserLLMConfig:
    """测试 UserLLMConfig 类。"""

    def test_create_basic_config(self):
        """测试创建基本配置。"""
        config = UserLLMConfig(api_key=SecretStr("sk-test123456789"))

        assert config.api_key.get_secret_value() == "sk-test123456789"
        assert config.model == "gpt-4o-mini"  # 默认值
        assert config.temperature == 0.7
        assert config.base_url is None
        assert config.streaming is False

    def test_create_custom_config(self):
        """测试创建自定义配置。"""
        config = UserLLMConfig(
            api_key=SecretStr("custom-key"),
            base_url="https://api.custom.com/v1",
            model="gpt-4o",
            temperature=0.9,
            max_tokens=2000,
            timeout=120,
            streaming=True,
        )

        assert config.api_key.get_secret_value() == "custom-key"
        assert config.base_url == "https://api.custom.com/v1"
        assert config.model == "gpt-4o"
        assert config.temperature == 0.9
        assert config.max_tokens == 2000
        assert config.timeout == 120
        assert config.streaming is True

    def test_azure_openai_config(self):
        """测试 Azure OpenAI 配置。"""
        config = UserLLMConfig(
            api_key=SecretStr("azure-key"),
            base_url="https://my-resource.openai.azure.com/",
            model="gpt-4",
            api_version="2024-02-01",
        )

        assert config.api_version == "2024-02-01"
        assert (
            config.base_url == "https://my-resource.openai.azure.com"
        )  # 末尾 / 应被移除

    def test_base_url_normalization(self):
        """测试 base_url 规范化。"""
        # 移除末尾斜杠
        config1 = UserLLMConfig(
            api_key=SecretStr("key"), base_url="https://api.example.com/"
        )
        assert config1.base_url == "https://api.example.com"

        # 空字符串变为 None
        config2 = UserLLMConfig(api_key=SecretStr("key"), base_url="   ")
        assert config2.base_url is None

    def test_model_validation(self):
        """测试模型名称验证。"""
        # 空模型名称应该失败
        with pytest.raises(ValidationError) as exc_info:
            UserLLMConfig(api_key=SecretStr("key"), model="")
        assert "模型名称不能为空" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            UserLLMConfig(api_key=SecretStr("key"), model="   ")
        assert "模型名称不能为空" in str(exc_info.value)

    def test_temperature_validation(self):
        """测试温度参数验证。"""
        # 有效范围
        config1 = UserLLMConfig(api_key=SecretStr("key"), temperature=0.0)
        assert config1.temperature == 0.0

        config2 = UserLLMConfig(api_key=SecretStr("key"), temperature=2.0)
        assert config2.temperature == 2.0

        # 超出范围应该失败
        with pytest.raises(ValidationError):
            UserLLMConfig(api_key=SecretStr("key"), temperature=-0.1)

        with pytest.raises(ValidationError):
            UserLLMConfig(api_key=SecretStr("key"), temperature=2.1)

    def test_model_dump_safe(self):
        """测试安全导出配置（脱敏）。"""
        config = UserLLMConfig(
            api_key=SecretStr("sk-1234567890abcdefghij"),
            model="gpt-4o",
        )

        safe_dump = config.model_dump_safe()

        # API Key 应该被脱敏
        assert safe_dump["api_key"] == "sk-1...ghij"
        # 其他字段正常
        assert safe_dump["model"] == "gpt-4o"

    def test_model_dump_safe_short_key(self):
        """测试短 API Key 的脱敏。"""
        config = UserLLMConfig(api_key=SecretStr("short"))
        safe_dump = config.model_dump_safe()
        assert safe_dump["api_key"] == "***"


class TestUserConfig:
    """测试 UserConfig 类。"""

    def test_create_user_config(self):
        """测试创建用户配置。"""
        llm_config = UserLLMConfig(api_key=SecretStr("sk-test"))
        user_config = UserConfig(
            user_id="user123",
            llm_config=llm_config,
        )

        assert user_config.user_id == "user123"
        assert user_config.llm_config is not None
        assert user_config.llm_config.api_key.get_secret_value() == "sk-test"

    def test_user_config_without_llm(self):
        """测试创建没有 LLM 配置的用户配置。"""
        user_config = UserConfig(user_id="user456")

        assert user_config.user_id == "user456"
        assert user_config.llm_config is None

    def test_user_id_validation(self):
        """测试用户 ID 验证。"""
        # 空用户 ID 应该失败
        with pytest.raises(ValidationError) as exc_info:
            UserConfig(user_id="")
        assert "用户 ID 不能为空" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            UserConfig(user_id="   ")
        assert "用户 ID 不能为空" in str(exc_info.value)

    def test_user_id_trimming(self):
        """测试用户 ID 去除空格。"""
        user_config = UserConfig(user_id="  user789  ")
        assert user_config.user_id == "user789"
