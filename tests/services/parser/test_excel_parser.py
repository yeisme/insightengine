"""测试 Excel parser。

由于创建真实的 Excel 文件需要复杂的依赖，这些测试主要验证接口和错误处理。
"""

import pytest


class TestExcelParser:
    """测试 ExcelParser 类。"""

    @pytest.fixture
    def parser(self):
        """返回 ExcelParser 实例。"""
        from insightengine.services.parser.excel.parser import ExcelParser
        
        return ExcelParser()

    def test_parser_name(self, parser):
        """测试 parser 名称。"""
        assert parser.name == "excel"

    def test_parse_interface_exists(self, parser):
        """测试 parse 方法存在。"""
        assert hasattr(parser, "parse")
        assert callable(parser.parse)
