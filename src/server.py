"""WebSocket server for STT transcription."""

import asyncio
import logging
from typing import Set

import websockets
from websockets.server import WebSocketServerProtocol

from .config import ServerConfig, TranscriberConfig, DEFAULT_SERVER_CONFIG, DEFAULT_TRANSCRIBER_CONFIG
from .message_types import (
    parse_client_message,
    StartMessage,
    StopMessage,
    AudioMessage,
    StatusMessage,
    TranscriptMessage,
)
from .transcriber import Transcriber, TranscriptionResult

logger = logging.getLogger(__name__)


class STTServer:
    """WebSocket server for speech-to-text transcription."""

    def __init__(
        self,
        server_config: ServerConfig = DEFAULT_SERVER_CONFIG,
        transcriber_config: TranscriberConfig = DEFAULT_TRANSCRIBER_CONFIG,
    ):
        self.server_config = server_config
        self.transcriber_config = transcriber_config
        self.clients: Set[WebSocketServerProtocol] = set()
        self.transcriber: Transcriber | None = None
        self._current_websocket: WebSocketServerProtocol | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    async def handle_client(self, websocket: WebSocketServerProtocol):
        """Handle a single client connection."""
        self.clients.add(websocket)
        self._current_websocket = websocket
        self._loop = asyncio.get_event_loop()
        client_id = id(websocket)
        logger.info(f"Client {client_id} connected")

        try:
            # Send ready status
            await websocket.send(StatusMessage(status="ready").to_json())

            async for raw_message in websocket:
                message = parse_client_message(raw_message)

                if message is None:
                    logger.warning(f"Unknown message from client {client_id}: {raw_message[:100]}")
                    continue

                if isinstance(message, StartMessage):
                    await self._handle_start(websocket, message)

                elif isinstance(message, StopMessage):
                    await self._handle_stop(websocket)

                elif isinstance(message, AudioMessage):
                    await self._handle_audio(websocket, message)

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} disconnected")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
            try:
                await websocket.send(StatusMessage(status="error", error=str(e)).to_json())
            except Exception:
                pass
        finally:
            self.clients.discard(websocket)
            self._current_websocket = None
            # Clean up transcriber if this client started it
            if self.transcriber and self.transcriber.is_active():
                self.transcriber.stop()
                self.transcriber = None

    async def _handle_start(self, websocket: WebSocketServerProtocol, message: StartMessage):
        """Handle start recording request."""
        logger.info(f"Starting transcription with language={message.language}")

        try:
            # Create new transcriber
            self.transcriber = Transcriber(
                model=self.transcriber_config.model,
                device=self.transcriber_config.device,
                compute_type=self.transcriber_config.compute_type,
                language=message.language or self.transcriber_config.language,
                beam_size=self.transcriber_config.beam_size,
            )

            # Set up callback for real-time updates
            def on_transcript(result: TranscriptionResult):
                if self._current_websocket and self._loop:
                    asyncio.run_coroutine_threadsafe(
                        self._send_transcript(result),
                        self._loop
                    )

            self.transcriber.set_transcript_callback(on_transcript)

            # Start transcription
            self.transcriber.start(language=message.language)

            await websocket.send(StatusMessage(status="recording").to_json())

        except Exception as e:
            logger.error(f"Error starting transcription: {e}")
            await websocket.send(StatusMessage(status="error", error=str(e)).to_json())

    async def _send_transcript(self, result: TranscriptionResult):
        """Send transcript to client."""
        if self._current_websocket:
            try:
                await self._current_websocket.send(TranscriptMessage(
                    text=result.text,
                    isFinal=result.is_final,
                ).to_json())
            except Exception as e:
                logger.error(f"Error sending transcript: {e}")

    async def _handle_stop(self, websocket: WebSocketServerProtocol):
        """Handle stop recording request."""
        logger.info("Stopping transcription")

        if not self.transcriber:
            await websocket.send(StatusMessage(status="error", error="Not recording").to_json())
            return

        try:
            await websocket.send(StatusMessage(status="processing").to_json())

            # Stop transcription (this blocks briefly for final transcription)
            final_text = self.transcriber.stop()

            await websocket.send(TranscriptMessage(
                text=final_text,
                isFinal=True,
            ).to_json())

            await websocket.send(StatusMessage(status="ready").to_json())

        except Exception as e:
            logger.error(f"Error stopping transcription: {e}")
            await websocket.send(StatusMessage(status="error", error=str(e)).to_json())
        finally:
            self.transcriber = None

    async def _handle_audio(self, websocket: WebSocketServerProtocol, message: AudioMessage):
        """Handle incoming audio chunk."""
        if not self.transcriber or not self.transcriber.is_active():
            return

        # Feed audio to transcriber (non-blocking)
        self.transcriber.feed_audio_base64(message.data)

    async def run(self):
        """Start the WebSocket server."""
        logger.info(f"Starting STT server on ws://{self.server_config.host}:{self.server_config.port}")

        async with websockets.serve(
            self.handle_client,
            self.server_config.host,
            self.server_config.port,
        ):
            logger.info("STT server running. Press Ctrl+C to stop.")
            await asyncio.Future()  # Run forever


def run_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    model: str = "distil-large-v3",
    language: str = "en",
    device: str = "cuda",
    compute_type: str = "int8_float16",
):
    """Run the STT server with the specified configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    server_config = ServerConfig(host=host, port=port)
    transcriber_config = TranscriberConfig(
        model=model,
        language=language,
        device=device,
        compute_type=compute_type,
    )

    server = STTServer(server_config, transcriber_config)

    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")


if __name__ == "__main__":
    run_server()
