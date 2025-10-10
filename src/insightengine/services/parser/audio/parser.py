from __future__ import annotations

import contextlib
import os
import tempfile
import wave
from array import array
from pathlib import Path
from typing import Any, Callable, Optional

import paddle

from ..base import MultiModalParser, ParserError
from ..registry import register_parser
from ..types import Attachment, MediaSegment, MediaType, ParseItem, ParseResult

_ASRExecutorFactory = Callable[[], Any]


def _lazy_import_asr_executor() -> _ASRExecutorFactory:
    try:
        from paddlespeech.cli.asr.infer import ASRExecutor
    except ModuleNotFoundError as exc:  # pragma: no cover - runtime env dependent
        raise ParserError(
            "paddlespeech is required for audio parsing; install paddlespeech>=1.0.0"
        ) from exc
    return ASRExecutor


class AudioParser(MultiModalParser):
    name = "audio"

    def __init__(
        self,
        *,
        model: str = "conformer_wenetspeech",
        lang: str = "zh",
        sample_rate: int = 16000,
        decode_method: str = "attention_rescoring",
        asr_executor: Optional[Any] = None,
    ) -> None:
        self.model = model
        self.lang = lang
        self.sample_rate = sample_rate
        self.decode_method = decode_method
        self._external_executor = asr_executor
        self._executor: Optional[Any] = None

    def parse_audio(self, source: Any, **opts: Any) -> ParseResult:
        audio_path, cleanup, source_ref, raw_bytes = self._prepare_audio_source(
            source, **opts
        )
        try:
            probe = self._probe_audio(audio_path)
            transcript = self._transcribe(audio_path, **opts)
        finally:
            if cleanup is not None:
                cleanup()

        text = transcript.strip()
        items = []
        if text:
            items.append(
                ParseItem(
                    id="segment-1",
                    text=text,
                    length=len(text),
                    position=1,
                )
            )

        duration = probe.get("duration")
        segment = MediaSegment(
            id="segment-1",
            start_time=0.0 if duration is not None else None,
            end_time=duration,
            text=text or None,
            metadata={"decode_method": opts.get("decode_method", self.decode_method)},
            language=opts.get("lang", self.lang),
        )

        content_type = opts.get("content_type") or probe.get("content_type")
        attachment_metadata = {
            "channels": probe.get("channels"),
            "frame_rate": probe.get("frame_rate"),
            "signal_level": probe.get("signal_level"),
        }
        attachments = [
            Attachment(
                id="audio-original",
                mime=content_type,
                url=source_ref,
                data=raw_bytes,
                type=MediaType.AUDIO,
                duration=duration,
                metadata=attachment_metadata,
            )
        ]

        metadata_payload = {
            "parser": self.name,
            "model": opts.get("model", self.model),
            "lang": opts.get("lang", self.lang),
            "sample_rate": opts.get("sample_rate", self.sample_rate),
            "decode_method": opts.get("decode_method", self.decode_method),
            "duration": duration,
            "channels": probe.get("channels"),
            "frame_rate": probe.get("frame_rate"),
            "signal_level": probe.get("signal_level"),
            "content_type": content_type,
        }
        extra_metadata = opts.get("metadata", {})
        metadata_payload.update(extra_metadata)

        return ParseResult(
            source=source_ref,
            items=items,
            segments=[segment],
            attachments=attachments,
            metadata=metadata_payload,
        )

    def _prepare_audio_source(
        self, source: Any, **opts: Any
    ) -> tuple[str, Optional[Callable[[], None]], Optional[str], Optional[bytes]]:
        if isinstance(source, Path):
            return str(source), None, str(source), None

        if isinstance(source, str):
            path = Path(source)
            if not path.exists():
                raise ParserError("audio source path does not exist")
            return str(path), None, str(path), None

        suffix = self._infer_suffix(opts)
        cleanup = None
        raw_bytes: Optional[bytes] = None

        if isinstance(source, (bytes, bytearray)):
            raw_bytes = bytes(source)
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.write(raw_bytes)
            tmp.flush()
            tmp.close()

            def _cleanup(tmp_path: str = tmp.name) -> None:
                with contextlib.suppress(FileNotFoundError):
                    os.unlink(tmp_path)

            cleanup = _cleanup
            return tmp.name, cleanup, None, raw_bytes

        if hasattr(source, "read"):
            data = source.read()
            if isinstance(data, str):
                data = data.encode("utf-8")
            if not isinstance(data, (bytes, bytearray)):
                raise ParserError("file-like audio source must yield bytes")
            raw_bytes = bytes(data)
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.write(raw_bytes)
            tmp.flush()
            tmp.close()

            def _cleanup(tmp_path: str = tmp.name) -> None:
                with contextlib.suppress(FileNotFoundError):
                    os.unlink(tmp_path)

            cleanup = _cleanup
            name = getattr(source, "name", None)
            return tmp.name, cleanup, name, raw_bytes

        raise ParserError(f"unsupported audio source type: {type(source)!r}")

    def _infer_suffix(self, opts: dict[str, Any]) -> str:
        content_type = opts.get("content_type", "")
        if content_type:
            mapping = {
                "audio/wav": ".wav",
                "audio/x-wav": ".wav",
                "audio/mpeg": ".mp3",
                "audio/mp3": ".mp3",
                "audio/flac": ".flac",
                "audio/aac": ".aac",
            }
            suffix = mapping.get(content_type.lower())
            if suffix:
                return suffix
        return opts.get("file_extension", ".wav")

    def _probe_audio(self, path: str) -> dict[str, Any]:
        info: dict[str, Any] = {"content_type": None}
        if path.lower().endswith(".wav"):
            with contextlib.closing(wave.open(path, "rb")) as wf:
                frame_rate = wf.getframerate()
                frames = wf.getnframes()
                channels = wf.getnchannels()
                duration = frames / frame_rate if frame_rate else None
                wf.rewind()
                signal_level = self._estimate_signal_level(wf)
            info.update(
                {
                    "content_type": "audio/wav",
                    "frame_rate": frame_rate,
                    "channels": channels,
                    "duration": duration,
                    "signal_level": signal_level,
                }
            )
        return info

    def _estimate_signal_level(self, wf: wave.Wave_read) -> Optional[float]:
        if wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
            return None
        frames = wf.readframes(wf.getnframes())
        if not frames:
            return 0.0
        samples = array("h")
        samples.frombytes(frames)
        if not samples:
            return 0.0
        tensor = paddle.to_tensor(samples, dtype=paddle.float32)
        scalar = paddle.mean(paddle.abs(tensor)).item()
        if isinstance(scalar, complex):
            return None
        return float(scalar)

    def _transcribe(self, audio_path: str, **opts: Any) -> str:
        executor = self._get_executor()
        model = opts.get("model", self.model)
        lang = opts.get("lang", self.lang)
        sample_rate = opts.get("sample_rate", self.sample_rate)
        decode_method = opts.get("decode_method", self.decode_method)
        kwargs = {
            "model": model,
            "lang": lang,
            "sample_rate": sample_rate,
            "decode_method": decode_method,
            "config": opts.get("config"),
            "ckpt_path": opts.get("ckpt_path"),
            "force_yes": True,
        }
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        try:
            transcription = executor(audio_path, **kwargs)
        except TypeError:
            fallback = {k: kwargs[k] for k in ("model", "lang") if k in kwargs}
            transcription = executor(audio_path, **fallback)
        except Exception as exc:  # pragma: no cover - passes through runtime errors
            raise ParserError(f"asr execution failed: {exc}") from exc
        if not isinstance(transcription, str):
            transcription = str(transcription)
        return transcription

    def _get_executor(self) -> Any:
        if self._external_executor is not None:
            return self._external_executor
        if self._executor is None:
            factory = _lazy_import_asr_executor()
            self._executor = factory()
        return self._executor


register_parser(AudioParser.name, AudioParser)

__all__ = ["AudioParser"]
