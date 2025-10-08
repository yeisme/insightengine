from __future__ import annotations

from typing import Optional

from .base import Parser


class ParserRegistry:
    """简单的解析器注册/查找表。

    用于在运行时注册解析器实现并通过 name 查找实例/类。
    """

    def __init__(self) -> None:
        # 使用简单的字典保存解析器名称到类的映射
        self._registry: dict[str, type[Parser]] = {}

    def register(self, name: str, cls: type[Parser]) -> None:
        # 注册时确保传入的是 Parser 的子类，避免意外类型
        if not issubclass(cls, Parser):
            raise TypeError("parser class must subclass Parser")
        self._registry[name] = cls

    def get(self, name: str) -> Optional[type[Parser]]:
        # 返回注册的 Parser 类，找不到时返回 None
        return self._registry.get(name)

    def create(self, name: str, **kwargs) -> Parser:
        # 复制一份简单的工厂逻辑，直接实例化解析器
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
    # 便捷封装：直接使用默认注册表创建解析器实例
    return _REGISTRY.create(name, **kwargs)
