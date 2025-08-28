from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Adiciona o diretório raiz ao sys.path para permitir importações absolutas
# de módulos como 'config' e 'database' quando executado como script.
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.append(str(ROOT_DIR))

from loguru import logger
from sqlalchemy.orm import Session

from assistant.agent_core import get_llm
from config.prompts import SUMMARIZE_PROMPT
from config.settings import settings
from database.connection import get_session_local  # Importar o sessionmaker
from database.models import ConversationHistory, ConversationSession, User


def get_unsummarized_sessions(db: Session) -> list[ConversationSession]:
    """Busca no banco de dados por sessões que ainda não foram sumarizadas."""
    return db.query(ConversationSession).filter(ConversationSession.is_summarized == False).all()


import json # Adicionar este import

# ...

def format_conversation(history: list[ConversationHistory]) -> str:
    """Formata o histórico de uma conversa em um único texto legível."""
    dialog = []
    for h in history:
        try:
            # --- CORREÇÃO CRÍTICA AQUI ---
            # Decodifica a string JSON para um dicionário Python
            message_data = json.loads(h.content)
            # Extrai o texto real da mensagem aninhada
            text = message_data.get("content", "")
            # --- FIM DA CORREÇÃO ---
            
            # Garante que o papel (role) venha do banco de dados para consistência
            role = h.role.capitalize()
            dialog.append(f"{role}: {text}")
        except (json.JSONDecodeError, TypeError):
            # Fallback para o caso de o conteúdo não ser um JSON válido
            dialog.append(f"{h.role.capitalize()}: {h.content}")
    return "\n".join(dialog)


def summarize_conversation(llm, conversation_text: str) -> str:
    """Envia o texto da conversa para o LLM e retorna a sumarização."""
    prompt = SUMMARIZE_PROMPT.format(conversation_text=conversation_text)
    try:
        response = llm.invoke(prompt)
        return response.content
    except Exception:
        logger.exception("Falha ao invocar o LLM para sumarização.")
        return ""


def update_user_preferences(db: Session, session: ConversationSession, summary: str):
    """Atualiza o campo de preferências do usuário com os novos fatos extraídos."""
    if "Nenhum fato relevante encontrado" in summary:
        logger.info(f"Nenhum fato novo para a sessão {session.session_id}.")
        return

    user: User | None = session.user
    if not user:
        # Se a sessão não tiver um usuário, cria um usuário padrão.
        # Em um sistema real, a associação usuário-sessão seria mais robusta.
        user = db.query(User).filter(User.username == "default_user").first()
        if not user:
            user = User(username="default_user", preferences=[])
            db.add(user)
        session.user = user

    # Extrai os fatos da sumarização (removendo marcadores)
    new_facts = [line.strip().lstrip("-").strip() for line in summary.split('\n') if line.strip()]
    
    # Evita duplicatas
    current_preferences = set(user.preferences or [])
    updated_preferences = list(current_preferences.union(set(new_facts)))
    
    user.preferences = updated_preferences
    logger.success(f"Preferências do usuário '{user.username}' atualizadas com {len(new_facts)} novos fatos.")


def run_summarizer_worker():
    """Loop principal do worker que busca, sumariza e atualiza as conversas."""
    logger.info("Worker de sumarização de memória iniciado.")
    llm = get_llm()
    SessionLocal = get_session_local()  # Obter a factory de sessões

    while True:
        try:
            # Cria uma nova sessão para cada ciclo de trabalho
            with SessionLocal() as db:
                sessions_to_process = get_unsummarized_sessions(db)
                if not sessions_to_process:
                    logger.info("Nenhuma sessão nova para sumarizar. Aguardando...")
                else:
                    logger.info(f"Encontradas {len(sessions_to_process)} sessões para sumarizar.")
                    for session in sessions_to_process:
                        conversation_text = format_conversation(session.history)
                        summary = summarize_conversation(llm, conversation_text)

                        if summary:
                            update_user_preferences(db, session, summary)

                        session.is_summarized = True
                        db.commit()  # Commit por sessão processada
                        logger.info(f"Sessão {session.session_id} processada e marcada como sumarizada.")

        except Exception as e:
            # O 'with' statement já lida com o rollback e fechamento da sessão
            logger.opt(exception=True).error(f"Erro no loop do worker de sumarização: {e}")

        finally:
            interval = settings.app.summarizer_interval_seconds
            logger.info(f"Aguardando {interval} segundos para o próximo ciclo.")
            time.sleep(interval)


if __name__ == "__main__":
    run_summarizer_worker()
