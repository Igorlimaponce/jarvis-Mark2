from __future__ import annotations
from langchain.tools import tool
from neo4j import GraphDatabase
import os

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

@tool
def query_knowledge_graph(query: str) -> str:
    """
    Use esta ferramenta para fazer perguntas complexas sobre entidades e suas relações que foram mencionadas em conversas passadas.
    É ideal para perguntas como 'O que você sabe sobre o Projeto X?' ou 'Quem está relacionado a Y?'.
    A query deve ser uma pergunta em linguagem natural sobre uma entidade.
    """
    try:
        # Simplificação: Apenas busca a entidade. Uma versão avançada traduziria a NLQ para Cypher.
        entity_name = query.strip() 
        with driver.session() as session:
            result = session.run("MATCH (n:Entity) WHERE n.name =~ $name RETURN n.name as name, n.label as label LIMIT 10", 
                                 name=f"(?i).*{entity_name}.*")
            records = list(result)
            if not records:
                return f"Nenhuma entidade encontrada com o nome '{entity_name}' na memória."
            
            response = "Entidades encontradas na memória:\n"
            for record in records:
                response += f"- {record['name']} (Tipo: {record['label']})\n"
            return response
    except Exception as e:
        return f"Erro ao consultar a memória do grafo: {e}"
