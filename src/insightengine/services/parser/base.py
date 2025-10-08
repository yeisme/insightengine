from __future__ import annotations

import abc
from typing import Any, Callable, Optional, Dict, cast

from .types import ParseResult


class ParserError(Exception):
    """解析器通用错误类型。"""


class Parser(abc.ABC):
    """解析器接口（抽象基类）。

    最小合同：
    - parse(source, /, **opts) -> ParseResult
    - 解析器应该尽可能在失败时抛出 ParserError 或其子类。
    - 实现应保持无状态或至少线程安全（若有状态，请在文档中说明）。
    """

    name: str = "base"

    @abc.abstractmethod
    def parse(self, source: Any, **opts) -> ParseResult:
        """将输入 source 解析为 ParseResult。

        source 可以是文件路径（str）、bytes、文件句柄或已解码的字符串。
        opts 可以包含例如 `content_type`, `page`, `max_chunk_size` 等实现相关的参数。
        """


class MultiModalParser(Parser):
    """多模态解析器基类。

    实现者可以选择性地实现下面的具体方法之一或多个：
    - parse_text
    - parse_image
    - parse_audio
    - parse_video

    默认的 parse 会基于 opts['content_type']、文件扩展名或 source 的类型做简单调度。
    """

    # 默认的前缀->处理方法映射（method names）。子类可以重写或运行时通过
    # `register_media` 添加/调整项以支持更多类型。
    media_dispatch: tuple[tuple[str, str], ...] = (
        ("image", "parse_image"),
        ("video", "parse_video"),
        ("audio", "parse_audio"),
        ("text", "parse_text"),
    )

    # 文件扩展名 -> 处理方法名 映射，便于替换多重 if/elif 检查。
    extension_dispatch: Dict[str, str] = {
        # images
        ".jpg": "parse_image",
        ".jpeg": "parse_image",
        ".png": "parse_image",
        ".gif": "parse_image",
        ".bmp": "parse_image",
        ".tiff": "parse_image",
        # videos
        ".mp4": "parse_video",
        ".mov": "parse_video",
        ".avi": "parse_video",
        ".mkv": "parse_video",
        ".webm": "parse_video",
        # audios
        ".mp3": "parse_audio",
        ".wav": "parse_audio",
        ".flac": "parse_audio",
        ".aac": "parse_audio",
    }

    @classmethod
    def register_media(cls, prefix: str, method_name: str) -> None:
        """在类层面注册新的前缀->处理方法名映射。

        Example: MyParser.register_media('application/vnd.custom', 'parse_custom')
        """
        lst = list(cls.media_dispatch)
        lst.append((prefix, method_name))
        cls.media_dispatch = tuple(lst)

    def parse_text(self, source: Any, **opts) -> ParseResult:
        raise NotImplementedError()

    def parse_image(self, source: Any, **opts) -> ParseResult:
        raise NotImplementedError()

    def parse_audio(self, source: Any, **opts) -> ParseResult:
        raise NotImplementedError()

    def parse_video(self, source: Any, **opts) -> ParseResult:
        raise NotImplementedError()

    def parse(self, source: Any, **opts) -> ParseResult:
        # 首先依据 caller 提供的 content_type 做调度
        content_type = opts.get("content_type")
        if content_type:
            ct = content_type.lower()  # 忽略大小写
            # 使用类级别的 media_dispatch（prefix -> method_name），类似 switch/case。
            for prefix, method_name in self.media_dispatch:
                if ct.startswith(prefix):
                    # 从当前类实例获取对应方法
                    handler = cast(
                        Optional[Callable[..., ParseResult]],
                        getattr(self, method_name, None),
                    )
                    if handler is None:
                        continue
                    return handler(source, **opts)

        # 尝试通过文件扩展名做简单推断
        if isinstance(source, str):
            import os

            _, ext = os.path.splitext(source)
            ext = ext.lower()

            # 通过扩展名查表分发到对应的 parse_* 方法
            method_name: Optional[str] = self.extension_dispatch.get(ext)
            if method_name:
                handler = cast(
                    Optional[Callable[..., ParseResult]],
                    getattr(self, method_name, None),
                )
                if handler is not None:
                    return handler(source, **opts)

            # 默认把字符串当作文本内容或文本路径
            try:
                return self.parse_text(source, **opts)
            except NotImplementedError:
                raise ParserError(
                    "parser does not implement any suitable parse_* method; please provide content_type in opts"
                )

        # 尝试通过 source 的类型/扩展名做简单推断
        if isinstance(source, (bytes, bytearray)):
            # 无法确定字节流的具体类型，按 image->video->audio 顺序尝试
            for method_name in ("parse_image", "parse_video", "parse_audio"):
                handler = cast(
                    Optional[Callable[..., ParseResult]],
                    getattr(self, method_name, None),
                )
                if handler is None:
                    continue
                try:
                    return handler(source, **opts)
                except NotImplementedError:
                    continue
                except Exception:
                    raise

        # 如果到这里还没有返回，则无法确定类型或没有可用的 handler
        raise ParserError("Unable to infer media type; provide content_type in opts")
