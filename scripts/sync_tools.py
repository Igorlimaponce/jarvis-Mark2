from __future__ import annotations

import os
import sys
from pathlib import Path

# Adiciona o diretório raiz ao sys.path para importações de módulos do projeto
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

from loguru import logger
from sqlalchemy.orm import Session

from database.connection import get_session_local
from database.models import Tool
from tools.__all_tools__ import get_all_tools

def sync_tools_to_db():
    """
    Sincroniza as ferramentas definidas no código Python com a tabela 'tools' no banco de dados.
    """
    logger.info("Iniciando sincronização de ferramentas com o banco de dados...")
    SessionLocal = get_session_local()
    
    with SessionLocal() as db:
        try:
            tools_from_code = get_all_tools()
            
            for tool_from_code in tools_from_code:
                tool_name = tool_from_code.name
                tool_description = tool_from_code.description
                
                # Verifica se a ferramenta já existe no DB
                tool_db = db.query(Tool).filter(Tool.name == tool_name).first()
                
                if not tool_db:
                    logger.info(f"Adicionando nova ferramenta ao DB: '{tool_name}'")
                    new_tool = Tool(
                        name=tool_name,
                        description=tool_description,
                        # O schema dos parâmetros pode ser adicionado aqui se as ferramentas usarem Pydantic
                        parameters_schema=tool_from_code.args,
                    )
                    db.add(new_tool)
                elif tool_db.description != tool_description:
                    logger.info(f"Atualizando descrição da ferramenta no DB: '{tool_name}'")
                    tool_db.description = tool_description
            
            db.commit()
            logger.success("Sincronização de ferramentas concluída com sucesso.")
        except Exception as e:
            logger.opt(exception=True).error(f"Falha ao sincronizar ferramentas: {e}")
            db.rollback()

if __name__ == "__main__":
    sync_tools_to_db()
