from __future__ import annotations

import io
import json
import pika
import torch
from loguru import logger
from TTS.api import TTS

from config.settings import settings, ROOT_DIR
from services.common.mq_client import MQClient

def load_model():
    """Carrega o modelo Coqui TTS e retorna a instância e o speaker."""
    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Usando dispositivo: {device}")

        logger.info(f"Carregando modelo Coqui TTS: {settings.tts.model_name}")
        tts_model = TTS(settings.tts.model_name).to(device)
        logger.info("Modelo Coqui TTS carregado com sucesso.")

        speaker_to_clone = None
        if settings.tts.speaker_wav:
            speaker_wav_full_path = ROOT_DIR / settings.tts.speaker_wav
            if speaker_wav_full_path.exists():
                logger.info(f"Usando speaker para clonagem de voz de: {speaker_wav_full_path}")
                speaker_to_clone = str(speaker_wav_full_path)
            else:
                logger.warning(f"Arquivo de speaker não encontrado em {speaker_wav_full_path}. Usando voz padrão.")
        
        return tts_model, speaker_to_clone
    except Exception:
        logger.exception("Falha crítica ao carregar o modelo Coqui TTS.")
        return None, None

def synthesize_text(model: TTS, text: str, language: str, speaker: str | None) -> bytes | None:
    """Sintetiza o texto em áudio e retorna os bytes."""
    try:
        logger.info(f"Sintetizando texto de {len(text)} caracteres na língua '{language}'")
        wav_bytes = model.tts(
            text=text,
            speaker_wav=speaker,
            language=language,
        )
        logger.info(f"Áudio gerado com {len(wav_bytes)} bytes.")
        return bytes(wav_bytes)
    except Exception:
        logger.exception("Falha inesperada durante a síntese de voz.")
        return None

def tts_worker_callback(ch, method, props, body):
    """Função de callback para processar mensagens da fila TTS."""
    try:
        payload = json.loads(body)
        job_id = payload.get("job_id")
        text_to_synthesize = payload.get("text")
        language = payload.get("language", "pt")
        if not job_id or not text_to_synthesize:
            raise ValueError("Payload inválido: job_id ou text ausentes.")
        audio_bytes = synthesize_text(tts_model, text_to_synthesize, language, speaker_to_clone) or b''
        response_payload = json.dumps({"job_id": job_id}).encode('utf-8')
        # Envia o áudio como body binário, job_id no header
        ch.basic_publish(
            exchange='jarvis_events',
            routing_key='tts.completed',
            properties=pika.BasicProperties(headers={"job_id": job_id}),
            body=audio_bytes
        )
        logger.info(f"TTS concluído para job_id {job_id}.")
    except Exception as e:
        logger.exception("Erro no processamento TTS.")
        job_id = None
        try:
            job_id = json.loads(body).get('job_id')
        except Exception:
            pass
        error_payload = json.dumps({"job_id": job_id, "error": str(e)}).encode('utf-8')
        ch.basic_publish(
            exchange='jarvis_events',
            routing_key='tts.failed',
            body=error_payload
        )
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)

if __name__ == "__main__":
    tts_model, speaker_to_clone = load_model()
    if tts_model:
        mq_client = MQClient()
        mq_client.declare_queue("tts_requests")
        mq_client.start_worker("tts_requests", tts_worker_callback)
    else:
        logger.error("Serviço TTS não pôde ser iniciado pois o modelo não foi carregado.")


