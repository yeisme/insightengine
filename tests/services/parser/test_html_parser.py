"""测试 HTML parser。"""

import io
import tempfile
from pathlib import Path

import pytest

from insightengine.services.parser.html.parser import HtmlParser
from insightengine.services.parser.types import MediaType


class TestHtmlParser:
    """测试 HtmlParser 类。"""

    @pytest.fixture
    def parser(self):
        """返回 HtmlParser 实例。"""
        return HtmlParser()

    def test_parser_name(self, parser):
        """测试 parser 名称。"""
        assert parser.name == "html"

    def test_parse_simple_html(self, parser):
        """测试解析简单 HTML。"""
        html = "<html><body><p>Hello world</p></body></html>"
        result = parser.parse(html)

        assert len(result.items) > 0
        assert result.items[0].text == "Hello world"
        assert result.metadata["parser"] == "html"

    def test_parse_with_headers(self, parser):
        """测试解析包含标题的 HTML。"""
        html = """<html><body>
        <h1>Main Title</h1>
        <h2>Subtitle</h2>
        <p>Paragraph text</p>
        </body></html>"""

        result = parser.parse(html)

        all_text = " ".join(item.text for item in result.items)
        assert "Main Title" in all_text
        assert "Subtitle" in all_text
        assert "Paragraph text" in all_text

    def test_parse_with_multiple_paragraphs(self, parser):
        """测试解析多个段落。"""
        html = """<html><body>
        <p>First paragraph.</p>
        <p>Second paragraph.</p>
        <p>Third paragraph.</p>
        </body></html>"""

        result = parser.parse(html)

        assert len(result.items) >= 3
        texts = [item.text for item in result.items]
        assert "First paragraph." in texts
        assert "Second paragraph." in texts
        assert "Third paragraph." in texts

    def test_parse_with_lists(self, parser):
        """测试解析列表。"""
        html = """<html><body>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
            <li>Item 3</li>
        </ul>
        </body></html>"""

        result = parser.parse(html)

        all_text = " ".join(item.text for item in result.items)
        assert "Item 1" in all_text
        assert "Item 2" in all_text
        assert "Item 3" in all_text

    def test_parse_with_images(self, parser):
        """测试解析图片。"""
        html = """<html><body>
        <p>Text before image</p>
        <img src="image1.png" alt="First image">
        <p>Text between images</p>
        <img src="https://example.com/image2.jpg" width="800" height="600">
        </body></html>"""

        result = parser.parse(html)

        # 检查附件
        assert len(result.attachments) == 2
        assert result.attachments[0].type == MediaType.IMAGE
        assert result.attachments[0].url == "image1.png"
        assert result.attachments[0].metadata.get("alt") == "First image"

        assert result.attachments[1].url == "https://example.com/image2.jpg"
        assert result.attachments[1].width == 800
        assert result.attachments[1].height == 600

    def test_parse_with_base_tag(self, parser):
        """测试解析带 base 标签的 HTML。"""
        html = """<html>
        <head><base href="https://example.com/docs/"></head>
        <body>
        <img src="image.png">
        </body>
        </html>"""

        result = parser.parse(html)

        assert len(result.attachments) == 1
        assert result.attachments[0].url == "https://example.com/docs/image.png"

    def test_parse_with_base_url_option(self, parser):
        """测试通过选项传递 base_url。"""
        html = '<html><body><img src="image.png"></body></html>'
        result = parser.parse(html, base_url="https://example.com/")

        assert len(result.attachments) == 1
        assert result.attachments[0].url == "https://example.com/image.png"

    def test_base_url_option_overrides_tag(self, parser):
        """测试 base_url 选项覆盖 base 标签。"""
        html = """<html>
        <head><base href="https://old.com/"></head>
        <body><img src="image.png"></body>
        </html>"""

        result = parser.parse(html, base_url="https://new.com/")

        assert result.attachments[0].url == "https://new.com/image.png"

    def test_parse_blockquote(self, parser):
        """测试解析引用块。"""
        html = """<html><body>
        <blockquote>This is a quote.</blockquote>
        </body></html>"""

        result = parser.parse(html)

        assert len(result.items) > 0
        assert "This is a quote." in result.items[0].text

    def test_parse_pre_tag(self, parser):
        """测试解析 pre 标签（保留换行）。"""
        html = """<html><body>
        <pre>Line 1
Line 2
Line 3</pre>
        </body></html>"""

        result = parser.parse(html)

        assert len(result.items) > 0
        # Pre 标签内容应该包含换行
        text = result.items[0].text
        assert "Line 1" in text
        assert "Line 2" in text
        assert "Line 3" in text

    def test_parse_from_file_path(self, parser):
        """测试从文件路径解析。"""
        html_content = "<html><body><p>File content</p></body></html>"

        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", delete=False, suffix=".html"
        ) as f:
            f.write(html_content)
            temp_path = f.name

        try:
            result = parser.parse(temp_path)
            assert result.source == temp_path
            assert len(result.items) > 0
        finally:
            Path(temp_path).unlink()

    def test_parse_from_bytes(self, parser):
        """测试从字节解析。"""
        html_bytes = b"<html><body><p>Byte content</p></body></html>"
        result = parser.parse(html_bytes)

        assert result.source is None
        assert len(result.items) > 0

    def test_parse_from_string_io(self, parser):
        """测试从 StringIO 解析。"""
        html_io = io.StringIO("<html><body><p>StringIO content</p></body></html>")
        result = parser.parse(html_io)

        assert result.source is None
        assert len(result.items) > 0

    def test_parse_with_custom_parser_backend(self, parser):
        """测试使用自定义解析后端。"""
        html = "<html><body><p>Test</p></body></html>"

        # 使用默认的 html.parser
        result = parser.parse(html, html_parser="html.parser")
        assert len(result.items) > 0

    def test_parse_empty_html(self, parser):
        """测试解析空 HTML。"""
        html = "<html><body></body></html>"
        result = parser.parse(html)

        # 可能没有 items，但不应该出错
        assert isinstance(result.items, list)

    def test_parse_only_text(self, parser):
        """测试解析纯文本（无标签）。"""
        html = "Just plain text with no tags"
        result = parser.parse(html)

        # 应该能够提取文本
        assert len(result.items) > 0
        assert "Just plain text" in result.items[0].text

    def test_image_without_src(self, parser):
        """测试没有 src 的图片标签（应该被忽略）。"""
        html = '<html><body><img alt="No source"></body></html>'
        result = parser.parse(html)

        assert len(result.attachments) == 0

    def test_image_id_generation(self, parser):
        """测试图片 ID 生成。"""
        html = """<html><body>
        <img src="img1.png">
        <img src="img2.png">
        <img src="img3.png">
        </body></html>"""

        result = parser.parse(html)

        assert len(result.attachments) == 3
        assert result.attachments[0].id == "img-1"
        assert result.attachments[1].id == "img-2"
        assert result.attachments[2].id == "img-3"

    def test_custom_metadata(self, parser):
        """测试传递自定义 metadata。"""
        html = "<html><body><p>Test</p></body></html>"
        result = parser.parse(html, metadata={"author": "Test", "version": "1.0"})

        assert result.metadata["author"] == "Test"
        assert result.metadata["version"] == "1.0"

    def test_item_positions_sequential(self, parser):
        """测试 item 位置是连续的。"""
        html = """<html><body>
        <p>Para 1</p>
        <p>Para 2</p>
        <p>Para 3</p>
        </body></html>"""

        result = parser.parse(html)

        if result.items:
            positions = [item.position for item in result.items]
            assert positions == sorted(positions)
            assert positions[0] == 1

    def test_complex_html_structure(self, parser):
        """测试复杂的 HTML 结构。"""
        html = """<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Test Page</title>
            <base href="https://example.com/">
        </head>
        <body>
            <header>
                <h1>Main Title</h1>
                <nav>
                    <ul>
                        <li>Nav 1</li>
                        <li>Nav 2</li>
                    </ul>
                </nav>
            </header>
            <main>
                <article>
                    <h2>Article Title</h2>
                    <p>Article paragraph 1.</p>
                    <p>Article paragraph 2.</p>
                    <img src="article-image.png" width="500" alt="Article Image">
                </article>
                <aside>
                    <blockquote>A quote in sidebar.</blockquote>
                </aside>
            </main>
            <footer>
                <p>Footer text</p>
            </footer>
        </body>
        </html>"""

        result = parser.parse(html)

        # 应该能提取多个段落
        assert len(result.items) >= 5

        # 应该有一个图片附件
        assert len(result.attachments) == 1
        assert result.attachments[0].url == "https://example.com/article-image.png"

        # 检查某些关键文本
        all_text = " ".join(item.text for item in result.items)
        assert "Main Title" in all_text
        assert "Article Title" in all_text
        assert "Footer text" in all_text
