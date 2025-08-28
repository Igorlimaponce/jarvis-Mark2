from __future__ import annotations

import re
from typing import List

import requests
from langchain.tools import tool


@tool
def web_search(query: str, limit: int = 5) -> List[str]:
	"""
	Faz uma busca web simples e retorna títulos/links.
	Placeholder com DuckDuckGo HTML.
	"""
	try:
		resp = requests.get("https://duckduckgo.com/html/", params={"q": query}, timeout=10)
		resp.raise_for_status()
		# Extrai links básicos
		links = re.findall(r'<a rel="nofollow" class="result__a" href="(.*?)".*?>(.*?)</a>', resp.text)
		results = []
		for href, title_html in links[:limit]:
			title = re.sub(r"<.*?>", "", title_html)
			results.append(f"{title} - {href}")
		return results
	except Exception as e:
		return [f"Erro na busca: {str(e)}"]
