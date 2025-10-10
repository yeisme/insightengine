"""测试 AudioParser，使用注入的 mock ASR executor 并创建一个假的 paddle 模块以避免依赖真实 paddle。"""

import io
import os
import struct
import sys
import tempfile
import types
import wave
import contextlib

import pytest
from typing import Any, cast


def _make_wav_bytes(
    n_frames: int = 160, nchannels: int = 1, sampwidth: int = 2, framerate: int = 16000
) -> bytes:
    """生成一个简单的 WAV 字节流（16-bit PCM）。"""
    bio = io.BytesIO()
    with wave.open(bio, "wb") as wf:
        wf.setnchannels(nchannels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(framerate)
        # 生成 n_frames 个样本（单通道），值为 0
        frames = struct.pack("<%dh" % n_frames, *([0] * n_frames))
        wf.writeframes(frames)
    return bio.getvalue()


def _make_fake_paddle_module():
    """构造一个非常轻量的 fake paddle 模块，满足 parser._estimate_signal_level 的最小需求。"""
    # 将模块视为 Any，避免静态类型检查器报错（为 ModuleType 动态添加属性）
    mod = cast(Any, types.ModuleType("paddle"))

    class _Scalar:
        def __init__(self, v):
            self._v = v

        def item(self):
            return self._v

    def to_tensor(samples, dtype=None):
        # samples 是 array('h') 或可迭代的数值，直接返回列表即可
        return list(samples)

    def abs_fn(tensor):
        return [abs(x) for x in tensor]

    def mean_fn(tensor):
        if not tensor:
            return _Scalar(0.0)
        return _Scalar(sum(tensor) / len(tensor))

    mod.to_tensor = to_tensor
    mod.abs = abs_fn
    mod.mean = mean_fn
    mod.float32 = "float32"
    return mod


@pytest.fixture
def parser(monkeypatch):
    """创建 AudioParser 的实例：

    - 在导入 parser 代码前注入 fake `paddle` 模块，避免真实依赖
    - 注入一个简单的 mock ASR executor，返回可预测的转写文本
    """
    # 在导入之前确保 sys.modules 中有 fake paddle
    fake = _make_fake_paddle_module()
    monkeypatch.setitem(sys.modules, "paddle", fake)

    # 延迟导入，确保上面的 monkeypatch 生效
    from insightengine.services.parser.audio.parser import AudioParser

    def mock_executor(audio_path, **kwargs):
        # 模拟 ASR executor，返回固定转写
        return "mock transcription"

    return AudioParser(asr_executor=mock_executor)


def test_parser_name(parser):
    assert parser.name == "audio"


class TestAudioParser:
    def test_parser_name(self, parser):
        assert parser.name == "audio"

    def test_parse_from_bytes(self, parser):
        wav = _make_wav_bytes()
        result = parser.parse_audio(wav)

        # 转写来自 mock executor
        assert len(result.items) == 1
        assert result.items[0].text == "mock transcription"
        assert result.metadata.get("parser") == "audio"
        # 附件应存在且标记为 audio/wav
        assert len(result.attachments) == 1
        assert result.attachments[0].mime == "audio/wav"

    def test_parse_from_fileobj(self, parser):
        wav = _make_wav_bytes()
        bio = io.BytesIO(wav)
        # 给 file-like 对象一个 name 属性以覆盖 source_ref
        bio.name = "in-memory.wav"

        result = parser.parse_audio(bio)

        assert len(result.items) == 1
        assert result.items[0].text == "mock transcription"
        assert result.attachments[0].mime == "audio/wav"

    def test_parse_from_path_and_cleanup(self, parser):
        wav = _make_wav_bytes()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(wav)
            f.flush()
            path = f.name

        try:
            result = parser.parse_audio(path)
            assert len(result.items) == 1
            assert result.items[0].text == "mock transcription"
            assert result.attachments[0].mime == "audio/wav"
        finally:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(path)

    def test_missing_path_raises(self, parser):
        import insightengine.services.parser.audio.parser as audio_mod

        with pytest.raises(audio_mod.ParserError):
            parser.parse_audio("/this/path/should/not/exist.wav")
