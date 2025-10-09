"""测试 parser 注册表功能。"""

import pytest

from insightengine.services.parser.base import Parser
from insightengine.services.parser.registry import (
    ParserRegistry,
    get_parser,
    register_parser,
)
from insightengine.services.parser.types import ParseResult


class DummyParser(Parser):
    """用于测试的虚拟 Parser。"""

    name = "dummy"

    def parse(self, source, **opts):
        return ParseResult(
            items=[],
            source=str(source),
            metadata={"parser": self.name},
        )


class AnotherParser(Parser):
    """另一个用于测试的 Parser。"""

    name = "another"

    def __init__(self, custom_option=None):
        self.custom_option = custom_option

    def parse(self, source, **opts):
        return ParseResult(
            items=[],
            metadata={"custom_option": self.custom_option},
        )


class NotAParser:
    """不是 Parser 子类的类，用于测试类型检查。"""

    name = "invalid"


class TestParserRegistry:
    """测试 ParserRegistry 类。"""

    def test_register_and_get(self):
        """测试注册和获取 parser。"""
        registry = ParserRegistry()
        registry.register("dummy", DummyParser)

        cls = registry.get("dummy")
        assert cls is DummyParser

    def test_get_nonexistent_parser(self):
        """测试获取不存在的 parser。"""
        registry = ParserRegistry()
        cls = registry.get("nonexistent")
        assert cls is None

    def test_register_non_parser_class(self):
        """测试注册非 Parser 子类应该失败。"""
        registry = ParserRegistry()

        with pytest.raises(TypeError, match="must subclass Parser"):
            registry.register("invalid", NotAParser)  # type: ignore

    def test_create_parser_instance(self):
        """测试通过注册表创建 parser 实例。"""
        registry = ParserRegistry()
        registry.register("dummy", DummyParser)

        parser = registry.create("dummy")
        assert isinstance(parser, DummyParser)
        assert parser.name == "dummy"

    def test_create_with_kwargs(self):
        """测试创建 parser 时传递参数。"""
        registry = ParserRegistry()
        registry.register("another", AnotherParser)

        parser = registry.create("another", custom_option="test_value")
        assert isinstance(parser, AnotherParser)
        assert parser.custom_option == "test_value"

    def test_create_nonexistent_parser(self):
        """测试创建不存在的 parser 应该失败。"""
        registry = ParserRegistry()

        with pytest.raises(KeyError, match="parser not found: nonexistent"):
            registry.create("nonexistent")

    def test_overwrite_registration(self):
        """测试覆盖已存在的注册。"""
        registry = ParserRegistry()
        registry.register("test", DummyParser)
        registry.register("test", AnotherParser)  # 覆盖

        cls = registry.get("test")
        assert cls is AnotherParser


class TestModuleLevelFunctions:
    """测试模块级别的注册函数。"""

    def test_register_and_get_parser(self):
        """测试 register_parser 和 get_parser。"""
        # 注册一个测试 parser
        register_parser("test_module", DummyParser)

        # 获取实例
        parser = get_parser("test_module")
        assert isinstance(parser, DummyParser)

    def test_get_parser_with_kwargs(self):
        """测试 get_parser 传递参数。"""
        register_parser("test_another", AnotherParser)

        parser = get_parser("test_another", custom_option="value")
        assert isinstance(parser, AnotherParser)
        assert parser.custom_option == "value"

    def test_get_nonexistent_parser_fails(self):
        """测试获取不存在的 parser 失败。"""
        with pytest.raises(KeyError):
            get_parser("definitely_not_registered")
