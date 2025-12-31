"""WebSocket message types for STT server communication."""

from dataclasses import dataclass, asdict
from typing import Literal, Optional
import json


# Client -> Server messages

@dataclass
class StartMessage:
    """Start recording session."""
    type: Literal["start"] = "start"
    language: Optional[str] = None

    def to_json(self) -> str:
        return json.dumps(asdict(self))


@dataclass
class StopMessage:
    """Stop recording and get final transcript."""
    type: Literal["stop"] = "stop"

    def to_json(self) -> str:
        return json.dumps(asdict(self))


@dataclass
class AudioMessage:
    """Audio chunk for transcription."""
    type: Literal["audio"] = "audio"
    data: str = ""  # Base64 encoded audio data

    def to_json(self) -> str:
        return json.dumps(asdict(self))


# Server -> Client messages

@dataclass
class StatusMessage:
    """Server status update."""
    type: Literal["status"] = "status"
    status: Literal["ready", "recording", "processing", "error"] = "ready"
    error: Optional[str] = None

    def to_json(self) -> str:
        d = asdict(self)
        if d["error"] is None:
            del d["error"]
        return json.dumps(d)


@dataclass
class TranscriptMessage:
    """Transcription result (interim or final)."""
    type: Literal["transcript"] = "transcript"
    text: str = ""
    isFinal: bool = False
    confidence: Optional[float] = None

    def to_json(self) -> str:
        d = asdict(self)
        if d["confidence"] is None:
            del d["confidence"]
        return json.dumps(d)


def parse_client_message(data: str) -> StartMessage | StopMessage | AudioMessage | None:
    """Parse a message from the client."""
    try:
        msg = json.loads(data)
        msg_type = msg.get("type")

        if msg_type == "start":
            return StartMessage(language=msg.get("language"))
        elif msg_type == "stop":
            return StopMessage()
        elif msg_type == "audio":
            return AudioMessage(data=msg.get("data", ""))
        else:
            return None
    except json.JSONDecodeError:
        return None
