from __future__ import annotations

import os
from typing import List

from langchain.tools import tool


@tool
def list_directory_contents(directory: str) -> List[str]:
	"""
	Retorna uma lista de arquivos e pastas em um diretório específico.
	Use esta ferramenta para explorar o sistema de arquivos local.
	"""
	try:
		return os.listdir(directory)
	except FileNotFoundError:
		return []
	except Exception as e:
		return [f"Erro: {str(e)}"]
