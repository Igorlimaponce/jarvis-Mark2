"""Conexão com o banco de dados e inicialização do schema."""
from __future__ import annotations

from pathlib import Path
import time
from typing import Generator

from loguru import logger
from sqlalchemy import create_engine, text, Engine
from sqlalchemy.orm import sessionmaker, Session

from config.settings import settings, ROOT_DIR

# --- CORREÇÃO PRINCIPAL ---
# O engine agora é criado diretamente no nível do módulo, permitindo a importação.
# A DSN (string de conexão) vem do seu objeto de configurações.
engine: Engine = create_engine(settings.db.dsn, echo=False, pool_pre_ping=True, future=True)

# A fábrica de sessões também é criada aqui.
SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, future=True
)

def get_db() -> Generator[Session, None, None]:
    """Dependência do FastAPI para obter uma sessão de banco de dados."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db_if_needed() -> None:
    """Aplica o schema.sql se as tabelas ainda não existirem."""
    # A função agora usa o 'engine' global.
    attempts = 0
    while True:
        try:
            conn = engine.connect()
            break
        except Exception as e:
            attempts += 1
            if attempts > 20:
                raise
            logger.warning(f"DB indisponível, tentando novamente ({attempts})... {e}")
            time.sleep(1.5)

    with conn:
        exists = conn.execute(
            text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'users')"
            )
        ).scalar()

        if exists:
            logger.info("Schema já existente. Nenhuma ação necessária.")
            return

        schema_path = ROOT_DIR / "database" / "schema.sql"
        logger.info(f"Aplicando schema do arquivo: {schema_path}")
        sql = Path(schema_path).read_text(encoding="utf-8")
        
        # Executa múltiplas instruções do arquivo .sql
        for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
            conn.execute(text(stmt))
        conn.commit()
        logger.success("Schema aplicado com sucesso.")


# Exporta os objetos necessários para outros arquivos
__all__ = ["engine", "get_db", "init_db_if_needed", "SessionLocal"]