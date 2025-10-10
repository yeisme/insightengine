"""insightengine.services.parser 包。

该包围绕 `Parser` 抽象类提供多种文件类型的解析器实现，负责将原始文件
（Markdown、HTML、PDF、Office、OCR/ASR 输出）拆分为段落与附件引用，生成
``insight.file.parsed.v1`` 事件。
"""

from .base import MultiModalParser, Parser, ParserError
from .registry import ParserRegistry, get_parser, register_parser
from .types import (
    Attachment,
    BoundingBox,
    MediaSegment,
    MediaType,
    ParseItem,
    ParseResult,
)

# 导入具体解析器以触发注册逻辑
from .audio import AudioParser  # noqa: F401
from .excel import ExcelParser  # noqa: F401
from .html import HtmlParser  # noqa: F401
from .markdown import MarkdownParser  # noqa: F401
from .pdf import PdfParser  # noqa: F401
from .powerpoint import PptParser, PptxParser  # noqa: F401
from .word import DocParser, DocxParser  # noqa: F401

__all__ = [
    "Attachment",
    "BoundingBox",
    "MediaSegment",
    "MediaType",
    "ParseItem",
    "ParseResult",
    "Parser",
    "MultiModalParser",
    "ParserError",
    "ParserRegistry",
    "register_parser",
    "get_parser",
    "AudioParser",
    "HtmlParser",
    "MarkdownParser",
    "PdfParser",
    "DocParser",
    "DocxParser",
    "ExcelParser",
    "PptParser",
    "PptxParser",
]
