from __future__ import annotations

from enum import Enum
from typing import Any, Mapping, Optional, Sequence

from pydantic import BaseModel, Field


class MediaType(str, Enum):
    """多媒体类型枚举。"""

    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    BINARY = "binary"
    TEXT = "text"


class Attachment(BaseModel):
    """引用的附件或外部资源（例如图片、音视频、二进制附件或外部资源引用）。

    保持与老版本向后兼容：保留 `url`, `mime`, `metadata` 字段，同时增加媒体相关的可选字段。
    """

    id: Optional[str] = None
    mime: Optional[str] = None
    url: Optional[str] = None
    # 原始二进制数据（可选，通常在内存解析时使用）
    data: Optional[bytes] = None
    # 媒体类型（image/video/audio/text/binary）
    type: Optional[MediaType] = None
    # 常见媒体属性
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None  # 秒
    frame_rate: Optional[float] = None
    channels: Optional[int] = None
    # 缩略图或预览图 URL
    thumbnail_url: Optional[str] = None
    # 对于音视频或 OCR/ASR 的语言或转录文本
    language: Optional[str] = None
    transcription: Optional[str] = None
    # 置信度（0-1）
    confidence: Optional[float] = None
    metadata: Mapping[str, Any] = Field(default_factory=dict)


class BoundingBox(BaseModel):
    """图像中对象的边界框，坐标以像素或归一化坐标表示（根据 metadata 约定）。"""

    x: float
    y: float
    width: float
    height: float


class ParseItem(BaseModel):
    """解析出的单元。可以表示文本块、带时间戳的媒体片段、或对图片的检测结果等。

    设计目标：兼容原有文本解析场景，同时支持多媒体相关字段。
    """

    id: Optional[str] = None
    # 如果该单元主要是文本（例如段落、ASR 转写），则填充 text
    text: Optional[str] = None
    # 文本长度（例如 token 数或字符数），可选
    length: Optional[int] = None
    # 相对位置（例如页码、块索引等）
    position: Optional[int] = None
    # 附件/媒体引用（保留老字段名以保持兼容）
    attachments: Sequence[Attachment] = Field(default_factory=list)
    # 当此单元对应音视频片段时的时间戳（秒）
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    # 当此单元对应图片检测结果时，可包含边界框
    bbox: Optional[BoundingBox] = None
    metadata: Mapping[str, Any] = Field(default_factory=dict)


class MediaSegment(BaseModel):
    """表示来源文件中的一个媒体段落/片段（例如视频中某个时间区间或一张图片的检测结果）。"""

    id: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    text: Optional[str] = None
    attachments: Sequence[Attachment] = Field(default_factory=list)
    metadata: Mapping[str, Any] = Field(default_factory=dict)


class ParseResult(BaseModel):
    """整个文件/资源的解析结果，支持多模态输出。

    - `items` 保持为通用的解析单元（文本段/检测结果等）。
    - `segments` 专门用于音视频或其他带时间轴的媒体片段。
    - `attachments` 列出解析过程中收集到的独立资源（例如提取的图片、音频片段）。
    """

    source: Optional[str] = None
    items: Sequence[ParseItem] = Field(default_factory=list)
    segments: Sequence[MediaSegment] = Field(default_factory=list)
    attachments: Sequence[Attachment] = Field(default_factory=list)
    metadata: Mapping[str, Any] = Field(default_factory=dict)
