# Este Dockerfile é para o serviço de sumarização de memória.
# Ele assume que a instalação das dependências é gerenciada pelo Dockerfile principal
# na raiz do projeto, para manter a consistência e o cache de layers.

FROM python:3.11-slim

WORKDIR /app

COPY services/memory_summarizer/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copia seletivamente o código do sumarizador e dependências comuns
COPY ./services/memory_summarizer/main.py /app/services/memory_summarizer/main.py
COPY ./services/common/ /app/services/common/
COPY ./config/ /app/config/
COPY ./database/ /app/database/
COPY ./assistant/ /app/assistant/
COPY ./tools/ /app/tools/
RUN touch services/__init__.py
RUN touch services/memory_summarizer/__init__.py

ENV PYTHONPATH=/app

# Executa o worker de sumarização
CMD ["python", "-m", "services.memory_summarizer.main"]
