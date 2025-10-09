"""Parser 包的集成测试。

测试各个 parser 之间的集成和整体功能。
"""

import pytest

# 只导入不会引起 lxml 问题的模块
from insightengine.services.parser.types import (
    Attachment,
    MediaType,
    ParseItem,
    ParseResult,
)
from insightengine.services.parser.base import Parser, ParserError
from insightengine.services.parser.registry import get_parser, register_parser
from insightengine.services.parser.html.parser import HtmlParser
from insightengine.services.parser.markdown.parser import MarkdownParser
from insightengine.services.parser.pdf.parser import PdfParser


class TestParserPackageImports:
    """测试包级别的导入。"""

    def test_import_types(self):
        """测试可以从包中导入类型。"""
        assert Attachment is not None
        assert MediaType is not None
        assert ParseItem is not None
        assert ParseResult is not None

    def test_import_base_classes(self):
        """测试可以从包中导入基类。"""
        assert Parser is not None
        assert ParserError is not None

    def test_import_registry_functions(self):
        """测试可以从包中导入注册函数。"""
        assert get_parser is not None
        assert register_parser is not None


class TestParserRegistration:
    """测试 parser 注册机制。"""

    def test_pdf_parser_registered(self):
        """测试 PDF parser 已注册。"""
        parser = get_parser("pdf")
        assert isinstance(parser, PdfParser)

    def test_html_parser_registered(self):
        """测试 HTML parser 已注册。"""
        parser = get_parser("html")
        assert isinstance(parser, HtmlParser)

    def test_markdown_parser_registered(self):
        """测试 Markdown parser 已注册。"""
        parser = get_parser("markdown")
        assert isinstance(parser, MarkdownParser)


class TestCrossParserConsistency:
    """测试不同 parser 之间的一致性。"""

    def test_all_parsers_have_name(self):
        """测试所有 parser 都有 name 属性。"""
        parsers = ["pdf", "html", "markdown"]

        for parser_name in parsers:
            parser = get_parser(parser_name)
            assert hasattr(parser, "name")
            assert isinstance(parser.name, str)
            assert len(parser.name) > 0

    def test_all_parsers_have_parse_method(self):
        """测试所有 parser 都有 parse 方法。"""
        parsers = ["pdf", "html", "markdown"]

        for parser_name in parsers:
            parser = get_parser(parser_name)
            assert hasattr(parser, "parse")
            assert callable(parser.parse)

    def test_parse_result_structure_consistent(self):
        """测试所有 parser 返回一致的结果结构。"""
        html_parser = get_parser("html")
        md_parser = get_parser("markdown")

        html_result = html_parser.parse("<p>Test</p>")
        md_result = md_parser.parse("# Test")

        # 两个结果都应该有相同的字段
        for result in [html_result, md_result]:
            assert hasattr(result, "items")
            assert hasattr(result, "source")
            assert hasattr(result, "attachments")
            assert hasattr(result, "segments")
            assert hasattr(result, "metadata")

            assert isinstance(result.items, list)
            assert isinstance(result.attachments, list)
            assert isinstance(result.metadata, dict)


class TestParseResultValidation:
    """测试 ParseResult 的验证和一致性。"""

    def test_parse_result_items_have_required_fields(self):
        """测试 ParseItem 都有必需的字段。"""
        parser = get_parser("markdown")
        result = parser.parse("# Title\n\nParagraph text.")

        for item in result.items:
            assert hasattr(item, "id")
            assert hasattr(item, "text")
            assert hasattr(item, "length")
            assert hasattr(item, "position")
            assert isinstance(item.text, str)
            assert isinstance(item.length, int)
            assert isinstance(item.position, int)

    def test_parse_result_positions_are_sequential(self):
        """测试不同 parser 的 position 都是连续的。"""
        parsers_and_content = [
            ("html", "<p>P1</p><p>P2</p><p>P3</p>"),
            ("markdown", "# H1\n\nP1\n\nP2"),
        ]

        for parser_name, content in parsers_and_content:
            parser = get_parser(parser_name)
            result = parser.parse(content)

            if result.items:
                positions = [item.position for item in result.items]
                if positions_non_none := [p for p in positions if p is not None]:
                    # 位置应该从 1 开始
                    assert min(positions_non_none) == 1
                    # 位置应该是排序的
                    assert positions_non_none == sorted(positions_non_none)

    def test_attachment_types_consistent(self):
        """测试不同 parser 的附件类型一致。"""
        html_parser = get_parser("html")
        md_parser = get_parser("markdown")

        html_result = html_parser.parse('<img src="test.png">')
        md_result = md_parser.parse("![img](test.png)")

        for result in [html_result, md_result]:
            if result.attachments:
                for att in result.attachments:
                    assert isinstance(att, Attachment)
                    if att.type:
                        assert isinstance(att.type, MediaType)


class TestErrorHandling:
    """测试错误处理的一致性。"""

    def test_parser_error_inheritance(self):
        """测试 ParserError 是 Exception 的子类。"""
        assert issubclass(ParserError, Exception)

    def test_parser_error_can_be_raised(self):
        """测试可以抛出 ParserError。"""
        with pytest.raises(ParserError):
            raise ParserError("Test error")

    def test_parser_error_with_message(self):
        """测试 ParserError 可以携带消息。"""
        error_message = "Custom error message"
        with pytest.raises(ParserError, match=error_message):
            raise ParserError(error_message)


class TestMetadataConsistency:
    """测试 metadata 的一致性。"""

    def test_all_parsers_include_parser_name_in_metadata(self):
        """测试所有 parser 都在 metadata 中包含 parser 名称。"""
        parsers_and_content = [
            ("html", "<p>Test</p>"),
            ("markdown", "# Test"),
        ]

        for parser_name, content in parsers_and_content:
            parser = get_parser(parser_name)
            result = parser.parse(content)

            assert "parser" in result.metadata
            assert result.metadata["parser"] == parser_name

    def test_custom_metadata_preserved(self):
        """测试自定义 metadata 被保留。"""
        parser = get_parser("markdown")
        custom_meta = {"author": "Test", "version": "1.0", "tags": ["test"]}

        result = parser.parse("# Test", metadata=custom_meta)

        assert result.metadata["author"] == "Test"
        assert result.metadata["version"] == "1.0"
        assert result.metadata["tags"] == ["test"]
        # 原有的 parser 信息也应该存在
        assert result.metadata["parser"] == "markdown"


class TestEdgeCases:
    """测试边界情况。"""

    def test_empty_content_handling(self):
        """测试空内容的处理。"""
        parsers_and_content = [
            ("html", ""),
            ("markdown", ""),
            ("html", "   "),
            ("markdown", "   "),
        ]

        for parser_name, content in parsers_and_content:
            parser = get_parser(parser_name)
            result = parser.parse(content)

            # 不应该崩溃，应该返回有效结果
            assert isinstance(result, ParseResult)
            assert isinstance(result.items, list)

    def test_unicode_content_handling(self):
        """测试 Unicode 内容处理。"""
        unicode_content = "# 中文标题\n\n日本語 テスト 🎉 Emoji"

        parsers = ["html", "markdown"]

        for parser_name in parsers:
            parser = get_parser(parser_name)

            # 应该能正确处理 Unicode
            if parser_name == "html":
                content = f"<p>{unicode_content}</p>"
            else:
                content = unicode_content

            result = parser.parse(content)
            assert isinstance(result, ParseResult)

    def test_very_long_content(self):
        """测试很长的内容。"""
        # 创建一个很长的文档
        long_content = "\n\n".join([f"Paragraph {i}" for i in range(1000)])

        parser = get_parser("markdown")
        result = parser.parse(long_content)

        # 应该能处理并返回大量 items
        assert len(result.items) >= 500
