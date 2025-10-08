from __future__ import annotations

import io
from pathlib import Path
from typing import Any, TYPE_CHECKING

from docx import Document

if TYPE_CHECKING:  # pragma: no cover - 仅用于类型检查
    from docx.document import Document as DocxDocument

from ..base import Parser, ParserError
from ..registry import register_parser
from ..text_utils import normalize_whitespace
from ..types import ParseItem, ParseResult


class DocxParser(Parser):
    """解析 Microsoft Word `.docx` 文件，输出结构化结果。"""

    name = "docx"

    def parse(self, source: Any, **opts) -> ParseResult:
        # 根据输入类型加载文档对象，同时返回可选的源路径
        document, source_path = _load_document(source)

        items = []
        position = 1

        for paragraph_index, paragraph in enumerate(document.paragraphs, start=1):
            text = normalize_whitespace(paragraph.text)
            if not text:
                continue
            items.append(
                ParseItem(
                    id=f"para-{paragraph_index}",
                    text=text,
                    length=len(text),
                    position=position,
                    metadata={"paragraph": paragraph_index},
                )
            )
            position += 1

        for table_index, table in enumerate(document.tables, start=1):
            for row_index, row in enumerate(table.rows, start=1):
                cell_text = normalize_whitespace(
                    " ".join(cell.text for cell in row.cells)
                )
                if not cell_text:
                    continue
                items.append(
                    ParseItem(
                        id=f"table-{table_index}-row-{row_index}",
                        text=cell_text,
                        length=len(cell_text),
                        position=position,
                        metadata={"table": table_index, "row": row_index},
                    )
                )
                position += 1

        metadata_payload = {
            "parser": self.name,
            "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
        extra_metadata = opts.get("metadata", {})
        metadata_payload.update(extra_metadata)

        return ParseResult(
            source=source_path,
            items=items,
            metadata=metadata_payload,
        )


def _load_document(source: Any) -> tuple["DocxDocument", str | None]:
    """根据 source 类型加载 docx 文档，并尽可能返回原始路径。"""

    if isinstance(source, Path):
        return Document(str(source)), str(source)

    if isinstance(source, str):
        path = Path(source)
        if path.exists():
            return Document(str(path)), str(path)
        raise ParserError("string source for docx must be an existing file path")

    if isinstance(source, (bytes, bytearray)):
        return Document(io.BytesIO(bytes(source))), None

    if hasattr(source, "read"):
        # 类文件对象可能返回 str 或 bytes，这里统一处理并保留名称信息
        data = source.read()
        if isinstance(data, str):
            data = data.encode("utf-8")
        if not isinstance(data, (bytes, bytearray)):
            raise ParserError("file-like object for docx must return bytes or str")
        return Document(io.BytesIO(bytes(data))), getattr(source, "name", None)

    raise ParserError(f"unsupported DOCX source type: {type(source)!r}")


register_parser(DocxParser.name, DocxParser)

__all__ = ["DocxParser"]
