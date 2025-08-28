# Arquivo de configuração do Docker para o serviço STT

# Use uma imagem base do Python
FROM python:3.11-slim

# Define o diretório de trabalho no contêiner
WORKDIR /app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgfortran5 \
    portaudio19-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instala o Rust, que é uma dependência para compilar `sudachipy`
ENV PATH="/root/.cargo/bin:${PATH}"
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# Copia e instala dependências Python primeiro para aproveitar o cache
COPY services/stt_requirements.txt requirements.txt
RUN pip install --no-cache-dir --timeout=600 -r requirements.txt

# Copia seletivamente apenas o código necessário para este serviço
COPY ./services/stt_service.py /app/services/stt_service.py
COPY ./services/common/ /app/services/common/
COPY ./config/ /app/config/
COPY ./database/ /app/database/
# Adiciona um __init__.py vazio para tornar 'services' um pacote
RUN touch services/__init__.py

ENV PYTHONPATH=/app

# Executa o worker diretamente com Python, já que não é mais um serviço web
CMD ["python", "-m", "services.stt_service"]
