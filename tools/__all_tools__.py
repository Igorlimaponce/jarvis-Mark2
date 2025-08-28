"""Registro de ferramentas disponíveis para o agente."""
from __future__ import annotations

from langchain_core.tools import BaseTool, tool
from langchain.tools import Tool
from langchain_core.messages import ToolMessage
from typing import List

from .file_system_tools import list_directory_contents
from .system_control_tools import open_application
from .web_search_tools import web_search
from .knowledge_search_tool import search_knowledge_base
from .knowledge_graph_tools import query_knowledge_graph


def get_all_tools() -> List:
	return [
		list_directory_contents,
		open_application,
		web_search,
		search_knowledge_base,
		query_knowledge_graph,
	]

def call_tool(tool_call: dict) -> ToolMessage:
    """
    Executa uma ferramenta com base no dicionário de chamada de ferramenta do LangChain.

    Args:
        tool_call: Um dicionário contendo 'name' e 'args' da ferramenta a ser chamada.

    Returns:
        Um ToolMessage com o resultado da execução da ferramenta.
    """
    all_tools = {t.name: t for t in get_all_tools()}
    tool_name = tool_call.get("name")
    tool_to_call = all_tools.get(tool_name)

    if not tool_to_call:
        return ToolMessage(
            content=f"Erro: A ferramenta '{tool_name}' não foi encontrada.",
            tool_call_id=tool_call.get("id"),
        )

    try:
        output = tool_to_call.invoke(tool_call.get("args"))
        return ToolMessage(
            content=str(output),
            tool_call_id=tool_call.get("id"),
        )
    except Exception as e:
        return ToolMessage(
            content=f"Erro ao executar a ferramenta '{tool_name}': {e}",
            tool_call_id=tool_call.get("id"),
        )


__all__ = ["get_all_tools"]
