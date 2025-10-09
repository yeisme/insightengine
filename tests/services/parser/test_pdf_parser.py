"""测试 PDF parser。"""

import io
import tempfile
from pathlib import Path

import pytest

from insightengine.services.parser.base import ParserError
from insightengine.services.parser.pdf.parser import PdfParser


class TestPdfParser:
    """测试 PdfParser 类。"""

    @pytest.fixture
    def parser(self):
        """返回 PdfParser 实例。"""
        return PdfParser()

    def test_parser_name(self, parser):
        """测试 parser 名称。"""
        assert parser.name == "pdf"

    def test_parse_from_nonexistent_file(self, parser):
        """测试解析不存在的文件应该失败。"""
        with pytest.raises(ParserError, match="must be an existing file path"):
            parser.parse("/nonexistent/file.pdf")

    def test_parse_from_invalid_pdf_bytes(self, parser):
        """测试解析无效的 PDF 字节。"""
        invalid_pdf = b"Not a PDF file"
        with pytest.raises(ParserError, match="failed to read PDF"):
            parser.parse(invalid_pdf)

    def test_parse_from_bytes_io(self, parser):
        """测试从 BytesIO 解析（需要有效的 PDF）。"""
        # 创建一个最小的有效 PDF
        minimal_pdf = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000117 00000 n
trailer<</Size 4/Root 1 0 R>>
startxref
217
%%EOF"""

        result = parser.parse(io.BytesIO(minimal_pdf))
        assert result.source is None  # BytesIO 没有 source path
        assert result.metadata["parser"] == "pdf"
        assert result.metadata["content_type"] == "application/pdf"
        assert result.metadata["page_count"] == 1

    def test_parse_result_structure(self, parser):
        """测试解析结果的基本结构。"""
        minimal_pdf = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000117 00000 n
trailer<</Size 4/Root 1 0 R>>
startxref
217
%%EOF"""

        result = parser.parse(minimal_pdf)

        # 检查基本字段
        assert isinstance(result.items, list)
        assert isinstance(result.metadata, dict)
        assert "parser" in result.metadata
        assert "page_count" in result.metadata
        assert "content_type" in result.metadata

    def test_parse_with_custom_metadata(self, parser):
        """测试传递自定义 metadata。"""
        minimal_pdf = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000117 00000 n
trailer<</Size 4/Root 1 0 R>>
startxref
217
%%EOF"""

        result = parser.parse(minimal_pdf, metadata={"author": "Test Author"})

        assert result.metadata["author"] == "Test Author"
        assert result.metadata["parser"] == "pdf"

    def test_unsupported_source_type(self, parser):
        """测试不支持的源类型。"""
        with pytest.raises(ParserError, match="unsupported PDF source type"):
            parser.parse(12345)

    def test_parse_from_path_object(self, parser):
        """测试从 Path 对象解析（创建临时 PDF）。"""
        # 创建临时 PDF 文件
        minimal_pdf = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000117 00000 n
trailer<</Size 4/Root 1 0 R>>
startxref
217
%%EOF"""

        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".pdf"
        ) as f:
            f.write(minimal_pdf)
            temp_path = Path(f.name)

        try:
            result = parser.parse(temp_path)
            assert result.source == str(temp_path)
            assert result.metadata["parser"] == "pdf"
        finally:
            temp_path.unlink()

    def test_parse_from_string_path(self, parser):
        """测试从字符串路径解析。"""
        minimal_pdf = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000117 00000 n
trailer<</Size 4/Root 1 0 R>>
startxref
217
%%EOF"""

        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".pdf"
        ) as f:
            f.write(minimal_pdf)
            temp_path = f.name

        try:
            result = parser.parse(temp_path)
            assert result.source == temp_path
        finally:
            Path(temp_path).unlink()
