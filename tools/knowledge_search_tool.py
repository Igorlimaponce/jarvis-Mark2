from __future__ import annotations

from langchain.tools import tool
from langchain_community.embeddings import OllamaEmbeddings
from langchain_chroma import Chroma

from config.settings import settings, ROOT_DIR


@tool
def search_knowledge_base(query: str) -> str:
    """
    Use esta ferramenta para responder a perguntas sobre os documentos pessoais e a base de conhecimento do usuário.
    É a fonte principal para informações específicas, arquivos e notas que o usuário forneceu.
    Não a use para perguntas gerais que podem ser respondidas sem conhecimento específico.
    """
    vector_store_path = str(ROOT_DIR / "data" / "vector_store")

    embedding_function = OllamaEmbeddings(
        model=settings.llm.model, base_url=str(settings.llm.base_url)
    )

    vector_store = Chroma(
        persist_directory=vector_store_path, embedding_function=embedding_function
    )

    results = vector_store.similarity_search(query, k=3)

    if not results:
        return "Nenhuma informação relevante encontrada na base de conhecimento."

    context = "\n---\n".join([doc.page_content for doc in results])
    return f"Informação encontrada na base de conhecimento:\n{context}"