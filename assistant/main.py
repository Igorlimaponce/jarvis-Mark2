# jarvis_mark2/assistant/main.py

import asyncio
import base64
import json
import os
from uuid import uuid4

import aio_pika
from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect
from langchain_core.messages import HumanMessage, SystemMessage, messages_to_dict
from loguru import logger
from sqlalchemy.orm import sessionmaker

from assistant.agent_graph import app_graph
from assistant.persistent_memory import PGConversationMemory
from config.prompts import SYSTEM_PROMPT
from database.connection import engine, init_db_if_needed
from database.models import User
from scripts.sync_tools import sync_tools_to_db

app = FastAPI(title="Jarvis Orchestrator", version="1.0")

# --- Gerenciamento de Conexões ---
active_websockets: dict[str, WebSocket] = {}
mq_connection = None
mq_channel = None

# --- Ciclo de Vida da Aplicação (Startup/Shutdown) ---

@app.on_event("startup")
async def startup_event():
    """Inicializa o banco de dados, sincroniza ferramentas e inicia o consumidor de eventos."""
    init_db_if_needed()
    logger.info("Sincronizando ferramentas com o banco de dados...")
    sync_tools_to_db()
    
    # Inicia o consumidor de RabbitMQ como uma task de background
    asyncio.create_task(start_event_consumer())
    logger.info("Orquestrador iniciado e consumidor de eventos agendado.")

@app.on_event("shutdown")
async def shutdown_event():
    """Fecha a conexão com o RabbitMQ de forma limpa."""
    global mq_connection
    if mq_connection:
        await mq_connection.close()
    logger.info("Conexão com RabbitMQ fechada.")

# --- Endpoints da API ---

@app.post("/v2/interact/start")
async def start_interaction(audio_file: UploadFile = File(...)):
    """Recebe o áudio, cria um job e publica o evento inicial."""
    global mq_channel
    if not mq_channel:
        raise HTTPException(status_code=503, detail="Serviço de mensageria indisponível.")

    job_id = str(uuid4())
    audio_bytes = await audio_file.read()

    # Publica o evento para o STT processar
    await mq_channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps({
                "job_id": job_id,
                "audio_bytes": base64.b64encode(audio_bytes).decode()
            }).encode()
        ),
        routing_key="stt.requested"
    )
    logger.info(f"[{job_id}] Job de interação iniciado e evento 'stt.requested' publicado.")
    return {"job_id": job_id}

@app.websocket("/v2/interact/ws/{job_id}")
async def ws_interaction(websocket: WebSocket, job_id: str):
    """Gerencia a conexão WebSocket para um job, aguardando por eventos."""
    await websocket.accept()
    active_websockets[job_id] = websocket
    logger.info(f"[{job_id}] WebSocket conectado.")
    try:
        # Mantém a conexão aberta para recebermos os eventos do consumidor
        while True:
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        logger.warning(f"[{job_id}] WebSocket desconectado.")
    finally:
        active_websockets.pop(job_id, None)

# --- Lógica do Consumidor de Eventos (Totalmente Assíncrono) ---

async def start_event_consumer():
    """Conecta ao RabbitMQ e inicia o consumo de eventos de forma assíncrona."""
    global mq_connection, mq_channel
    loop = asyncio.get_event_loop()
    try:
        rabbitmq_url = os.getenv("RABBITMQ_URL")
        mq_connection = await aio_pika.connect_robust(rabbitmq_url, loop=loop)
        mq_channel = await mq_connection.channel()
        
        # Garante que a topologia (exchange e filas) existe
        await mq_channel.exchange_declare(name="jarvis_events", type="topic", durable=True)
        queue = await mq_channel.declare_queue("orchestrator_events_queue", durable=True)
        
        # Binds para os eventos que o orquestrador precisa ouvir
        await queue.bind("jarvis_events", routing_key="stt.completed")
        await queue.bind("jarvis_events", routing_key="stt.failed")
        await queue.bind("jarvis_events", routing_key="tts.completed")
        await queue.bind("jarvis_events", routing_key="tts.failed")

        logger.info("[Event Consumer] Conectado ao RabbitMQ e pronto para consumir eventos.")
        await queue.consume(on_message)

    except Exception:
        logger.exception("[Event Consumer] Falha crítica ao conectar/consumir do RabbitMQ.")

async def on_message(message: aio_pika.IncomingMessage):
    """Callback assíncrono para processar cada evento recebido."""
    async with message.process():
        routing_key = message.routing_key
        logger.info(f"Evento recebido com routing_key: {routing_key}")
        try:
            if routing_key == "stt.completed":
                await handle_stt_completed(message)
            elif routing_key == "tts.completed":
                await handle_tts_completed(message)
            elif routing_key in ("stt.failed", "tts.failed"):
                await handle_task_failed(message)
        except Exception:
            logger.exception(f"Erro não tratado ao processar evento '{routing_key}'.")

async def handle_stt_completed(message: aio_pika.IncomingMessage):
    """Processa o resultado do STT e invoca o agente de IA."""
    payload = json.loads(message.body)
    job_id = payload.get("job_id")
    user_text = payload.get("text")

    if not all([job_id, user_text]):
        logger.error(f"Payload inválido para 'stt.completed': {payload}")
        return

    logger.info(f"[{job_id}] STT concluído. Texto: '{user_text}'")

    try:
        # Executa o grafo do agente de forma assíncrona, não bloqueando o consumidor
        final_state = await invoke_agent_graph(job_id, user_text)
        assistant_reply = final_state["messages"][-1].content
        logger.info(f"[{job_id}] Resposta do Agente: '{assistant_reply}'")

        # Publica a resposta para o TTS sintetizar
        await mq_channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps({
                    "job_id": job_id,
                    "text": assistant_reply
                }).encode()
            ),
            routing_key="tts.requested"
        )
    except Exception as e:
        logger.exception(f"[{job_id}] Falha no pipeline do agente. Gerando resposta de erro.")
        # Se o agente falhar, envia um texto de erro para o TTS
        await mq_channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps({
                    "job_id": job_id,
                    "text": "Desculpe, encontrei um problema ao processar sua solicitação."
                }).encode()
            ),
            routing_key="tts.requested"
        )

async def handle_tts_completed(message: aio_pika.IncomingMessage):
    """Envia o áudio sintetizado para o cliente via WebSocket."""
    job_id = message.headers.get("job_id")
    if job_id in active_websockets:
        websocket = active_websockets[job_id]
        try:
            await websocket.send_bytes(message.body)
            logger.info(f"[{job_id}] Áudio final enviado para o cliente via WebSocket.")
        except WebSocketDisconnect:
            logger.warning(f"[{job_id}] WebSocket já estava desconectado ao tentar enviar áudio.")
        finally:
            # Opcional: fechar a conexão após enviar a resposta final
            await websocket.close()
            active_websockets.pop(job_id, None)

async def handle_task_failed(message: aio_pika.IncomingMessage):
    """Envia uma notificação de erro para o cliente via WebSocket."""
    payload = json.loads(message.body)
    job_id = payload.get("job_id")
    error_message = payload.get("error", "Erro desconhecido")
    logger.error(f"[{job_id}] Falha recebida: {message.routing_key} - {error_message}")

    if job_id in active_websockets:
        websocket = active_websockets[job_id]
        try:
            await websocket.send_json({"error": message.routing_key, "detail": error_message})
        finally:
            await websocket.close()
            active_websockets.pop(job_id, None)

# --- Funções Auxiliares ---

async def invoke_agent_graph(session_id: str, user_text: str) -> dict:
    """Função auxiliar para invocar o LangGraph de forma assíncrona."""
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    db = SessionLocal()
    try:
        memory = PGConversationMemory(session_id=session_id, db_session=db)
        human_message = HumanMessage(content=user_text)
        message_db_id = memory.save_message_and_get_id(messages_to_dict([human_message])[0])
        
        history = memory.load_memory_variables({})
        messages = history.get("memory", [])
        
        user = db.query(User).filter(User.username == "igor").first()
        system_prompt_text = SYSTEM_PROMPT
        if user and user.preferences:
            facts = "\n".join(f"- {fact}" for fact in user.preferences)
            system_prompt_text = f"{SYSTEM_PROMPT}\n\nFatos conhecidos sobre o usuário:\n{facts}"
        
        messages.insert(0, SystemMessage(content=system_prompt_text))
        messages.append(human_message)
        
        graph_input = {"messages": messages, "db_session": db, "message_db_id": message_db_id}
        final_state = await app_graph.ainvoke(graph_input, {"recursion_limit": 10})
        
        assistant_reply = final_state["messages"][-1].content
        memory.save_context({"input": user_text}, {"output": assistant_reply})
        return final_state
    finally:
        db.close()

# Manter o endpoint de health check
@app.get("/health")
async def health():
    return {"status": "ok"}