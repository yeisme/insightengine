"""兼容旧接口的导出模块。

该文件把原先在单一大文件中的类型与类拆分到三个文件：
- `types.py`：数据模型（Attachment, ParseItem, ParseResult 等）
- `base.py`：Parser, MultiModalParser, ParserError
- `registry.py`：ParserRegistry 与模块级注册函数

为了向后兼容，`abc.py` 仍然导出原有符号，供外部代码不改动导入路径直接使用。
"""

from __future__ import annotations

from .types import (  # noqa: F401
    MediaType,
    Attachment,
    BoundingBox,
    ParseItem,
    MediaSegment,
    ParseResult,
)
from .base import Parser, MultiModalParser, ParserError  # noqa: F401
from .registry import ParserRegistry, register_parser, get_parser  # noqa: F401
