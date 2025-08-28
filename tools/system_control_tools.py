from __future__ import annotations

import subprocess
import sys

from langchain.tools import tool


@tool
def open_application(app_name: str) -> str:
	"""
	Abre uma aplicação no computador do usuário.
	Exemplo de uso: 'abra o firefox' ou 'inicie o terminal'.
	"""
	try:
		if sys.platform == "win32":
			subprocess.Popen([app_name])
		elif sys.platform == "darwin":  # macOS
			subprocess.Popen(["open", "-a", app_name])
		else:  # linux
			subprocess.Popen([app_name])
		return f"Aplicação '{app_name}' iniciada com sucesso."
	except Exception as e:
		return f"Erro ao iniciar a aplicação '{app_name}': {str(e)}"
