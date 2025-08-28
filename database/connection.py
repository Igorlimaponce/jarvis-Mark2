"""Conexão com o banco de dados e inicialização do schema."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Generator, Optional

from loguru import logger
import time
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

from config.settings import settings, ROOT_DIR
from .models import Base


_engine: Optional[Engine] = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine(echo: bool = False) -> Engine:
	global _engine
	if _engine is None:
		# A DSN agora vem diretamente do objeto de settings
		_engine = create_engine(settings.db.dsn, echo=echo, pool_pre_ping=True, future=True)
	return _engine


def get_session_local() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=get_engine(), future=True
        )
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency to get a DB session."""
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db_if_needed() -> None:
	"""Aplica o schema.sql se as tabelas ainda não existirem.

	Verificação: procura pela tabela 'users' no information_schema.
	"""
	engine = get_engine()
	# Aguarda DB ficar pronto (retry simples)
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
				"""
				SELECT EXISTS (
					SELECT FROM information_schema.tables 
					WHERE table_schema = 'public' AND table_name = 'users'
				)
				"""
			)
		).scalar()
		if exists:
			logger.info("Schema já existente. Nenhuma ação necessária.")
			return
		schema_path = ROOT_DIR / "database" / "schema.sql"
		logger.info(f"Aplicando schema do arquivo: {schema_path}")
		sql = Path(schema_path).read_text(encoding="utf-8")
		# Executa múltiplas instruções
		for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
			conn.execute(text(stmt))
		conn.commit()
		logger.success("Schema aplicado com sucesso.")


__all__ = ["get_engine", "get_db", "init_db_if_needed"]

