from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Iterable, Iterator, Sequence

from .base import ParserError

if TYPE_CHECKING:  # pragma: no cover - 仅用于类型检查的导入
    from .types import ParseItem


_WS_RE = re.compile(r"\s+")


def normalize_whitespace(value: str) -> str:
    """将连续的空白字符折叠为单个空格并去除首尾空白。"""

    return _WS_RE.sub(" ", value).strip()


def split_into_paragraphs(text: str) -> list[str]:
    """把一段文本拆分成逻辑段落。

    连续的空行视为段落分隔符；拆分后会去除空段落并规范化空白。
    """

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    chunks = re.split(r"\n{2,}", normalized)
    return [
        normalize_whitespace(chunk) for chunk in chunks if normalize_whitespace(chunk)
    ]


def read_text_source(source: Any, *, encoding: str = "utf-8") -> tuple[str, str | None]:
    """将 *source* 读取为字符串。

    返回 `(text, path)` 二元组，如果源自文件系统则返回解析后的路径，否则为 `None`。
    """

    if isinstance(source, Path):
        # 直接读取 Path 对象
        return _read_path(source, encoding), str(source)

    if isinstance(source, str):
        # 字符串既可能是已解码的内容，也可能是文件路径。
        # 如果字符串为空或仅包含空白，视为内容而不是路径（避免 Path('') -> Path('.') 导致错误）。
        if not source.strip():
            return "", None

        # 优先尝试当作路径
        path_candidate = Path(source)
        if path_candidate.exists():
            return _read_path(path_candidate, encoding), str(path_candidate)

        # 如果字符串看起来像一个文件路径（包含路径分隔符或有文件后缀），
        # 则应当视为路径并在不存在时抛出错误，避免把错误的路径当作内容继续处理。
        if ("/" in source) or ("\\" in source) or path_candidate.suffix:
            raise ParserError("source must be an existing file path")

        return source, None

    if isinstance(source, (bytes, bytearray)):
        # 原始字节流需要尝试多种编码解码
        return _decode_bytes(bytes(source)), None

    if hasattr(source, "read"):
        # 兼容 file-like 对象，尽可能容纳字符串或字节返回值
        data = source.read()
        if isinstance(data, (bytes, bytearray)):
            return _decode_bytes(bytes(data)), None
        if isinstance(data, str):
            return data, None
        raise ParserError(
            "unsupported file-like object; expected str or bytes from read()"
        )

    raise ParserError(f"unsupported source type: {type(source)!r}")


def _read_path(path: Path, encoding: str) -> str:
    try:
        return path.read_text(encoding=encoding)
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def _decode_bytes(data: bytes) -> str:
    # Prefer utf-8-sig so that a leading BOM is removed when present
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    # 最后一层兜底：使用替换模式确保仍能保留尽可能多的内容
    return data.decode("utf-8", errors="replace")


def iter_normalized_chunks(chunks: Iterable[str]) -> Iterator[str]:
    """遍历 *chunks*，按顺序返回去除多余空白后的非空文本片段。"""

    for chunk in chunks:
        normalized = normalize_whitespace(chunk)
        if normalized:
            yield normalized


def build_items_from_chunks(
    chunks: Sequence[str],
    *,
    start_index: int = 1,
    metadata_factory: Callable[[int, str], dict[str, Any]] | None = None,
) -> list["ParseItem"]:
    """将文本列表转换为 `ParseItem` 对象列表。

    参数说明
    -------
    chunks:
        需要处理的文本片段序列。
    start_index:
        `position` 字段起始编号，默认从 1 开始。
    metadata_factory:
        可选回调，接受 `(index, chunk)` 并返回每个条目的 metadata。
    """

    from .types import ParseItem  # Local import to avoid circular dependency

    items: list[ParseItem] = []
    position = start_index

    for idx, chunk in enumerate(chunks, start=1):
        # 在生成 ParseItem 前再次做空白规范化，确保输出一致
        text = normalize_whitespace(chunk)
        if not text:
            continue

        # 如果提供了 metadata_factory，允许调用方根据索引与文本生成额外元数据
        metadata = metadata_factory(idx, text) if metadata_factory else {}
        items.append(
            ParseItem(
                id=f"chunk-{idx}",
                text=text,
                length=len(text),
                position=position,
                metadata=metadata,
            )
        )
        position += 1

    return items
