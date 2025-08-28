import os
import pytest

import requests


@pytest.mark.skipif(os.getenv("CI") == "true", reason="Requer serviços rodando")
def test_health_endpoints():
	for url in [
		os.getenv("ORCH_URL", "http://localhost:8000/health"),
		os.getenv("STT_URL", "http://localhost:8001/health"),
		os.getenv("LLM_URL", "http://localhost:8002/health"),
		os.getenv("TTS_URL", "http://localhost:8003/health"),
	]:
		r = requests.get(url, timeout=3)
		assert r.status_code == 200
		assert r.json().get("status") == "ok"
