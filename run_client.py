from __future__ import annotations
import tempfile
from pathlib import Path
import uuid
import requests
from loguru import logger
import threading
import time

from assistant.audio_manager import AudioManager
from assistant.audio_output import AudioOutput
from assistant.wake_word_detector import WakeWordDetector
from config.settings import settings, ROOT_DIR

SESSION_CACHE_FILE = ROOT_DIR / ".session_id_cache"

class ClientState:
    LISTENING = 1
    PROCESSING = 2
    SPEAKING = 3

def get_or_create_session_id() -> str:
    if SESSION_CACHE_FILE.exists():
        session_id = SESSION_CACHE_FILE.read_text().strip()
        if session_id:
            logger.info(f"Retomando sessão existente: {session_id}")
            return session_id
    session_id = str(uuid.uuid4())
    SESSION_CACHE_FILE.write_text(session_id)
    logger.info(f"Iniciando nova sessão de cliente: {session_id}")
    return session_id

def main():
    orchestrator_url = str(settings.api.orchestrator_url)
    session_id = get_or_create_session_id()

    try:
        detector = WakeWordDetector()
        audio_manager = AudioManager(detector)
        audio_output = AudioOutput()
    except Exception as e:
        logger.error(f"Falha ao inicializar os componentes de áudio: {e}")
        return

    state = ClientState.LISTENING
    stop_event = threading.Event()
    
    def wake_word_listener():
        logger.info("Thread de detecção iniciada.")
        while not stop_event.is_set():
            if state == ClientState.LISTENING:
                audio_manager.listen_for_wake_word()
                nonlocal state
                state = ClientState.PROCESSING
            time.sleep(0.1)

    listener_thread = threading.Thread(target=wake_word_listener, daemon=True)
    listener_thread.start()

    logger.info("Cliente iniciado. Diga 'Jarvis' para começar.")

    try:
        while True:
            if state == ClientState.PROCESSING:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp_file:
                    command_audio_path = Path(tmp_file.name)
                    audio_manager.record_command(command_audio_path)

                    logger.info("Enviando comando para o orquestrador...")
                    with open(command_audio_path, "rb") as f:
                        files = {"audio_file": (command_audio_path.name, f, "audio/wav")}
                        headers = {"X-Session-Id": session_id}
                        response = requests.post(
                            f"{orchestrator_url}/interact", files=files, headers=headers, timeout=120, stream=True
                        )

                    if response.status_code == 200:
                        state = ClientState.SPEAKING
                        for audio_chunk in response.iter_content(chunk_size=None):
                            if audio_chunk:
                                audio_output.play_audio_stream(audio_chunk)
                        state = ClientState.LISTENING
                        logger.info("Ouvindo novamente...")
                    else:
                        logger.error(f"Erro na API: {response.status_code} - {response.text}")
                        state = ClientState.LISTENING

            time.sleep(0.1)
    except KeyboardInterrupt:
        logger.info("Cliente finalizado pelo usuário.")
        stop_event.set()
        listener_thread.join()

if __name__ == "__main__":
    main()