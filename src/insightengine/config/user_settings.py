"""用户级别配置类。

用户可以通过自定义 API Key 等信息创建配置实例,支持大模型相关配置。
主要集成 LangChain 生态,使用 OpenAI Provider(兼容性最好)。
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, SecretStr, field_validator


class UserLLMConfig(BaseModel):
    """用户级别的大模型配置。

    支持 OpenAI 及兼容 OpenAI API 格式的服务（如 Azure OpenAI、本地部署的模型等）。
    用户可以通过自定义上传 API Key 创建配置实例。
    
    为了支持多模型文件解析，应该使用支持多模型的模型。

    Examples:
        >>> # 使用 OpenAI 官方服务
        >>> config = UserLLMConfig(
        ...     api_key="sk-xxx",
        ...     model="gpt-4o"
        ... )

        >>> # 使用兼容 OpenAI 的第三方服务
        >>> config = UserLLMConfig(
        ...     api_key="custom-key",
        ...     base_url="https://api.custom-llm.com/v1",
        ...     model="custom-model-name"
        ... )

        >>> # 使用 Azure OpenAI
        >>> config = UserLLMConfig(
        ...     api_key="azure-key",
        ...     base_url="https://your-resource.openai.azure.com/",
        ...     model="gpt-4",
        ...     api_version="2024-02-01"
        ... )
    """

    # 必填：API Key
    api_key: SecretStr = Field(..., description="OpenAI API Key 或兼容服务的 API Key")

    # 可选：API Base URL（默认使用 OpenAI 官方）
    base_url: Optional[str] = Field(
        default=None,
        description="API 基础 URL。留空则使用 OpenAI 官方 API，也可指向兼容 OpenAI 的服务",
    )

    # 模型名称
    model: str = Field(
        default="gpt-4o-mini",
        description="模型名称，如 gpt-4o, gpt-4o-mini, gpt-3.5-turbo 等",
    )

    # 温度参数（控制随机性）
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="采样温度，范围 [0, 2]。越高越随机，越低越确定",
    )

    # 最大 tokens
    max_tokens: Optional[int] = Field(
        default=None, gt=0, description="生成的最大 token 数量。留空则使用模型默认值"
    )

    # 超时设置（秒）
    timeout: Optional[int] = Field(
        default=60, gt=0, description="API 请求超时时间（秒）"
    )

    # 最大重试次数
    max_retries: int = Field(
        default=2, ge=0, description="API 请求失败时的最大重试次数"
    )

    # API 版本（主要用于 Azure OpenAI）
    api_version: Optional[str] = Field(
        default=None, description="API 版本（Azure OpenAI 必填，如 '2024-02-01'）"
    )

    # 组织 ID（可选）
    organization: Optional[str] = Field(
        default=None, description="OpenAI 组织 ID（可选）"
    )

    # 自定义 HTTP 头
    default_headers: Optional[dict[str, str]] = Field(
        default=None, description="自定义 HTTP 请求头"
    )

    # 流式输出
    streaming: bool = Field(default=False, description="是否使用流式输出")

    @field_validator("model")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """验证模型名称不为空。"""
        if not v or not v.strip():
            raise ValueError("模型名称不能为空")
        return v.strip()

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: Optional[str]) -> Optional[str]:
        """验证并规范化 base_url。"""
        if v is not None:
            v = v.strip()
            if not v:
                return None
            # 确保 URL 不以 / 结尾（LangChain 会自动添加）
            return v.rstrip("/")
        return v

    def get_langchain_chat_model(self):
        """创建并返回 LangChain ChatOpenAI 实例。

        Returns:
            ChatOpenAI: 配置好的 LangChain ChatOpenAI 模型实例

        Examples:
            >>> config = UserLLMConfig(api_key="sk-xxx")
            >>> llm = config.get_langchain_chat_model()
            >>> response = llm.invoke("Hello, how are you?")
        """
        from langchain_openai import ChatOpenAI

        # 构建参数字典
        params: dict[str, Any] = {
            "model": self.model,
            "temperature": self.temperature,
            "api_key": self.api_key.get_secret_value(),
            "max_retries": self.max_retries,
            "streaming": self.streaming,
        }

        # 添加可选参数
        if self.base_url:
            params["base_url"] = self.base_url
        if self.max_tokens:
            params["max_tokens"] = self.max_tokens
        if self.timeout:
            params["timeout"] = self.timeout
        if self.organization:
            params["organization"] = self.organization
        if self.default_headers:
            params["default_headers"] = self.default_headers

        # Azure OpenAI 特殊处理
        if self.api_version:
            params["api_version"] = self.api_version
            # Azure 需要设置 azure_endpoint（与 base_url 相同）
            if self.base_url:
                params["azure_endpoint"] = self.base_url

        return ChatOpenAI(**params)

    def get_langchain_embeddings(self, model: Optional[str] = None):
        """创建并返回 LangChain OpenAI Embeddings 实例。

        Args:
            model: 嵌入模型名称，默认使用 text-embedding-3-small

        Returns:
            OpenAIEmbeddings: 配置好的 LangChain OpenAI Embeddings 实例

        Examples:
            >>> config = UserLLMConfig(api_key="sk-xxx")
            >>> embeddings = config.get_langchain_embeddings()
            >>> vectors = embeddings.embed_documents(["Hello", "World"])
        """
        from langchain_openai import OpenAIEmbeddings

        embedding_model = model or "text-embedding-3-small"

        # 构建参数字典
        params: dict[str, Any] = {
            "model": embedding_model,
            "api_key": self.api_key.get_secret_value(),
            "max_retries": self.max_retries,
        }

        # 添加可选参数
        if self.base_url:
            params["base_url"] = self.base_url
        if self.timeout:
            params["timeout"] = self.timeout
        if self.organization:
            params["organization"] = self.organization
        if self.default_headers:
            params["default_headers"] = self.default_headers

        return OpenAIEmbeddings(**params)

    def model_dump_safe(self) -> dict:
        """安全地导出配置（隐藏敏感信息）。

        Returns:
            dict: 配置字典，API Key 会被脱敏
        """
        data = self.model_dump()
        # 脱敏 API Key - 先获取实际值
        key_value = self.api_key.get_secret_value()
        if len(key_value) > 8:
            data["api_key"] = f"{key_value[:4]}...{key_value[-4:]}"
        else:
            data["api_key"] = "***"
        return data


class UserConfig(BaseModel):
    """用户配置的顶层容器。

    包含用户级别的所有配置，目前主要是大模型配置。
    未来可以扩展其他用户自定义配置。

    Examples:
        >>> llm_config = UserLLMConfig(api_key=SecretStr("sk-xxx"))
        >>> user_config = UserConfig(
        ...     user_id="user123",
        ...     llm_config=llm_config
        ... )
    """

    user_id: str = Field(..., description="用户唯一标识")

    llm_config: Optional[UserLLMConfig] = Field(default=None, description="大模型配置")

    # 未来可扩展其他配置
    # vector_config: Optional[VectorConfig] = None
    # crawler_config: Optional[CrawlerConfig] = None

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """验证用户 ID 不为空。"""
        if not v or not v.strip():
            raise ValueError("用户 ID 不能为空")
        return v.strip()


__all__ = ["UserLLMConfig", "UserConfig"]
