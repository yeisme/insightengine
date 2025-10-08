from __future__ import annotations

from typing import Optional

from .base import Parser


class ParserRegistry:
    """简单的解析器注册/查找表。

    用于在运行时注册解析器实现并通过 name 查找实例/类。
    """

    def __init__(self) -> None:
        self._registry: dict[str, type[Parser]] = {}

    def register(self, name: str, cls: type[Parser]) -> None:
        if not issubclass(cls, Parser):
            raise TypeError("parser class must subclass Parser")
        self._registry[name] = cls

    def get(self, name: str) -> Optional[type[Parser]]:
        return self._registry.get(name)

    def create(self, name: str, **kwargs) -> Parser:
        cls = self.get(name)
        if cls is None:
            raise KeyError(f"parser not found: {name}")
        return cls(**kwargs)


# 模块级默认注册表
_REGISTRY = ParserRegistry()


def register_parser(name: str, cls: type[Parser]) -> None:
    """注册解析器到默认注册表。"""
    _REGISTRY.register(name, cls)


def get_parser(name: str, **kwargs) -> Parser:
    return _REGISTRY.create(name, **kwargs)
