from __future__ import annotations

import operator
from typing import Annotated, TypedDict, Union, Optional
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import BaseMessage
from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session
from loguru import logger

from assistant.agent_core import get_llm
from tools.__all_tools__ import get_all_tools, call_tool
from database.models import Tool, ToolUsageLog


class AgentState(TypedDict):
    """Define o estado do nosso agente. Este estado é passado entre os nós do grafo."""
    messages: Annotated[list[BaseMessage], operator.add]
    sender: str
    db_session: Optional[Session] = None
    message_db_id: Optional[int] = None


def create_graph_workflow() -> StateGraph:
    """Cria e configura o grafo de estados para o agente."""
    
    llm = get_llm()
    tools = get_all_tools()
    # Vincula as ferramentas ao LLM para que ele saiba quando e como chamá-las
    tools_as_openai = [convert_to_openai_tool(t) for t in tools]

# 2. Anexa as ferramentas convertidas ao modelo usando o método .bind()
    llm_with_tools = llm.bind(tools=tools_as_openai)
    # --- Nós do Grafo ---

    def agent_node(state: AgentState):
        """Nó principal: invoca o LLM para decidir o próximo passo."""
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response], "sender": "agent"}

    def tool_node(state: AgentState):
        """Nó de ferramentas: executa a ferramenta e REGISTRA o uso."""
        tool_outputs = []
        db = state.get("db_session")
        message_id = state.get("message_db_id")
        last_agent_message = state["messages"][-1]
        tool_calls = last_agent_message.tool_calls

        # --- INÍCIO DA MODIFICAÇÃO PARA FEEDBACK ---
        # Se uma ferramenta potencialmente lenta for chamada, podemos adicionar um metadado.
        # A lógica real do TTS de feedback viverá no orchestrator, mas o sinal pode vir daqui.
        feedback_message = None
        for tool_call in tool_calls:
            if tool_call.get("name") in ["web_search", "search_knowledge_base"]:
                feedback_message = "Só um momento, estou pesquisando isso para você."
                break # Apenas um feedback é necessário
        # --- FIM DA MODIFICAÇÃO ---

        for tool_call in tool_calls:
            tool_output = call_tool(tool_call)
            tool_outputs.append(tool_output)

            # --- LÓGICA DE LOGGING ADICIONADA ---
            if db and message_id:
                try:
                    tool_name = tool_call.get("name")
                    # Busca o ID da ferramenta no banco de dados
                    tool_db_entry = db.query(Tool).filter(Tool.name == tool_name).first()

                    if tool_db_entry:
                        log_entry = ToolUsageLog(
                            message_id=message_id,
                            tool_id=tool_db_entry.tool_id,
                            call_parameters=tool_call.get("args"),
                            output=str(tool_output.content),
                            status="success" # Adicionar tratamento de erro para status "error"
                        )
                        db.add(log_entry)
                        db.commit()
                except Exception as e:
                    logger.opt(exception=True).error(f"Falha ao registrar uso da ferramenta: {e}")
                    db.rollback()
            # --- FIM DA LÓGICA DE LOGGING ---
        
        # O estado pode ser aumentado para incluir a mensagem de feedback
        # return {"messages": tool_outputs, "sender": "tool", "feedback": feedback_message}
        # Por simplicidade, vamos manter a lógica de TTS apenas no orchestrator por enquanto.
        return {"messages": tool_outputs, "sender": "tool"}

    # --- Arestas Condicionais ---

    def should_continue(state: AgentState) -> str:
        """
        Decide o próximo passo. Se o LLM chamou uma ferramenta, vai para o nó de ferramentas.
        Caso contrário, finaliza o fluxo.
        """
        last_message = state["messages"][-1]
        if last_message.tool_calls:
            return "tool"
        return END

    # --- Construção do Grafo ---

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tool", tool_node)
    
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue)
    workflow.add_edge("tool", "agent")

    return workflow.compile()

# Compila o grafo na inicialização para ser reutilizado
app_graph = create_graph_workflow()
