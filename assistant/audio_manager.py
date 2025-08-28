from __future__ import annotations

import time
import wave
from collections import deque
from pathlib import Path

import pyaudio
from loguru import logger
import webrtcvad # Importar a nova biblioteca

from assistant.wake_word_detector import WakeWordDetector

class AudioManager:
    """Gerencia a captura de áudio, detecção de wake word e gravação de comandos."""

    def __init__(self, detector: WakeWordDetector):
        self.detector = detector
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.detector.sample_rate,
            input=True,
            frames_per_buffer=self.detector.frame_length,
        )
        # --- NOVA LÓGICA DE VAD ---
        self.vad = webrtcvad.Vad()
        self.vad.set_mode(3)  # Modo mais agressivo (sensível ao silêncio)
        # WebRTC VAD opera em chunks de 10, 20 ou 30 ms.
        # O sample rate do porcupine é 16000 Hz. 16000 * 0.030 = 480 frames.
        # Usaremos o frame_length do porcupine (512) que é próximo e compatível.
        self.VAD_FRAME_MS = (self.detector.frame_length * 1000) / self.detector.sample_rate
        logger.info(f"VAD configurado para operar com chunks de {self.VAD_FRAME_MS:.0f} ms.")
        # --------------------------

    def listen_for_wake_word(self) -> None:
        """Escuta continuamente até que a wake word seja detectada."""
        logger.info(f"Ouvindo pela wake word '{self.detector.porcupine.keyword}'...")
        while True:
            pcm = self.stream.read(self.detector.frame_length)
            if self.detector.process(pcm):
                logger.success("Wake word detectada!")
                return

    def record_command(self, output_path: Path, timeout: int = 10, silence_duration_ms: int = 1500) -> None:
        """Grava o áudio após a wake word até detectar silêncio usando VAD."""
        logger.info("Gravando comando...")
        frames = []
        
        num_silence_frames_needed = int(silence_duration_ms / self.VAD_FRAME_MS)
        consecutive_silent_frames = 0
        
        start_time = time.time()
        
        # Grava um chunk inicial para não perder o início da fala
        initial_chunk = self.stream.read(self.detector.frame_length)
        frames.append(initial_chunk)
        
        while time.time() - start_time < timeout:
            pcm_chunk = self.stream.read(self.detector.frame_length)
            frames.append(pcm_chunk)
            
            # A lógica agora usa a biblioteca VAD
            is_speech = self.vad.is_speech(pcm_chunk, self.detector.sample_rate)
            
            if not is_speech:
                consecutive_silent_frames += 1
            else:
                consecutive_silent_frames = 0
            
            if consecutive_silent_frames > num_silence_frames_needed:
                logger.info("Silêncio detectado pelo VAD, finalizando gravação.")
                break
        else:
            logger.warning("Timeout de gravação atingido.")

        logger.success(f"Gravação finalizada. Salvando em {output_path}")
        with wave.open(str(output_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(self.p.get_sample_size(pyaudio.paInt16))
            wf.setframerate(self.detector.sample_rate)
            wf.writeframes(b"".join(frames))

    def __del__(self) -> None:
        if hasattr(self, "stream") and self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if hasattr(self, "p") and self.p:
            self.p.terminate()
        logger.info("Gerenciador de áudio finalizado.")