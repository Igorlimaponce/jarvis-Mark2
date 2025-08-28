from __future__ import annotations

import struct
from typing import Generator

import pvporcupine
from loguru import logger

from config.settings import settings


class WakeWordDetector:
    """Detecta a palavra de ativação (wake word) em um fluxo de áudio."""

    def __init__(self) -> None:
        access_key = settings.porcupine.access_key
        keyword = settings.porcupine.keyword

        if not access_key or access_key == "YOUR_PICOVOICE_ACCESS_KEY":
            raise ValueError(
                "A chave de acesso do Porcupine não foi definida. "
                "Obtenha uma em https://console.picovoice.ai/ e defina PORCUPINE__ACCESS_KEY no .env"
            )

        try:
            self.porcupine = pvporcupine.create(
                access_key=access_key, keywords=[keyword]
            )
            logger.info(f"Detector de Wake Word inicializado com a palavra: '{keyword}'")
        except pvporcupine.PorcupineError as e:
            logger.error(f"Erro ao inicializar o Porcupine: {e}")
            raise

        self.frame_length = self.porcupine.frame_length
        self.sample_rate = self.porcupine.sample_rate

    def process(self, pcm_chunk: bytes) -> bool:
        """Processa um pedaço de áudio e retorna True se a wake word for detectada."""
        pcm = struct.unpack_from("h" * self.frame_length, pcm_chunk)
        result = self.porcupine.process(pcm)
        return result != -1

    def __del__(self) -> None:
        if hasattr(self, "porcupine") and self.porcupine:
            self.porcupine.delete()
            logger.info("Detector de Wake Word finalizado.")