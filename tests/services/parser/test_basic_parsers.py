from __future__ import annotations

from pathlib import Path

import pytest

from insightengine.services.parser import (
    DocxParser,
    HtmlParser,
    MarkdownParser,
    PdfParser,
)


@pytest.fixture
def html_content() -> str:
    return """
    <html>
      <head><title>Example</title></head>
      <body>
        <h1>Heading</h1>
        <p>First paragraph.</p>
        <p>Second paragraph with <strong>bold</strong> text.</p>
        <img src="/static/image.png" alt="Sample" width="640" height="480" />
      </body>
    </html>
    """


def test_html_parser_extracts_blocks_and_attachments(html_content: str) -> None:
    parser = HtmlParser()
    result = parser.parse(html_content)

    texts = [item.text for item in result.items if item.text]
    assert "Heading" in texts
    assert "First paragraph." in texts
    assert any(att.url and att.url.endswith("image.png") for att in result.attachments)
    assert result.metadata["content_type"] == "text/html"


def test_markdown_parser_supports_images() -> None:
    markdown_text = """
    # Title

    Content line one.

    ![Alt text](https://example.com/pic.jpg)
    """

    parser = MarkdownParser()
    result = parser.parse(markdown_text)

    assert any(item.text == "Title" for item in result.items)
    assert any(att.url == "https://example.com/pic.jpg" for att in result.attachments)
    assert result.metadata["content_type"] == "text/markdown"


def test_docx_parser_reads_paragraphs_and_tables(tmp_path: Path) -> None:
    from docx import Document

    doc = Document()
    doc.add_heading("Docx Heading", level=1)
    doc.add_paragraph("Paragraph one.")
    table = doc.add_table(rows=1, cols=2)
    cells = table.rows[0].cells
    cells[0].text = "Cell 1"
    cells[1].text = "Cell 2"

    file_path = tmp_path / "sample.docx"
    doc.save(file_path)

    parser = DocxParser()
    result = parser.parse(file_path)

    assert len(result.items) >= 3
    table_items = [item for item in result.items if item.metadata.get("table")]
    assert table_items, "Expected at least one table-derived item"
    assert result.metadata["content_type"].startswith("application/vnd.openxmlformats")


def test_pdf_parser_handles_blank_pdf(tmp_path: Path) -> None:
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)

    file_path = tmp_path / "blank.pdf"
    with file_path.open("wb") as fh:
        writer.write(fh)

    parser = PdfParser()
    result = parser.parse(file_path)

    assert result.metadata["page_count"] == 1
    assert result.metadata["content_type"] == "application/pdf"
    assert result.items == []
