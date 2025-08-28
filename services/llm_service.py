from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from loguru import logger

from config.settings import settings

class ChatMessage(BaseModel):
	role: str
	content: str


class ChatRequest(BaseModel):
	messages: List[ChatMessage]
	model: Optional[str] = None
	tools: Optional[List[Dict[str, Any]]] = None
	temperature: Optional[float] = 0.2


class ChatResponse(BaseModel):
	content: str
	raw: Dict[str, Any]


app = FastAPI(title="LLM Service", version="1.0")


@app.get("/health")
async def health() -> Dict[str, str]:
	return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
	base_url = str(settings.llm.base_url).rstrip("/")
	# Proxy para API compatível (Ollama chat/openai-like)
	payload = {
		"model": req.model or settings.llm.model,
		"messages": [m.model_dump() for m in req.messages],
		"temperature": req.temperature or settings.llm.temperature,
	}
	if req.tools:
		payload["tools"] = req.tools

	logger.debug(f"Enviando para LLM backend {base_url}: {payload.keys()}")
	try:
		async with httpx.AsyncClient(timeout=120) as client:
			# Ollama: POST /api/chat
			# OpenAI:  POST /v1/chat/completions
			# Detecta caminho por heurística simples
			if "openai.com" in base_url or base_url.endswith("/v1/chat/completions"):
				url = base_url
			else:
				url = f"{base_url}/api/chat"
			resp = await client.post(url, json=payload)
			resp.raise_for_status()
			data = resp.json()
	except httpx.HTTPError as e:
		logger.exception("Erro ao contatar LLM backend")
		raise HTTPException(status_code=502, detail=str(e))

	# Normalização simples de resposta
	content: str = ""
	if "message" in data and isinstance(data["message"], dict):
		content = data["message"].get("content", "")
	elif "choices" in data and data["choices"]:
		content = data["choices"][0]["message"]["content"]
	else:
		content = data.get("content", "")

	return ChatResponse(content=content, raw=data)


# Execução local com: uvicorn services.llm_service:app --reload --port 8002
