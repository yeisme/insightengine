from __future__ import annotations

from typing import Any, Optional, Sequence
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import markdown as md

from ..base import Parser
from ..registry import register_parser
from ..text_utils import (
    build_items_from_chunks,
    read_text_source,
    split_into_paragraphs,
)
from ..types import Attachment, MediaType, ParseResult


def _safe_int(value: Any) -> Optional[int]:
    """温和地尝试转换为 int，失败时返回 None。"""

    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


class MarkdownParser(Parser):
    """解析 Markdown 内容，输出结构化的 `ParseResult`。"""

    name = "markdown"

    def parse(self, source: Any, **opts) -> ParseResult:
        # 将输入读取为文本，同时尽量保留来源路径
        markdown_text, source_path = read_text_source(source)

        extensions: Sequence[str] = opts.get("extensions", ())
        extension_configs = opts.get("extension_configs", {})
        # 借助第三方 markdown 库先将 Markdown 转换为 HTML，再复用 HTML 解析流程
        html_text = md.markdown(
            markdown_text,
            extensions=list(extensions),
            extension_configs=extension_configs,
            output_format="html",
        )

        soup = BeautifulSoup(html_text, "html.parser")

        base_url = opts.get("base_url")

        # 与 HTML 解析器相同：优先抽取块级标签作为段落
        block_tags = (
            "p",
            "li",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "blockquote",
            "pre",
        )
        paragraphs: list[str] = []
        for tag in soup.find_all(block_tags):
            separator = "\n" if tag.name in {"pre"} else " "
            text = tag.get_text(separator, strip=True)
            if text:
                paragraphs.append(text)

        if not paragraphs:
            text_content = soup.get_text("\n", strip=True)
            paragraphs = split_into_paragraphs(text_content)

        # 将段落块转换为 ParseItem 列表
        items = build_items_from_chunks(paragraphs)

        attachments = []
        for idx, img in enumerate(soup.find_all("img"), start=1):
            src = img.get("src")
            if not src:
                continue
            # 同样使用 urljoin，并通过 str() 避免类型与类型检查冲突
            resolved_url = urljoin(str(base_url), str(src)) if base_url else str(src)
            metadata = {k: v for k, v in {"alt": img.get("alt")}.items() if v}
            attachments.append(
                Attachment(
                    id=f"img-{idx}",
                    url=resolved_url,
                    mime=str(img.get("type")) if img.get("type") else None,
                    type=MediaType.IMAGE,
                    width=_safe_int(img.get("width")),
                    height=_safe_int(img.get("height")),
                    metadata=metadata,
                )
            )

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
