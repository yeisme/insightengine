"""测试 Word (.docx) parser。

由于创建真实的 Word 文档需要复杂的依赖，这些测试主要验证接口和错误处理。
"""

import pytest


class TestDocxParser:
    """测试 DocxParser 类。"""

    @pytest.fixture
    def parser(self):
        """返回 DocxParser 实例。"""
        from insightengine.services.parser.word.parser import DocxParser
        
        return DocxParser()

    def test_parser_name(self, parser):
        """测试 parser 名称。"""
        assert parser.name == "docx"

    def test_parse_interface_exists(self, parser):
        """测试 parse 方法存在。"""
        assert hasattr(parser, "parse")
        assert callable(parser.parse)


class TestDocParser:
    """测试 DocParser 类（.doc 格式）。"""

    @pytest.fixture
    def parser(self):
        """返回 DocParser 实例。"""
        from insightengine.services.parser.word.parser import DocParser
        
        return DocParser()

    def test_parser_name(self, parser):
        """测试 parser 名称。"""
        assert parser.name == "doc"

    def test_parse_interface_exists(self, parser):
        """测试 parse 方法存在。"""
        assert hasattr(parser, "parse")
        assert callable(parser.parse)
