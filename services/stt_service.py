from __future__ import annotations

import json
import wave
import io
import pika # Adicionado para pika.BasicProperties

from loguru import logger
from vosk import Model, KaldiRecognizer

from config.settings import settings, ROOT_DIR
from services.common.mq_client import MQClient

def load_model():
    """Carrega o modelo Vosk e retorna a instância."""
    try:
        model_path = ROOT_DIR / settings.stt.model_path

        if not model_path.exists():
            logger.error(f"Modelo Vosk não encontrado em: {model_path}")
            return None
        
        logger.info(f"Carregando modelo Vosk de: {model_path}")
        model = Model(str(model_path))
        logger.info("Modelo Vosk carregado com sucesso.")
        return model
    except Exception:
        logger.exception("Falha crítica ao carregar o modelo Vosk.")
        return None

def process_audio_bytes(model: Model, audio_bytes: bytes) -> str:
    """Processa os bytes de áudio e retorna o texto transcrito."""
    try:
        with io.BytesIO(audio_bytes) as audio_stream:
            with wave.open(audio_stream, "rb") as wf:
                if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
                    logger.error("Formato de áudio inválido. Requerido: WAV, 16kHz, 16-bit, mono PCM.")
                    return ""
                
                rec = KaldiRecognizer(model, wf.getframerate())
                rec.SetWords(True)

                full_text = ""
                while True:
                    data = wf.readframes(4000)
                    if len(data) == 0:
                        break
                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        full_text += result.get("text", "") + " "

                final_result = json.loads(rec.FinalResult())
                full_text += final_result.get("text", "")
                
                return full_text.strip()
    except Exception:
        logger.exception("Erro durante a transcrição do áudio.")
        return ""

def stt_worker_callback(ch, method, props, body):
    """Função de callback para processar mensagens da fila STT."""
    try:
        # Espera-se que o body seja um JSON com 'job_id' e 'audio_bytes'
        payload = json.loads(body)
        job_id = payload.get('job_id')
        audio_bytes = payload.get('audio_bytes')
        logger.info(f"Recebida requisição STT para job_id: {job_id}")
        if not job_id or not audio_bytes:
            raise ValueError("Payload inválido: job_id ou audio_bytes ausentes.")
        # Decodifica audio_bytes se vier como base64
        if isinstance(audio_bytes, str):
            import base64
            audio_bytes = base64.b64decode(audio_bytes)
        transcribed_text = process_audio_bytes(vosk_model, audio_bytes)
        response_payload = json.dumps({"job_id": job_id, "text": transcribed_text}).encode('utf-8')
        ch.basic_publish(
            exchange='jarvis_events',
            routing_key='stt.completed',
            body=response_payload
        )
        logger.info(f"STT concluído para job_id {job_id}.")
    except Exception as e:
        logger.exception("Erro no processamento STT.")
        # Tenta extrair job_id do payload, se possível
        job_id = None
        try:
            job_id = json.loads(body).get('job_id')
        except Exception:
            pass
        error_payload = json.dumps({"job_id": job_id, "error": str(e)}).encode('utf-8')
        ch.basic_publish(
            exchange='jarvis_events',
            routing_key='stt.failed',
            body=error_payload
        )
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)

if __name__ == "__main__":
    vosk_model = load_model()
    if vosk_model:
        mq_client = MQClient()
        mq_client.declare_queue("stt_requests")
        # O método start_worker agora é bloqueante e gerencia o consumo
        mq_client.start_worker("stt_requests", stt_worker_callback)
    else:
        logger.error("Serviço STT não pôde ser iniciado pois o modelo não foi carregado.")

