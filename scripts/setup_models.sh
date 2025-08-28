#!/usr/bin/env bash
set -euo pipefail

# --- Diretórios ---
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
ROOT_DIR=$(realpath "$SCRIPT_DIR/..")
MODELS_DIR="$ROOT_DIR/models"
STT_DIR="$MODELS_DIR/stt"
VOSK_MODEL_DIR="$STT_DIR/vosk-model-small-pt-0.3"
VOSK_MODEL_URL="https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip"
VOSK_ZIP_FILE="$STT_DIR/vosk-model.zip"

echo "================================================="
echo "Iniciando setup dos modelos para o Jarvis Mark II"
echo "================================================="
echo "Diretório raiz do projeto: $ROOT_DIR"
echo ""

# --- Ollama ---
echo "[1/3] Verificando Ollama..."
if ! command -v ollama &> /dev/null; then
    echo "AVISO: O comando 'ollama' não foi encontrado."
    echo "Por favor, instale o Ollama para ter a funcionalidade do LLM: https://ollama.com"
else
    echo "Ollama encontrado. Tentando baixar o modelo Llama 3 (pode levar tempo)..."
    # O `|| true` evita que o script pare se o pull falhar (ex: sem conexão)
    ollama pull llama3 || true
fi
echo "-------------------------------------------------"
echo ""

# --- Vosk (STT) ---
echo "[2/3] Configurando modelo Vosk (Speech-to-Text)..."
if [ -d "$VOSK_MODEL_DIR" ]; then
    echo "Diretório do modelo Vosk já existe em '$VOSK_MODEL_DIR'. Pulando download."
else
    echo "Diretório do modelo Vosk não encontrado. Baixando..."
    mkdir -p "$STT_DIR"
    
    # Usando curl para baixar o arquivo
    if command -v curl &> /dev/null; then
        curl -L "$VOSK_MODEL_URL" -o "$VOSK_ZIP_FILE"
    elif command -v wget &> /dev/null; then
        wget "$VOSK_MODEL_URL" -O "$VOSK_ZIP_FILE"
    else
        echo "ERRO: Nem 'curl' nem 'wget' foram encontrados. Não é possível baixar o modelo."
        exit 1
    fi
    
    echo "Download completo. Descompactando..."
    unzip "$VOSK_ZIP_FILE" -d "$STT_DIR"
    
    echo "Limpando arquivo zip..."
    rm "$VOSK_ZIP_FILE"
    
    echo "Modelo Vosk configurado com sucesso em '$VOSK_MODEL_DIR'."
fi
echo "-------------------------------------------------"
echo ""

# --- Coqui/Piper (TTS) ---
echo "[3/3] Configurando modelo Coqui (Text-to-Speech)..."
# O download do modelo Coqui é gerenciado pela própria biblioteca na primeira execução.
# Este passo apenas informa o usuário e cria o diretório de vozes de exemplo.
TTS_DIR="$MODELS_DIR/tts"
mkdir -p "$TTS_DIR"
echo "O modelo Coqui TTS será baixado automaticamente na primeira vez que o serviço for executado."
echo "Se você quiser usar a clonagem de voz, coloque seus arquivos .wav de amostra em '$TTS_DIR'."
echo "-------------------------------------------------"
echo ""

echo "================================================="
echo "Setup finalizado!"
echo "Lembre-se de configurar seu arquivo .env se ainda não o fez."
echo "================================================="

