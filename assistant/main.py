from __future__ import annotations

import io
import json
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
import anyio # Biblioteca para I/O assíncrono
import random
from loguru import logger
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage, SystemMessage, messages_to_dict

from assistant.agent_graph import app_graph
from assistant.persistent_memory import PGConversationMemory
from config.prompts import SYSTEM_PROMPT
from database.connection import get_db, init_db_if_needed
from database.models import User
from services.common.mq_client import MQClient
# ADICIONE ESTA LINHA PARA IMPORTAR A FUNÇÃO
from scripts.sync_tools import sync_tools_to_db 

app = FastAPI(title="Jarvis Orchestrator", version="1.0")


@app.on_event("startup")
async def _startup():
    init_db_if_needed()
    
    # --- INÍCIO DA MODIFICAÇÃO ---
    # Garante que as ferramentas do código estejam sincronizadas com o banco de dados.
    logger.info("Sincronizando ferramentas com o banco de dados na inicialização...")
    sync_tools_to_db()
    # --- FIM DA MODIFICAÇÃO ---

    # Declarar filas no RabbitMQ para garantir que existam
    try:
        mq_client = MQClient()
        mq_client.declare_queue("stt_requests")
        mq_client.declare_queue("tts_requests")
        mq_client.declare_queue("graph_builder_queue")
        mq_client.close()
        logger.info("Filas do RabbitMQ declaradas com sucesso.")
    except Exception as e:
        logger.opt(exception=True).error("Falha ao declarar filas do RabbitMQ na inicialização.")

    logger.info("Orquestrador iniciado")


@app.get("/health")
async def health():
    return {"status": "ok"}

# Crie uma lista de frases de feedback carismáticas
FEEDBACK_PHRASES = [
    "Consultando meus bancos de dados, senhor.",
    "Um momento, estou processando sua solicitação.",
    "Computando a resposta mais eficiente.",
    "Acessando os protocolos relevantes.",
]

@app.post("/interact")
async def interact(
    audio_file: UploadFile = File(...),
    x_session_id: str | None = Header(None),
    db: Session = Depends(get_db),
):
    session_id = x_session_id or str(uuid4())
    
    async def response_generator():
        mq_client = None
        try:
            mq_client = MQClient()
            audio_bytes = await audio_file.read()

            # 1. Speech-to-Text via RabbitMQ (sem mudanças)
            stt_response_body = mq_client.call("stt_requests", audio_bytes)
            if not stt_response_body:
                logger.error(f"[{session_id}] Timeout ou nenhuma resposta do serviço STT.")
                return

            user_text = json.loads(stt_response_body).get("text", "")
            if not user_text:
                logger.warning(f"[{session_id}] STT não retornou texto.")
                return

            logger.info(f"[{session_id}] Usuário: {user_text}")

            # --- INÍCIO DA MODIFICAÇÃO PARA FEEDBACK ---
            # 2. Geração de Feedback Auditivo (se necessário)
            if any(keyword in user_text.lower() for keyword in ["pesquise", "procure", "analise", "o que é"]):
                feedback_text = random.choice(FEEDBACK_PHRASES)
                logger.info(f"[{session_id}] Gerando feedback: '{feedback_text}'")
                tts_payload = json.dumps({"text": feedback_text}).encode('utf-8')
                feedback_audio = mq_client.call("tts_requests", tts_payload)
                if feedback_audio:
                    yield feedback_audio
            # --- FIM DA MODIFICAÇÃO ---

            # 3. Invocação do Agente e Resposta Final (lógica principal)
            memory = PGConversationMemory(session_id=session_id, db_session=db)
            human_message = HumanMessage(content=user_text)
            message_db_id = memory.save_message_and_get_id(messages_to_dict([human_message])[0])
            
            history = memory.load_memory_variables({})
            messages = history.get("memory", [])
            
            user = db.query(User).filter(User.username == "igor").first() # Simplificado
            system_prompt_text = SYSTEM_PROMPT
            if user and user.preferences:
                facts = "\n".join(f"- {fact}" for fact in user.preferences)
                system_prompt_text = f"{SYSTEM_PROMPT}\n\nFatos conhecidos sobre o usuário:\n{facts}"
            
            messages.insert(0, SystemMessage(content=system_prompt_text))
            messages.append(human_message)

            graph_input = {"messages": messages, "db_session": db, "message_db_id": message_db_id}
            final_state = await app_graph.ainvoke(graph_input, {"recursion_limit": 10})
            assistant_reply = final_state["messages"][-1].content

            logger.info(f"[{session_id}] Jarvis: {assistant_reply}")
            memory.save_context({"input": user_text}, {"output": assistant_reply})
            
            # Publica a conversa para construção do grafo de conhecimento
            try:
                graph_payload = json.dumps({
                    "user_text": user_text,
                    "assistant_text": assistant_reply,
                    "session_id": session_id
                }).encode('utf-8')
                mq_client.publish("graph_builder_queue", graph_payload)
                logger.info(f"[{session_id}] Conversa publicada para o Graph Builder.")
            except Exception as e:
                logger.error(f"[{session_id}] Falha ao publicar para o Graph Builder: {e}")

            # 4. Geração do Áudio Final
            final_tts_payload = json.dumps({"text": assistant_reply}).encode('utf-8')
            final_audio = mq_client.call("tts_requests", final_tts_payload)
            if final_audio:
                yield final_audio

        except Exception as e:
            logger.exception("Falha inesperada na interação")
            # Em caso de erro, podemos opcionalmente gerar um áudio de erro
        finally:
            if mq_client:
                mq_client.close()

    return StreamingResponse(response_generator(), media_type="application/octet-stream")
