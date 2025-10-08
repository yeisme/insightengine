from __future__ import annotations

import io
from pathlib import Path
from typing import Any, cast

from pypdf import PdfReader

from ..base import Parser, ParserError
from ..registry import register_parser
from ..text_utils import build_items_from_chunks, split_into_paragraphs
from ..types import ParseResult


class PdfParser(Parser):
    """使用 `pypdf` 的文本提取能力解析 PDF 文档。"""

    name = "pdf"

    def parse(self, source: Any, **opts) -> ParseResult:
        # 将传入的 source 标准化为 pypdf 可接受的输入形式
        pdf_source, source_path = _prepare_pdf_source(source)

        try:
            reader = PdfReader(pdf_source)
        except Exception as exc:  # pragma: no cover - 依赖外部库，难以稳定覆盖
            raise ParserError(f"failed to read PDF: {exc}") from exc

        items = []
        position = 1
        for page_index, page in enumerate(reader.pages, start=1):
            try:
                page_text = page.extract_text() or ""
            except Exception as exc:  # pragma: no cover - pypdf 仅在极端场景报错
                raise ParserError(
                    f"failed to extract text on page {page_index}: {exc}"
                ) from exc

            # 先按段落拆分；若结果为空但仍有文本，保持整页文本
            paragraphs = split_into_paragraphs(page_text) if page_text else []
            if not paragraphs and page_text.strip():
                paragraphs = [page_text]

            page_items = build_items_from_chunks(
                paragraphs,
                start_index=position,
                metadata_factory=lambda _idx, _chunk, page=page_index: {"page": page},
            )
            if page_items:
                items.extend(page_items)
                last_position = cast(int, page_items[-1].position)
                position = last_position + 1

        metadata_payload = {
            "parser": self.name,
            "page_count": len(reader.pages),
            "content_type": "application/pdf",
        }
        extra_metadata = opts.get("metadata", {})
        metadata_payload.update(extra_metadata)

        return ParseResult(
            source=source_path,
            items=items,
            metadata=metadata_payload,
        )


def _prepare_pdf_source(source: Any) -> tuple[Any, str | None]:
    """把不同类型的输入统一整理为 PdfReader 可读取的对象。"""

    if isinstance(source, Path):
        return str(source), str(source)

    if isinstance(source, str):
        path = Path(source)
        if path.exists():
            return str(path), str(path)
        raise ParserError("string source for PDF must be an existing file path")

    if isinstance(source, (bytes, bytearray)):
        return io.BytesIO(bytes(source)), None

    if hasattr(source, "read"):
        # 对 file-like 对象保留其原始引用，由 PdfReader 自行处理
        return source, getattr(source, "name", None)

    raise ParserError(f"unsupported PDF source type: {type(source)!r}")


register_parser(PdfParser.name, PdfParser)

__all__ = ["PdfParser"]
