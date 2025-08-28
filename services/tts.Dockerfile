# Arquivo de configuração do Docker para o serviço TTS

# Use uma imagem base do Python
FROM python:3.11-slim

# Instala dependências do sistema necessárias para o Coqui TTS
# `libsndfile1` é crucial para manipulação de áudio.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instala o Rust, que é uma dependência para compilar o `tokenizers` usado pelo TTS
ENV PATH="/root/.cargo/bin:${PATH}"
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# Define o diretório de trabalho no contêiner
WORKDIR /app

# Copia os arquivos de dependências
COPY services/tts_requirements.txt requirements.txt

# Instala as dependências Python
# O --no-cache-dir é uma boa prática para manter a imagem menor
RUN pip install --no-cache-dir --timeout=600 -r requirements.txt

# Copia seletivamente apenas o código necessário
COPY ./services/tts_service.py /app/services/tts_service.py
COPY ./services/common/ /app/services/common/
COPY ./config/ /app/config/
COPY ./database/ /app/database/
RUN touch services/__init__.py

ENV PYTHONPATH=/app

# Comando para iniciar o serviço
CMD ["python", "-m", "services.tts_service"]
