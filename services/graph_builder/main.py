import pika
import spacy
from neo4j import GraphDatabase
from loguru import logger
import os
import json
from langchain.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from services.common.mq_client import MQClient

# Carregar modelo Spacy
try:
    nlp = spacy.load("pt_core_news_lg")
except OSError:
    print("Downloading spacy model...")
    from spacy.cli import download
    download("pt_core_news_lg")
    nlp = spacy.load("pt_core_news_lg")


# Configurações do Neo4j
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# Configuração do LLM para extração de relações
llm = Ollama(model="llama3")

prompt_template = """
A partir do texto a seguir, extraia as entidades (pessoas, organizações, locais, etc.) e as relações entre elas.
Retorne o resultado em formato JSON com duas chaves: 'entities' e 'relationships'.
'entities' deve ser uma lista de dicionários, cada um com 'name' e 'type'.
'relationships' deve ser uma lista de dicionários, cada um com 'source', 'target' e 'type'.

Texto: "{text}"

JSON:
"""
PROMPT = PromptTemplate(template=prompt_template, input_variables=["text"])
chain = LLMChain(llm=llm, prompt=PROMPT)

def add_graph_data(tx, data):
    entities = data.get('entities', [])
    relationships = data.get('relationships', [])

    for entity in entities:
        tx.run("MERGE (n:Entity {name: $name, label: $label})", name=entity['name'], label=entity['type'])

    for rel in relationships:
        tx.run(
            '''
            MATCH (a:Entity {name: $source})
            MATCH (b:Entity {name: $target})
            MERGE (a)-[r:RELATIONSHIP {type: $type}]->(b)
            ''',
            source=rel['source'],
            target=rel['target'],
            type=rel['type']
        )

def process_message(ch, method, props, body):
    try:
        message_data = json.loads(body)
        user_text = message_data.get("user_text", "")
        assistant_text = message_data.get("assistant_text", "")

        full_text = f"{user_text}. {assistant_text}"
        
        # Extrair entidades e relações com o LLM
        llm_result = chain.run(full_text)
        graph_data = json.loads(llm_result)

        with driver.session() as session:
            session.execute_write(add_graph_data, graph_data)
        
        logger.info(f"Processado e adicionado ao grafo: {full_text[:50]}...")
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.exception(f"Falha ao processar mensagem para o grafo: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag)


if __name__ == "__main__":
    logger.info("Serviço Graph Builder iniciado. Aguardando mensagens...")
    mq_client = MQClient()
    mq_client.declare_queue("graph_builder_queue")
    mq_client.start_worker("graph_builder_queue", process_message)
    driver.close()
