from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from langchain.agents import AgentExecutor, AgentType, initialize_agent
from langchain.chat_models.base import BaseChatModel
from langchain.memory import ConversationBufferMemory
from langchain.prompts import MessagesPlaceholder
from langchain_community.chat_models import ChatOllama

from config.settings import settings
from tools.__all_tools__ import get_all_tools

router = APIRouter(prefix="/agent", tags=["agent"])


def get_llm() -> BaseChatModel:
    """Factory function to get the LLM instance based on config."""
    # A URL do serviço LLM pode vir de uma variável de ambiente específica
    # ou do base_url definido nas configurações do LLM.
    llm_service_url = settings.llm_service_url or settings.llm.base_url
    
    return ChatOllama(
        base_url=str(llm_service_url),
        model=settings.llm.model,
        temperature=settings.llm.temperature,
    )


from .agent_graph import app_graph

def get_agent_graph():
    """Retorna o grafo de agente compilado."""
    # O grafo já é compilado na importação, então apenas o retornamos.
    # Lógica adicional pode ser adicionada aqui se a injeção de dependências
    # no grafo se tornar necessária no futuro.
    return app_graph
