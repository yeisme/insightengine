"""测试 text_utils 模块的文本处理工具函数。"""

import io
import tempfile
from pathlib import Path

import pytest

from insightengine.services.parser.base import ParserError
from insightengine.services.parser.text_utils import (
    build_items_from_chunks,
    iter_normalized_chunks,
    normalize_whitespace,
    read_text_source,
    split_into_paragraphs,
)


class TestNormalizeWhitespace:
    """测试 normalize_whitespace 函数。"""

    def test_single_space(self):
        """测试正常的单个空格保持不变。"""
        assert normalize_whitespace("hello world") == "hello world"

    def test_multiple_spaces(self):
        """测试多个空格折叠为一个。"""
        assert normalize_whitespace("hello    world") == "hello world"

    def test_tabs_and_newlines(self):
        """测试制表符和换行符折叠为单个空格。"""
        assert normalize_whitespace("hello\t\n\nworld") == "hello world"

    def test_leading_trailing_whitespace(self):
        """测试去除首尾空白。"""
        assert normalize_whitespace("  hello world  ") == "hello world"

    def test_mixed_whitespace(self):
        """测试混合空白字符。"""
        assert normalize_whitespace("  hello  \t\n  world  \r\n") == "hello world"

    def test_empty_string(self):
        """测试空字符串。"""
        assert normalize_whitespace("") == ""

    def test_only_whitespace(self):
        """测试纯空白字符串。"""
        assert normalize_whitespace("   \t\n\r   ") == ""


class TestSplitIntoParagraphs:
    """测试 split_into_paragraphs 函数。"""

    def test_single_paragraph(self):
        """测试单个段落。"""
        text = "This is a single paragraph."
        result = split_into_paragraphs(text)
        assert result == ["This is a single paragraph."]

    def test_multiple_paragraphs(self):
        """测试多个段落（用双换行分隔）。"""
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        result = split_into_paragraphs(text)
        assert len(result) == 3
        assert result[0] == "First paragraph."
        assert result[1] == "Second paragraph."
        assert result[2] == "Third paragraph."

    def test_with_windows_line_endings(self):
        """测试 Windows 风格的换行符。"""
        text = "First paragraph.\r\n\r\nSecond paragraph."
        result = split_into_paragraphs(text)
        assert len(result) == 2
        assert result[0] == "First paragraph."
        assert result[1] == "Second paragraph."

    def test_mixed_line_endings(self):
        """测试混合的换行符。"""
        text = "First.\r\n\nSecond.\n\r\nThird."
        result = split_into_paragraphs(text)
        assert len(result) == 3

    def test_extra_whitespace(self):
        """测试段落间有额外空白。"""
        text = "First.\n\n\n\nSecond."
        result = split_into_paragraphs(text)
        assert len(result) == 2
        assert result[0] == "First."
        assert result[1] == "Second."

    def test_empty_paragraphs_filtered(self):
        """测试空段落被过滤。"""
        text = "First.\n\n   \n\nSecond."
        result = split_into_paragraphs(text)
        assert len(result) == 2
        assert result == ["First.", "Second."]

    def test_whitespace_normalized(self):
        """测试段落内的空白被规范化。"""
        text = "First  paragraph   with   spaces.\n\nSecond\t\tparagraph."
        result = split_into_paragraphs(text)
        assert result[0] == "First paragraph with spaces."
        assert result[1] == "Second paragraph."


class TestReadTextSource:
    """测试 read_text_source 函数。"""

    def test_read_from_string(self):
        """测试从字符串读取。"""
        text, path = read_text_source("Hello world")
        assert text == "Hello world"
        assert path is None

    def test_read_from_bytes(self):
        """测试从字节读取（UTF-8）。"""
        text, path = read_text_source(b"Hello world")
        assert text == "Hello world"
        assert path is None

    def test_read_from_bytearray(self):
        """测试从 bytearray 读取。"""
        text, path = read_text_source(bytearray(b"Hello world"))
        assert text == "Hello world"
        assert path is None

    def test_read_from_file_path_string(self):
        """测试从文件路径字符串读取。"""
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", delete=False, suffix=".txt"
        ) as f:
            f.write("File content")
            temp_path = f.name

        try:
            text, path = read_text_source(temp_path)
            assert text == "File content"
            assert path == temp_path
        finally:
            Path(temp_path).unlink()

    def test_read_from_path_object(self):
        """测试从 Path 对象读取。"""
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", delete=False, suffix=".txt"
        ) as f:
            f.write("Path content")
            temp_path = Path(f.name)

        try:
            text, path = read_text_source(temp_path)
            assert text == "Path content"
            assert str(temp_path) == path
        finally:
            temp_path.unlink()

    def test_read_from_text_io(self):
        """测试从文本 IO 对象读取。"""
        buffer = io.StringIO("StringIO content")
        text, path = read_text_source(buffer)
        assert text == "StringIO content"
        assert path is None

    def test_read_from_bytes_io(self):
        """测试从字节 IO 对象读取。"""
        buffer = io.BytesIO(b"BytesIO content")
        text, path = read_text_source(buffer)
        assert text == "BytesIO content"
        assert path is None

    def test_read_utf8_with_bom(self):
        """测试读取带 BOM 的 UTF-8 文件。"""
        text, path = read_text_source(b"\xef\xbb\xbfHello")
        assert text == "Hello"

    def test_read_latin1_encoding(self):
        """测试读取 Latin-1 编码的内容。"""
        # é 在 Latin-1 中是 \xe9
        text, path = read_text_source(b"Caf\xe9")
        assert "Caf" in text  # 至少部分内容能读取

    def test_unsupported_source_type(self):
        """测试不支持的源类型。"""
        with pytest.raises(ParserError, match="unsupported source type"):
            read_text_source(12345)

    def test_unsupported_file_like_object(self):
        """测试不支持的 file-like 对象。"""

        class BadFileObject:
            def read(self):
                return 12345  # 返回错误类型

        with pytest.raises(
            ParserError, match="unsupported file-like object"
        ):
            read_text_source(BadFileObject())

    def test_nonexistent_file_path(self):
        """测试不存在的文件路径。"""
        with pytest.raises(
            ParserError, match="must be an existing file path"
        ):
            read_text_source("/nonexistent/file/path.txt")


class TestIterNormalizedChunks:
    """测试 iter_normalized_chunks 函数。"""

    def test_normalize_and_filter(self):
        """测试规范化并过滤空块。"""
        chunks = ["  hello  ", "  ", "world", "\t\n", "  test  "]
        result = list(iter_normalized_chunks(chunks))
        assert result == ["hello", "world", "test"]

    def test_empty_input(self):
        """测试空输入。"""
        result = list(iter_normalized_chunks([]))
        assert result == []

    def test_all_empty_chunks(self):
        """测试所有块都是空白。"""
        chunks = ["  ", "\t\n", "   "]
        result = list(iter_normalized_chunks(chunks))
        assert result == []


class TestBuildItemsFromChunks:
    """测试 build_items_from_chunks 函数。"""

    def test_basic_items(self):
        """测试基本的 items 构建。"""
        chunks = ["First chunk", "Second chunk", "Third chunk"]
        items = build_items_from_chunks(chunks)

        assert len(items) == 3
        assert items[0].id == "chunk-1"
        assert items[0].text == "First chunk"
        assert items[0].position == 1
        assert items[1].id == "chunk-2"
        assert items[1].position == 2
        assert items[2].id == "chunk-3"
        assert items[2].position == 3

    def test_custom_start_index(self):
        """测试自定义起始索引。"""
        chunks = ["First", "Second"]
        items = build_items_from_chunks(chunks, start_index=10)

        assert items[0].position == 10
        assert items[1].position == 11

    def test_with_metadata_factory(self):
        """测试使用 metadata_factory。"""
        chunks = ["First", "Second"]

        def meta_factory(idx, chunk):
            return {"index": idx, "length": len(chunk)}

        items = build_items_from_chunks(chunks, metadata_factory=meta_factory)

        assert items[0].metadata["index"] == 1
        assert items[0].metadata["length"] == 5
        assert items[1].metadata["index"] == 2
        assert items[1].metadata["length"] == 6

    def test_text_length_calculated(self):
        """测试文本长度自动计算。"""
        chunks = ["Short", "Much longer text"]
        items = build_items_from_chunks(chunks)

        assert items[0].length == 5
        assert items[1].length == 16

    def test_empty_chunks_list(self):
        """测试空的 chunks 列表。"""
        items = build_items_from_chunks([])
        assert items == []

    def test_id_generation(self):
        """测试 ID 生成。"""
        chunks = ["A", "B", "C"]
        items = build_items_from_chunks(chunks)

        assert items[0].id == "chunk-1"
        assert items[1].id == "chunk-2"
        assert items[2].id == "chunk-3"

    def test_position_sequential(self):
        """测试位置是连续的。"""
        chunks = ["A", "B", "C", "D"]
        items = build_items_from_chunks(chunks, start_index=5)

        positions = [item.position for item in items]
        assert positions == [5, 6, 7, 8]
