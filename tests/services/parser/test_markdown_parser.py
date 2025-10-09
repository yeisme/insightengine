import pytest
from insightengine.services.parser.markdown.parser import MarkdownParser
from insightengine.services.parser.types import Attachment, MediaType, ParseResult


class TestMarkdownParser:
    @pytest.fixture
    def parser(self):
        return MarkdownParser()

    def test_parse_heading_and_paragraph(self, parser):
        md = """# 一级标题\n\n段落内容。"""
        result = parser.parse(md)
        assert isinstance(result, ParseResult)
        texts = [item.text for item in result.items if item.text is not None]
        assert any("一级标题" in t for t in texts)
        assert any("段落内容" in t for t in texts)

    def test_parse_code_block(self, parser):
        md = """```python\nprint('hello')\n```"""
        result = parser.parse(md)
        texts = [item.text for item in result.items if item.text is not None]
        assert any("print('hello')" in t for t in texts)

    def test_parse_list(self, parser):
        md = """- 项目一\n- 项目二\n- 项目三"""
        result = parser.parse(md)
        texts = [item.text for item in result.items if item.text is not None]
        assert any("项目一" in t for t in texts)
        assert any("项目三" in t for t in texts)

    def test_parse_image_attachment(self, parser):
        md = """![alt文本](img.png "标题")"""
        result = parser.parse(md)
        assert result.attachments
        att = result.attachments[0]
        assert isinstance(att, Attachment)
        assert att.url and att.url.endswith("img.png")
        assert att.type == MediaType.IMAGE
        assert att.metadata.get("alt") == "alt文本"
        assert att.metadata.get("title") == "标题"

    def test_parse_table(self, parser):
        md = """| 列1 | 列2 |\n| --- | --- |\n| a   | b   |"""
        result = parser.parse(md)
        texts = [item.text for item in result.items if item.text is not None]
        assert any("列1" in t for t in texts)
        assert any("a" in t for t in texts)

    def test_empty_content(self, parser):
        result = parser.parse("")
        assert isinstance(result, ParseResult)
        assert result.items == [] or all(
            (item.text is None or not item.text.strip()) for item in result.items
        )

    def test_unicode_content(self, parser):
        md = "# 标题\n\n内容 with emoji 🎉 和多语言：日本語"
        result = parser.parse(md)
        texts = [item.text for item in result.items if item.text is not None]
        assert any("🎉" in t for t in texts)
        assert any("日本語" in t for t in texts)

    def test_custom_metadata(self, parser):
        md = "# test"
        meta = {"author": "A", "tags": ["t"]}
        result = parser.parse(md, metadata=meta)
        assert result.metadata["author"] == "A"
        assert result.metadata["tags"] == ["t"]
        assert result.metadata["parser"] == "markdown"

    def test_base_url_for_image(self, parser):
        md = "![img](pic.jpg)"
        result = parser.parse(md, base_url="http://a.com/docs/")
        assert result.attachments
        att = result.attachments[0]
        assert att.url and att.url.startswith("http://a.com/")

    def test_items_position_and_length(self, parser):
        md = "# H1\n\nP1\n\nP2"
        result = parser.parse(md)
        positions = [item.position for item in result.items]
        assert positions == sorted(positions)
        for item in result.items:
            assert isinstance(item.length, int)
            if item.text is not None:
                assert item.length == len(item.text)
