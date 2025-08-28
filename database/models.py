"""Modelos ORM equivalentes ao schema.sql."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
	JSON,
	Boolean,
	Column,
	ForeignKey,
	Integer,
	String,
	Text,
	TIMESTAMP,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
	pass


class User(Base):
	__tablename__ = "users"

	user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
	username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
	preferences: Mapped[Optional[dict]] = mapped_column(JSON)
	created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))

	sessions: Mapped[list[ConversationSession]] = relationship("ConversationSession", back_populates="user")


class ConversationSession(Base):
	__tablename__ = "conversation_sessions"

	session_id: Mapped[int] = mapped_column(Integer, primary_key=True)
	user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
	start_time: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
	summary: Mapped[Optional[str]] = mapped_column(Text)
	is_summarized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
	
	user: Mapped[User] = relationship("User", back_populates="sessions")
	messages: Mapped[list[ConversationMessage]] = relationship("ConversationMessage", back_populates="session")


class ConversationMessage(Base):
	__tablename__ = "conversation_history"

	message_id: Mapped[int] = mapped_column(Integer, primary_key=True)
	session_id: Mapped[int] = mapped_column(ForeignKey("conversation_sessions.session_id"), nullable=False)
	role: Mapped[str] = mapped_column(String(50), nullable=False)
	content: Mapped[str] = mapped_column(Text, nullable=False)
	timestamp: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
	metadata: Mapped[Optional[dict]] = mapped_column(JSON)

	session: Mapped[ConversationSession] = relationship("ConversationSession", back_populates="messages")
	tool_usages: Mapped[list[ToolUsageLog]] = relationship("ToolUsageLog", back_populates="message")


class Tool(Base):
	__tablename__ = "tools"

	tool_id: Mapped[int] = mapped_column(Integer, primary_key=True)
	name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
	description: Mapped[str] = mapped_column(Text, nullable=False)
	parameters_schema: Mapped[Optional[dict]] = mapped_column(JSON)
	is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
	created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))

	usage_logs: Mapped[list["ToolUsageLog"]] = relationship("ToolUsageLog", back_populates="tool")


class ToolUsageLog(Base):
	__tablename__ = "tool_usage_logs"

	log_id: Mapped[int] = mapped_column(Integer, primary_key=True)
	message_id: Mapped[int] = mapped_column(ForeignKey("conversation_history.message_id"), nullable=False)
	tool_id: Mapped[int] = mapped_column(ForeignKey("tools.tool_id"), nullable=False)
	call_parameters: Mapped[Optional[dict]] = mapped_column(JSON)
	output: Mapped[Optional[str]] = mapped_column(Text)
	status: Mapped[str] = mapped_column(String(50), nullable=False)
	timestamp: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))

	message: Mapped[ConversationMessage] = relationship("ConversationMessage", back_populates="tool_usages")
	tool: Mapped["Tool"] = relationship("Tool", back_populates="usage_logs")


class ScheduledTask(Base):
	__tablename__ = "scheduled_tasks"

	task_id: Mapped[int] = mapped_column(Integer, primary_key=True)
	user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
	task_description: Mapped[str] = mapped_column(Text, nullable=False)
	due_time: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
	status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
	created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))

	user: Mapped[User] = relationship("User")


class KnowledgeBaseDocument(Base):
	__tablename__ = "knowledge_base_documents"

	document_id: Mapped[int] = mapped_column(Integer, primary_key=True)
	source_path: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
	document_type: Mapped[Optional[str]] = mapped_column(String(50))
	metadata: Mapped[Optional[dict]] = mapped_column(JSON)
	last_indexed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
	chromadb_collection_name: Mapped[Optional[str]] = mapped_column(String(255))
