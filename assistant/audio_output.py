from __future__ import annotations

import io

import pyaudio
import soundfile as sf
from loguru import logger


class AudioOutput:
    """Gerencia a reprodução de áudio."""

    def __init__(self) -> None:
        self.p = pyaudio.PyAudio()

    def play_audio_stream(self, audio_bytes: bytes) -> None:
        """Reproduz um fluxo de bytes de áudio (formato WAV)."""
        try:
            with sf.SoundFile(io.BytesIO(audio_bytes), "r") as sound_file:
                stream = self.p.open(
                    format=pyaudio.paInt16,
                    channels=sound_file.channels,
                    rate=sound_file.samplerate,
                    output=True,
                )
                logger.info("Reproduzindo resposta...")
                data = sound_file.read(1024, dtype="int16")
                while len(data) > 0:
                    stream.write(data.tobytes())
                    data = sound_file.read(1024, dtype="int16")

                stream.stop_stream()
                stream.close()
                logger.success("Reprodução finalizada.")
        except Exception as e:
            logger.error(f"Erro ao reproduzir áudio: {e}")

    def __del__(self) -> None:
        self.p.terminate()