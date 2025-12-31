"""Faster-whisper based transcriber for audio transcription."""

import base64
import io
import logging
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Callable
import threading

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """Result from transcription."""
    text: str
    is_final: bool
    confidence: float = 1.0


class Transcriber:
    """
    Transcriber using faster-whisper.

    Accumulates audio chunks and transcribes them in batches for efficiency.
    """

    def __init__(
        self,
        model: str = "distil-large-v3",
        device: str = "cuda",
        compute_type: str = "int8_float16",
        language: str = "en",
        beam_size: int = 1,
    ):
        self.model_name = model
        self.device = device
        self.compute_type = compute_type
        self.default_language = language
        self.beam_size = beam_size

        self.model = None
        self.is_recording = False
        self.audio_buffer: list[bytes] = []
        self.current_text = ""
        self.language = language

        self._on_transcript: Optional[Callable[[TranscriptionResult], None]] = None
        self._stop_event = threading.Event()

    def _load_model(self):
        """Lazy load the whisper model."""
        if self.model is None:
            logger.info(f"Loading faster-whisper model: {self.model_name}")
            from faster_whisper import WhisperModel
            import os

            # Auto-detect best device and compute type
            device = self.device
            compute_type = self.compute_type

            # Check if CUDA should be used
            cuda_available = False
            if device == "cuda":
                try:
                    import torch
                    if torch.cuda.is_available():
                        # Test if cuDNN actually works
                        try:
                            torch.backends.cudnn.is_available()
                            cuda_available = True
                        except Exception:
                            logger.warning("cuDNN not available")
                except Exception as e:
                    logger.warning(f"CUDA check failed: {e}")

            if device == "cuda" and not cuda_available:
                logger.warning("CUDA/cuDNN not available, falling back to CPU")
                device = "cpu"
                compute_type = "int8"
            elif device == "cpu" and compute_type in ("int8_float16", "float16"):
                # These compute types require CUDA
                logger.info("Adjusting compute_type for CPU")
                compute_type = "int8"

            logger.info(f"Using device={device}, compute_type={compute_type}")

            # Force CPU mode in environment if needed
            if device == "cpu":
                os.environ["CUDA_VISIBLE_DEVICES"] = ""

            self.model = WhisperModel(
                self.model_name,
                device=device,
                compute_type=compute_type,
            )
            logger.info("Model loaded successfully")

    def set_transcript_callback(self, callback: Callable[[TranscriptionResult], None]):
        """Set callback for real-time transcript updates."""
        self._on_transcript = callback

    def start(self, language: Optional[str] = None) -> None:
        """Start a recording session."""
        self._load_model()

        self.language = language or self.default_language
        self.is_recording = True
        self.audio_buffer = []
        self.current_text = ""
        self._stop_event.clear()

        logger.info(f"Transcriber started with language={self.language}")

    def _transcribe_audio(self, audio_bytes: bytes) -> str:
        """Transcribe audio bytes using faster-whisper."""
        if not audio_bytes or len(audio_bytes) < 1000:
            logger.warning(f"Audio too short: {len(audio_bytes)} bytes")
            return ""

        try:
            # Convert WebM/Opus to PCM using PyAV
            logger.info(f"Decoding {len(audio_bytes)} bytes of audio...")
            audio_array = self._decode_audio(audio_bytes)

            if audio_array is None:
                logger.error("Audio decode returned None")
                return ""

            if len(audio_array) < 1000:
                logger.warning(f"Decoded audio too short: {len(audio_array)} samples")
                return ""

            logger.info(f"Decoded to {len(audio_array)} samples ({len(audio_array)/16000:.1f}s), transcribing...")

            # Transcribe
            segments, info = self.model.transcribe(
                audio_array,
                language=self.language,
                beam_size=self.beam_size,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=200,
                ),
            )

            # Combine all segments
            text = " ".join(segment.text.strip() for segment in segments)
            logger.info(f"Transcribed: '{text[:100]}{'...' if len(text) > 100 else ''}")
            return text.strip()

        except Exception as e:
            logger.error(f"Transcription error: {e}", exc_info=True)
            return self.current_text

    def _decode_audio(self, audio_bytes: bytes) -> Optional[np.ndarray]:
        """Decode WebM/Opus audio to numpy array using FFmpeg (more lenient than PyAV)."""
        try:
            # Write to temp file
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
                f.write(audio_bytes)
                temp_path = f.name

            try:
                logger.info(f"Decoding WebM with FFmpeg from: {temp_path} ({len(audio_bytes)} bytes)")

                # Use FFmpeg to convert to raw PCM
                # -f webm: force input format (more lenient parsing)
                # -i: input file
                # -f f32le: output as 32-bit float little-endian
                # -ar 16000: resample to 16kHz
                # -ac 1: convert to mono
                # pipe:1: output to stdout
                result = subprocess.run(
                    [
                        "ffmpeg",
                        "-hide_banner",
                        "-loglevel", "error",
                        "-f", "webm",
                        "-i", temp_path,
                        "-f", "f32le",
                        "-ar", "16000",
                        "-ac", "1",
                        "pipe:1",
                    ],
                    capture_output=True,
                    timeout=30,
                )

                if result.returncode != 0:
                    logger.error(f"FFmpeg failed: {result.stderr.decode()}")
                    return None

                if not result.stdout:
                    logger.error("FFmpeg produced no output")
                    return None

                # Convert raw bytes to numpy array
                audio = np.frombuffer(result.stdout, dtype=np.float32)
                logger.info(f"Decoded {len(audio)} samples ({len(audio)/16000:.1f}s at 16kHz)")
                return audio

            except subprocess.TimeoutExpired:
                logger.error("FFmpeg timed out")
                return None
            except Exception as e:
                logger.error(f"FFmpeg decode failed: {e}", exc_info=True)
                return None
            finally:
                # Clean up temp file
                Path(temp_path).unlink(missing_ok=True)

        except Exception as e:
            logger.error(f"Audio decode error: {e}", exc_info=True)
            return None

    def _transcribe_audio_array(self, audio_array: np.ndarray) -> str:
        """Transcribe numpy audio array using faster-whisper."""
        if len(audio_array) < 1000:
            logger.warning(f"Audio too short: {len(audio_array)} samples")
            return ""

        try:
            logger.info(f"Transcribing {len(audio_array)} samples ({len(audio_array)/16000:.1f}s)...")

            segments, info = self.model.transcribe(
                audio_array,
                language=self.language,
                beam_size=self.beam_size,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=200,
                ),
            )

            text = " ".join(segment.text.strip() for segment in segments)
            logger.info(f"Transcription result: '{text[:100]}' ({len(text)} chars)")
            return text.strip()

        except Exception as e:
            logger.error(f"Transcription error: {e}", exc_info=True)
            return self.current_text

    def feed_audio(self, audio_bytes: bytes) -> Optional[TranscriptionResult]:
        """
        Feed audio chunk to the transcriber.

        Args:
            audio_bytes: Audio data (WebM/Opus chunks)
        """
        if not self.is_recording:
            return None

        # Accumulate raw bytes - decode all at once at the end
        self.audio_buffer.append(audio_bytes)
        logger.debug(f"Received audio chunk: {len(audio_bytes)} bytes, total chunks: {len(self.audio_buffer)}")

        return None  # Results come via callback

    def feed_audio_base64(self, audio_b64: str) -> Optional[TranscriptionResult]:
        """Feed base64-encoded audio chunk."""
        try:
            audio_bytes = base64.b64decode(audio_b64)
            return self.feed_audio(audio_bytes)
        except Exception as e:
            logger.error(f"Error decoding base64 audio: {e}")
            return None

    def stop(self) -> str:
        """Stop recording and return final transcript."""
        if not self.is_recording:
            return self.current_text

        self.is_recording = False
        self._stop_event.set()

        logger.info(f"Stopping transcription, {len(self.audio_buffer)} chunks accumulated")

        if self.audio_buffer:
            # Concatenate all raw bytes
            all_audio_bytes = b"".join(self.audio_buffer)
            logger.info(f"Total audio: {len(all_audio_bytes)} bytes")

            # Decode with FFmpeg and transcribe
            final_text = self._transcribe_audio(all_audio_bytes)
            if final_text:
                self.current_text = final_text

        logger.info(f"Final transcript: '{self.current_text}'")

        if self._on_transcript:
            self._on_transcript(TranscriptionResult(
                text=self.current_text,
                is_final=True
            ))

        return self.current_text

    def is_active(self) -> bool:
        """Check if the transcriber is currently recording."""
        return self.is_recording
