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
    logger.info(f"Recebida requisição STT com correlation_id: {props.correlation_id}")
    
    transcribed_text = process_audio_bytes(vosk_model, body)
    
    response_payload = json.dumps({"text": transcribed_text}).encode('utf-8')
    
    # Publica a resposta na fila de callback especificada pelo orquestrador
    ch.basic_publish(
        exchange='',
        routing_key=props.reply_to,
        properties=pika.BasicProperties(correlation_id=props.correlation_id),
        body=response_payload
    )
    ch.basic_ack(delivery_tag=method.delivery_tag)
    logger.info(f"Resposta STT enviada para a fila '{props.reply_to}'.")

if __name__ == "__main__":
    vosk_model = load_model()
    if vosk_model:
        mq_client = MQClient()
        mq_client.declare_queue("stt_requests")
        # O método start_worker agora é bloqueante e gerencia o consumo
        mq_client.start_worker("stt_requests", stt_worker_callback)
    else:
        logger.error("Serviço STT não pôde ser iniciado pois o modelo não foi carregado.")

