"""测试 parser 的基础类型和数据模型。"""

# 直接从子模块导入，避免触发 __init__.py 中的 powerpoint 导入
import sys

sys.path.insert(0, "src")

from insightengine.services.parser.types import (
    Attachment,
    BoundingBox,
    MediaSegment,
    MediaType,
    ParseItem,
    ParseResult,
)


class TestMediaType:
    """测试 MediaType 枚举。"""

    def test_media_type_values(self):
        """测试 MediaType 的所有枚举值。"""
        assert MediaType.IMAGE == "image"
        assert MediaType.VIDEO == "video"
        assert MediaType.AUDIO == "audio"
        assert MediaType.BINARY == "binary"
        assert MediaType.TEXT == "text"

    def test_media_type_string_conversion(self):
        """测试 MediaType 可以作为字符串使用。"""
        assert str(MediaType.IMAGE) == "image"
        assert MediaType.IMAGE.value == "image"


class TestAttachment:
    """测试 Attachment 数据模型。"""

    def test_create_minimal_attachment(self):
        """测试创建最小的 Attachment 实例。"""
        att = Attachment()
        assert att.id is None
        assert att.mime is None
        assert att.url is None
        assert att.data is None
        assert att.type is None

    def test_create_image_attachment(self):
        """测试创建图片 Attachment。"""
        att = Attachment(
            id="img-1",
            mime="image/png",
            url="https://example.com/image.png",
            type=MediaType.IMAGE,
            width=800,
            height=600,
        )
        assert att.id == "img-1"
        assert att.mime == "image/png"
        assert att.url == "https://example.com/image.png"
        assert att.type == MediaType.IMAGE
        assert att.width == 800
        assert att.height == 600

    def test_attachment_with_binary_data(self):
        """测试包含二进制数据的 Attachment。"""
        data = b"binary content"
        att = Attachment(
            id="bin-1",
            data=data,
            type=MediaType.BINARY,
        )
        assert att.data == data
        assert att.type == MediaType.BINARY

    def test_attachment_with_metadata(self):
        """测试带有 metadata 的 Attachment。"""
        att = Attachment(
            id="img-1",
            url="https://example.com/img.jpg",
            metadata={"alt": "description", "author": "John"},
        )
        assert att.metadata["alt"] == "description"
        assert att.metadata["author"] == "John"

    def test_video_attachment_with_duration(self):
        """测试视频 Attachment。"""
        att = Attachment(
            id="video-1",
            type=MediaType.VIDEO,
            url="https://example.com/video.mp4",
            duration=120.5,
            width=1920,
            height=1080,
            frame_rate=30.0,
        )
        assert att.duration == 120.5
        assert att.frame_rate == 30.0
        assert att.width == 1920
        assert att.height == 1080

    def test_audio_attachment(self):
        """测试音频 Attachment。"""
        att = Attachment(
            id="audio-1",
            type=MediaType.AUDIO,
            url="https://example.com/audio.mp3",
            duration=180.0,
            channels=2,
            transcription="Hello world",
            language="en",
            confidence=0.95,
        )
        assert att.type == MediaType.AUDIO
        assert att.channels == 2
        assert att.transcription == "Hello world"
        assert att.language == "en"
        assert att.confidence == 0.95


class TestBoundingBox:
    """测试 BoundingBox 数据模型。"""

    def test_create_bounding_box(self):
        """测试创建 BoundingBox。"""
        bbox = BoundingBox(x=10, y=20, width=100, height=50)
        assert bbox.x == 10
        assert bbox.y == 20
        assert bbox.width == 100
        assert bbox.height == 50

    def test_bounding_box_with_confidence(self):
        """测试带置信度的 BoundingBox。"""
        bbox = BoundingBox(x=0, y=0, width=200, height=150, confidence=0.9)
        assert bbox.confidence == 0.9


class TestParseItem:
    """测试 ParseItem 数据模型。"""

    def test_create_simple_parse_item(self):
        """测试创建简单的 ParseItem。"""
        item = ParseItem(
            id="item-1",
            text="Hello world",
            length=11,
            position=1,
        )
        assert item.id == "item-1"
        assert item.text == "Hello world"
        assert item.length == 11
        assert item.position == 1

    def test_parse_item_with_metadata(self):
        """测试带 metadata 的 ParseItem。"""
        item = ParseItem(
            id="para-1",
            text="Sample paragraph",
            length=16,
            position=1,
            metadata={"paragraph": 1, "page": 2},
        )
        assert item.metadata["paragraph"] == 1
        assert item.metadata["page"] == 2

    def test_parse_item_with_attachments(self):
        """测试带附件的 ParseItem。"""
        att = Attachment(id="img-1", url="test.png")
        item = ParseItem(
            id="item-1",
            text="Text with image",
            length=15,
            position=1,
            attachments=[att],
        )
        assert len(item.attachments) == 1
        assert item.attachments[0].id == "img-1"

    def test_parse_item_with_bounding_box(self):
        """测试带边界框的 ParseItem。"""
        bbox = BoundingBox(x=10, y=20, width=100, height=50)
        item = ParseItem(
            id="item-1",
            text="Text region",
            length=11,
            position=1,
            bbox=bbox,
        )
        assert item.bbox is not None
        assert item.bbox.x == 10
        assert item.bbox.width == 100


class TestMediaSegment:
    """测试 MediaSegment 数据模型。"""

    def test_create_media_segment(self):
        """测试创建 MediaSegment。"""
        segment = MediaSegment(
            id="seg-1",
            start_time=0.0,
            end_time=5.0,
            text="Spoken text",
        )
        assert segment.id == "seg-1"
        assert segment.start_time == 0.0
        assert segment.end_time == 5.0
        assert segment.text == "Spoken text"

    def test_media_segment_with_confidence(self):
        """测试带置信度的 MediaSegment。"""
        segment = MediaSegment(
            id="seg-1",
            start_time=0.0,
            end_time=2.5,
            text="Hello",
            confidence=0.98,
            language="en",
        )
        assert segment.confidence == 0.98
        assert segment.language == "en"


class TestParseResult:
    """测试 ParseResult 数据模型。"""

    def test_create_minimal_parse_result(self):
        """测试创建最小的 ParseResult。"""
        result = ParseResult(items=[])
        assert result.items == []
        assert result.source is None
        assert result.attachments == []
        assert result.segments == []
        assert result.metadata == {}

    def test_parse_result_with_items(self):
        """测试包含 items 的 ParseResult。"""
        items = [
            ParseItem(id="1", text="First", length=5, position=1),
            ParseItem(id="2", text="Second", length=6, position=2),
        ]
        result = ParseResult(items=items, source="test.txt")
        assert len(result.items) == 2
        assert result.source == "test.txt"

    def test_parse_result_with_all_fields(self):
        """测试包含所有字段的 ParseResult。"""
        items = [ParseItem(id="1", text="Text", length=4, position=1)]
        attachments = [Attachment(id="img-1", url="test.png")]
        segments = [
            MediaSegment(id="seg-1", start_time=0.0, end_time=1.0, text="Audio")
        ]
        metadata = {"parser": "test", "page_count": 1}

        result = ParseResult(
            source="document.pdf",
            items=items,
            attachments=attachments,
            segments=segments,
            metadata=metadata,
        )

        assert result.source == "document.pdf"
        assert len(result.items) == 1
        assert len(result.attachments) == 1
        assert len(result.segments) == 1
        assert result.metadata["parser"] == "test"
        assert result.metadata["page_count"] == 1

    def test_parse_result_metadata_defaults(self):
        """测试 metadata 的默认值。"""
        result = ParseResult(items=[])
        assert isinstance(result.metadata, dict)
        assert len(result.metadata) == 0

    def test_parse_result_immutability(self):
        """测试 ParseResult 的不可变性（Pydantic 默认行为）。"""
        result = ParseResult(items=[])
        # Pydantic v2 模型默认是可变的，但我们可以测试复制
        result_copy = result.model_copy()
        assert result_copy.items == []
        assert result_copy is not result
