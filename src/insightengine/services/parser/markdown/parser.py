from __future__ import annotations

from typing import Any, Optional
from urllib.parse import urljoin

import mistune
from mistune.core import BaseRenderer

from ..base import Parser
from ..registry import register_parser
from ..text_utils import build_items_from_chunks, read_text_source
from ..types import Attachment, MediaType, ParseResult


def _safe_int(value: Any) -> Optional[int]:
    """温和地尝试转换为 int，失败时返回 None。"""
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None



class MarkdownTextRenderer(BaseRenderer):
    """适配 mistune v3 的自定义渲染器，递归提取文本块和图片信息。"""
    def __init__(self, base_url: Optional[str] = None):
        super().__init__()
        self.base_url = base_url
        self.paragraphs: list[str] = []
        self.images: list[dict[str, Any]] = []

    def _extract_text(self, token, state=None) -> str:
        # 递归提取 token 中所有文本，遇到图片时调用 image 方法
        if isinstance(token, str):
            return token
        if isinstance(token, dict):
            if token.get("type") == "image":
                # 先让 image 收集附件信息
                self.image(token, state)
                # 再尽量返回可读的 alt 文本（attrs.alt / token.alt / children）
                attrs = token.get("attrs", {})
                alt = attrs.get("alt") or token.get("alt")
                if not alt and "children" in token:
                    alt = "".join(self._extract_text(c, state) for c in token.get("children", []))
                return alt or ""
            if "raw" in token:
                return token["raw"]
            if "children" in token:
                return "".join(self._extract_text(child, state) for child in token["children"])
            return ""
        if isinstance(token, list):
            return "".join(self._extract_text(child, state) for child in token)
        return ""

    # 基本文本节点
    def text(self, token, state):
        return self._extract_text(token, state)

    def emphasis(self, token, state):
        return self._extract_text(token, state)

    def strong(self, token, state):
        return self._extract_text(token, state)

    def link(self, token, state):
        return self._extract_text(token, state)

    def codespan(self, token, state):
        return self._extract_text(token, state)

    def linebreak(self, token, state):
        return " "

    def softbreak(self, token, state):
        return " "

    def inline_html(self, token, state):
        return ""

    def paragraph(self, token, state):
        text = self._extract_text(token, state).strip()
        if text:
            self.paragraphs.append(text)
        return ""

    def heading(self, token, state):
        text = self._extract_text(token, state).strip()
        if text:
            self.paragraphs.append(text)
        return ""

    def thematic_break(self, token, state):
        return ""

    def block_text(self, token, state):
        return self._extract_text(token, state)

    def block_code(self, token, state):
        code = token.get("raw", "").strip()
        if code:
            self.paragraphs.append(code)
        return ""

    def block_quote(self, token, state):
        text = self._extract_text(token, state).strip()
        if text:
            self.paragraphs.append(text)
        return ""

    def block_html(self, token, state):
        return ""

    def block_error(self, token, state):
        return ""

    def list(self, token, state):
        # 递归处理所有列表项，确保每个列表项文本被加入 self.paragraphs
        if "children" in token:
            for child in token["children"]:
                # child 通常为 list_item token
                try:
                    self.list_item(child, state)
                except Exception:
                    # 兜底：直接提取并追加文本
                    text = self._extract_text(child, state).strip()
                    if text:
                        self.paragraphs.append(text)
        return ""

    def list_item(self, token, state):
        text = self._extract_text(token, state).strip()
        if text:
            self.paragraphs.append(text)
        return ""

    def image(self, token, state):
        # 兼容不同 token 结构来提取 url/alt/title
        attrs = token.get("attrs", {}) or {}
        # 常见字段名：src / url / href
        url = attrs.get("src") or attrs.get("url") or attrs.get("href") or token.get("src") or token.get("url") or token.get("href") or ""
        # alt 可能在 attrs、token 或 children
        alt = attrs.get("alt") or token.get("alt")
        if not alt and "children" in token:
            alt = "".join(self._extract_text(c, state) for c in token.get("children", []))
        title = attrs.get("title") or token.get("title")

        if not url:
            # 没有 URL 则不作为附件收集
            return ""

        resolved_url = urljoin(str(self.base_url), url) if self.base_url else url
        image_info = {
            "url": resolved_url,
            "alt": alt or None,
            "title": title or None,
        }
        self.images.append(image_info)
        return ""

    # 表格相关
    def table(self, token, state):
        # 递归处理表格，确保每个单元格文本被加入 self.paragraphs
        if "children" in token:
            for child in token["children"]:
                try:
                    self.table_section(child, state)
                except Exception:
                    text = self._extract_text(child, state).strip()
                    if text:
                        self.paragraphs.append(text)
        return ""

    def table_section(self, token, state):
        # 处理表头/表体
        if "children" in token:
            for row in token["children"]:
                try:
                    self.table_row(row, state)
                except Exception:
                    text = self._extract_text(row, state).strip()
                    if text:
                        self.paragraphs.append(text)
        return ""

    def table_head(self, token, state):
        return self.table_section(token, state)

    def table_body(self, token, state):
        return self.table_section(token, state)

    def table_row(self, token, state):
        if "children" in token:
            for cell in token["children"]:
                try:
                    self.table_cell(cell, state)
                except Exception:
                    text = self._extract_text(cell, state).strip()
                    if text:
                        self.paragraphs.append(text)
        return ""

    def table_cell(self, token, state):
        text = self._extract_text(token, state).strip()
        if text:
            self.paragraphs.append(text)
        return ""

    # 兼容 mistune v3 可能出现的空行 token
    def blank_line(self, token, state):
        return ""


class MarkdownParser(Parser):
    """解析 Markdown 内容，输出结构化的 `ParseResult`。

    使用 mistune 库直接解析 Markdown，不经过 HTML 转换。
    """

    name = "markdown"

    def parse(self, source: Any, **opts) -> ParseResult:
        # 优先将字符串当作内容而非路径，避免误判
        from pathlib import Path
        source_path = None
        if isinstance(source, Path):
            markdown_text, source_path = read_text_source(source)
        elif isinstance(source, str):
            # 只要不是实际存在的文件就直接当内容
            path_candidate = Path(source)
            if path_candidate.exists():
                markdown_text, source_path = read_text_source(source)
            else:
                markdown_text = source
                source_path = None
        else:
            markdown_text, source_path = read_text_source(source)

        base_url = opts.get("base_url")

        # 创建自定义渲染器
        renderer = MarkdownTextRenderer(base_url=base_url)

        # 创建 Markdown 解析器
        plugins = opts.get("plugins", ["table", "strikethrough", "footnotes", "url"])
        markdown = mistune.create_markdown(renderer=renderer, plugins=plugins)

        # 解析 Markdown
        markdown(markdown_text)

        # 将段落块转换为 ParseItem 列表
        items = build_items_from_chunks(renderer.paragraphs)

        # 构建附件列表
        attachments = []
        for idx, img_info in enumerate(renderer.images, start=1):
            metadata = {}
            if img_info.get("alt"):
                metadata["alt"] = img_info["alt"]
            if img_info.get("title"):
                metadata["title"] = img_info["title"]

            attachments.append(
                Attachment(
                    id=f"img-{idx}",
                    url=img_info["url"],
                    type=MediaType.IMAGE,
                    metadata=metadata,
                )
            )

        # 构建结果元数据
        metadata_payload = {"parser": self.name, "content_type": "text/markdown"}
        extra_metadata = opts.get("metadata", {})
        metadata_payload.update(extra_metadata)

        return ParseResult(
            source=source_path,
            items=items,
            attachments=attachments,
            metadata=metadata_payload,
        )


register_parser(MarkdownParser.name, MarkdownParser)

__all__ = ["MarkdownParser"]
