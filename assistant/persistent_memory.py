from __future__ import annotations
from typing import Any, Dict, List

from langchain.memory import ConversationBufferMemory
from langchain_core.messages import BaseMessage, messages_from_dict, messages_to_dict
from sqlalchemy.orm import Session
from loguru import logger # Adicionar import para logging

from database.models import ConversationMessage as HistoryModel, ConversationSession as SessionModel, User
class PGConversationMemory(ConversationBufferMemory):
    session_id: str
    db_session: Session

    def __init__(self, session_id: str, db_session: Session, **kwargs):
        super().__init__(**kwargs)
        self.session_id = session_id
        self.db_session = db_session
        self._load_messages()

    def _load_messages(self):
        """Carrega o histórico da sessão do banco de dados."""
        session = self.db_session.query(SessionModel).filter(SessionModel.session_id == self.session_id).first()
        if session and session.messages:
            loaded_messages = [messages_from_dict([h.content])[0] for h in session.messages]
            self.chat_memory.messages.extend(loaded_messages)

    # --- NOVO MÉTODO PRIVADO PARA CENTRALIZAR A LÓGICA ---
    def _get_or_create_session(self) -> SessionModel:
        """Busca a sessão de conversa no DB ou cria uma nova se não existir."""
        session = self.db_session.query(SessionModel).filter(SessionModel.session_id == self.session_id).first()
        if session:
            return session

        # A lógica de criação agora está em um único lugar.
        logger.info(f"Sessão de conversa não encontrada para o id '{self.session_id}'. Criando uma nova.")
        user = self.db_session.query(User).filter_by(username="igor").first()
        if not user:
            # Em um sistema real, isso deveria levantar um erro ou criar o usuário
            raise ValueError("Usuário padrão 'igor' não encontrado no banco de dados.")
        
        new_session = SessionModel(session_id=self.session_id, user_id=user.user_id)
        self.db_session.add(new_session)
        self.db_session.flush() # Garante que a sessão tenha um ID antes do commit
        return new_session

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """Salva o contexto da interação no banco de dados, não apenas na memória."""
        super().save_context(inputs, outputs)
        messages_to_save = messages_to_dict(self.chat_memory.messages[-2:])
        
        # USA O MÉTODO CENTRALIZADO
        session = self._get_or_create_session()

        for msg_dict in messages_to_save:
            history_entry = HistoryModel(
                session_id=session.id,
                role=msg_dict.get('type'),
                content=msg_dict,
            )
            self.db_session.add(history_entry)
        
        self.db_session.commit()

    def save_message_and_get_id(self, message_dict: dict) -> int | None:
        """Salva uma única mensagem no histórico e retorna seu ID no banco de dados."""
        # USA O MÉTODO CENTRALIZADO
        session = self._get_or_create_session()

        history_entry = HistoryModel(
            session_id=session.id,
            role=message_dict.get("type"),
            content=message_dict,
        )
        self.db_session.add(history_entry)
        self.db_session.commit()
        return history_entry.message_id
