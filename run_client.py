from __future__ import annotations
import tempfile
from pathlib import Path
import requests
from loguru import logger
import threading
import time
import asyncio
import websockets
import json

from assistant.audio_manager import AudioManager
from assistant.audio_output import AudioOutput
from assistant.wake_word_detector import WakeWordDetector
from config.settings import settings

class ClientState:
    LISTENING = 1
    PROCESSING = 2

def main():
    """Função principal que gerencia o estado do cliente e o loop de interação."""
    orchestrator_ws_url = str(settings.api.orchestrator_url).replace("http", "ws")
    orchestrator_http_url = str(settings.api.orchestrator_url)

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
        """Thread que escuta a wake word em background."""
        while not stop_event.is_set():
            if state == ClientState.LISTENING:
                audio_manager.listen_for_wake_word()
                nonlocal state
                state = ClientState.PROCESSING
            time.sleep(0.1)

    listener_thread = threading.Thread(target=wake_word_listener, daemon=True)
    listener_thread.start()

    logger.info("Cliente V2 iniciado. Diga 'Jarvis' para começar.")

    try:
        while True:
            if state == ClientState.PROCESSING:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp_file:
                    command_audio_path = Path(tmp_file.name)
                    audio_manager.record_command(command_audio_path)

                    logger.info("Enviando comando para o orquestrador...")
                    job_id = None
                    try:
                        with open(command_audio_path, "rb") as f:
                            files = {"audio_file": (command_audio_path.name, f, "audio/wav")}
                            response = requests.post(
                                f"{orchestrator_http_url}/v2/interact/start", files=files, timeout=10
                            )
                            response.raise_for_status()
                            job_id = response.json().get("job_id")
                            logger.info(f"Job iniciado com ID: {job_id}")

                    except requests.RequestException as e:
                        logger.error(f"Erro ao iniciar a interação: {e}")
                        state = ClientState.LISTENING
                        continue  # Volta a escutar

                    if job_id:
                        # Inicia a comunicação via WebSocket
                        asyncio.run(handle_websocket_communication(orchestrator_ws_url, job_id, audio_output))
                
                # Após o processamento (sucesso ou falha), volta a escutar
                state = ClientState.LISTENING
                logger.info("Ouvindo novamente...")

            time.sleep(0.1)
    except KeyboardInterrupt:
        logger.info("Cliente finalizado pelo usuário.")
        stop_event.set()
        listener_thread.join()

async def handle_websocket_communication(uri, job_id, audio_output):
    """Gerencia a comunicação WebSocket para um job específico."""
    ws_uri = f"{uri}/v2/interact/ws/{job_id}"
    logger.info(f"Conectando ao WebSocket: {ws_uri}")
    try:
        async with websockets.connect(ws_uri, timeout=120) as websocket:
            while True:
                message = await websocket.recv()
                if isinstance(message, str):
                    # Mensagens de status ou erro em JSON
                    data = json.loads(message)
                    if "error" in data:
                        logger.error(f"Recebido erro do orquestrador: {data}")
                        # TODO: Reproduzir um som de erro genérico
                        break
                    else:
                        logger.info(f"Status update: {data}")
                elif isinstance(message, bytes):
                    # Resposta de áudio final
                    logger.info(f"Recebido stream de áudio de {len(message)} bytes. Reproduzindo...")
                    audio_output.play_audio_stream(message)
                    logger.info("Reprodução finalizada.")
                    break  # Finaliza a conexão após receber o áudio

    except websockets.exceptions.ConnectionClosed as e:
        logger.warning(f"Conexão WebSocket fechada: {e}")
    except Exception:
        logger.exception("Erro na comunicação WebSocket:")

if __name__ == "__main__":
    main()