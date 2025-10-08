from __future__ import annotations

from typing import Any, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..base import Parser, ParserError
from ..registry import register_parser
from ..text_utils import (
    build_items_from_chunks,
    read_text_source,
    split_into_paragraphs,
)
from ..types import Attachment, MediaType, ParseResult


def _safe_int(value: Any) -> Optional[int]:
    """尝试将任意值转换为 int。

    BeautifulSoup 提取的属性通常是字符串或 None。为了稳健地把 width/height
    之类的值转成整数，使用此辅助函数：当输入为 None、无法转换或类型错误时
    返回 None，这样调用方可安全地将其传入 Attachment。
    """
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


class HtmlParser(Parser):
    """解析 HTML 文档并抽取结构化文本与附件（图片等）。

    行为简介：
    - 从输入读取文本与可选的源路径（通过 read_text_source）
    - 使用 BeautifulSoup 解析 HTML（可通过 opts 覆盖解析后端）
    - 从 <base> 标签或 opts 中推断 base_url，用于解析相对资源 URL
    - 将块级元素合并为段落列表，再把段落切分为 items
    - 抽取 <img> 标签并构建 Attachment 对象返回
    """

    name = "html"

    def parse(self, source: Any, **opts) -> ParseResult:
        # 读取输入源（可能是文件路径、字符串或 file-like 对象），
        # 返回原始文本与解析出来的 source_path 用于追踪来源。
        html_text, source_path = read_text_source(source)

        # 允许通过 opts 覆盖默认的 BeautifulSoup 解析后端（如 'lxml'）
        parser_backend = opts.get("html_parser", "html.parser")
        try:
            soup = BeautifulSoup(html_text, parser_backend)
        except Exception as exc:  # pragma: no cover - BeautifulSoup 很少会抛出包装错误
            # 将解析错误统一为 ParserError，便于上层统一处理
            raise ParserError(f"failed to parse HTML: {exc}") from exc

        # 推断页面的 base URL，用于将相对路径解析为绝对 URL：
        # - 优先使用 opts 中的 'base_url'
        # - 否则尝试从 <base href="..."> 标签读取
        base_url = opts.get("base_url")
        if base_url is None:
            base_tag = soup.find("base")
            if base_tag is not None:
                base_href = base_tag.get("href")
                if base_href:
                    base_url = base_href

        # 定义作为“块级文本”的标签集合，优先从这些标签抽取段落。
        # 对于 <pre> 保留换行符，其他块内用空格连接。
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
            # get_text 会递归拼接子节点文本；strip=True 会去除首尾空白
            text = tag.get_text(separator, strip=True)
            if text:
                paragraphs.append(text)

        # 如果没有找到任何块级标签的文本，退回到整个文档的文本并按段落分割
        if not paragraphs:
            text_content = soup.get_text("\n", strip=True)
            paragraphs = split_into_paragraphs(text_content)

        # 将段落块转换为最终的 items（可能包含分段、id 等元信息）
        items = build_items_from_chunks(paragraphs)

        # 抽取图片资源作为附件（Attachment）
        attachments = []
        for idx, img in enumerate(soup.find_all("img"), start=1):
            # 读取 src 属性；若不存在则跳过
            src = img.get("src")
            if not src:
                continue

            # 注意：BeautifulSoup 返回的属性类型可能不是纯 str（例如特殊包装类型），
            # 并且 urllib.parse.urljoin 的签名对 AnyStr 有严格类型约束。为避免类型检查
            # 报错并保证运行时行为正确，这里将 base_url 和 src 明确转换为 str。
            # 运行时通常 base_url 为 None 或字符串；如果是 bytes/其它类型，需要额外处理。
            resolved_url = urljoin(str(base_url), str(src)) if base_url else str(src)

            # 仅收集存在的元信息（例如 alt 文本）
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

        # 构建返回时的元数据载荷，允许外部通过 opts 追加或覆盖
        metadata_payload = {"parser": self.name, "content_type": "text/html"}
        extra_metadata = opts.get("metadata", {})
        metadata_payload.update(extra_metadata)

        return ParseResult(
            source=source_path,
            items=items,
            attachments=attachments,
            metadata=metadata_payload,
        )


register_parser(HtmlParser.name, HtmlParser)

__all__ = ["HtmlParser"]
