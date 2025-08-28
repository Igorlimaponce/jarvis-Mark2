from __future__ import annotations

from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader
from langchain_community.embeddings import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from loguru import logger

from config.settings import settings, ROOT_DIR

# --- ADICIONE ESTAS DUAS LINHAS ---
KNOWLEDGE_BASE_DIR = ROOT_DIR / "knowledge_base" / "sources"
VECTOR_STORE_DIR = ROOT_DIR / "data" / "vector_store"
# ---------------------------------

def run_indexing():
    """
    Carrega documentos de um diretório, divide-os em pedaços,
    gera embeddings e os armazena em um banco de dados vetorial Chroma.
    """
    source_dir = KNOWLEDGE_BASE_DIR
    vector_store_path = VECTOR_STORE_DIR

    if not source_dir.exists() or not any(source_dir.iterdir()):
        logger.warning(
            f"Diretório da base de conhecimento '{source_dir}' está vazio ou não existe. "
            "Crie o diretório e adicione seus arquivos (.txt, .md, .pdf, etc.) para indexar."
        )
        return

    logger.info(f"Iniciando indexação do diretório: {source_dir}")

    # Carregar documentos
    loader = DirectoryLoader(str(source_dir), glob="**/*.*", show_progress=True)
    docs = loader.load()
    if not docs:
        logger.warning("Nenhum documento encontrado para indexar.")
        return

    logger.success(f"{len(docs)} documentos carregados.")

    # Dividir documentos em pedaços
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)
    logger.info(f"Documentos divididos em {len(splits)} pedaços.")

    # Gerar embeddings e armazenar no Chroma
    embedding_function = OllamaEmbeddings(
        model=settings.llm.model, base_url=str(settings.llm.base_url)
    )

    logger.info("Gerando embeddings e criando o banco de dados vetorial (pode levar tempo)...")
    vector_store = Chroma.from_documents(
        documents=splits,
        embedding=embedding_function,
        persist_directory=str(vector_store_path),
    )
    logger.success(f"Base de conhecimento criada e salva em: {vector_store_path}")


if __name__ == "__main__":
    run_indexing()