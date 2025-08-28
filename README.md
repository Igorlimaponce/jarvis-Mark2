<<<<<<< HEAD
# jarvis-Mark2
=======
## Jarvis Mark II – Arquitetura de IA por Microsserviços

Este projeto implementa um assistente de IA pessoal, modular e local, inspirado no Jarvis. A arquitetura é baseada em microsserviços desacoplados que se comunicam via message queue (RabbitMQ), garantindo robustez e escalabilidade.

### Arquitetura
- **Orchestrator**: O cérebro do sistema, construído com FastAPI e LangGraph. Ele gerencia o fluxo da conversa, invoca o LLM e coordena os outros serviços.
- **STT (Speech-to-Text)**: Um worker que consome áudio da fila e o transcreve usando Vosk.
- **TTS (Text-to-Speech)**: Um worker que consome texto da fila e o sintetiza em áudio usando Coqui TTS.
- **Memory Summarizer**: Um serviço de background que analisa conversas passadas para extrair fatos e preferências, permitindo que o Jarvis aprenda com o tempo.
- **Cliente**: Uma aplicação standalone (`run_client.py`) que detecta a wake word, grava comandos e interage com o orquestrador.

### Pré-requisitos
- **Docker e Docker Compose**
- **Ollama**: Rodando localmente para servir o LLM (ex: `ollama pull llama3`).
- **Python 3.11+**

### Configuração
1.  **Chave do Picovoice:** Crie uma conta gratuita no [Picovoice Console](https://console.picovoice.ai/) para obter sua `AccessKey` para a detecção de wake word.
2.  **Arquivo de Ambiente:** Copie o arquivo `.env.example` para `.env`.
3.  **Preencha o `.env`:** Insira sua `PORCUPINE__ACCESS_KEY` e ajuste as outras variáveis, como as credenciais do banco de dados, se necessário.

### Execução
O projeto é projetado para ser executado com Docker Compose, que gerencia todos os serviços.

1.  **Baixar Modelos:**
    Execute o script de setup para baixar o modelo de STT.
    ```bash
    bash scripts/setup_models.sh
    ```

2.  **Iniciar os Serviços:**
    Use Docker Compose para construir e iniciar todos os contêineres em segundo plano.
    ```bash
    docker-compose up --build -d
    ```

3.  **Monitorar os Logs (Opcional):**
    Para ver os logs de todos os serviços em tempo real, use:
    ```bash
    docker-compose logs -f
    ```

4.  **Iniciar o Cliente:**
    Em um novo terminal, inicie o cliente para começar a interagir com o Jarvis por voz.
    ```bash
    python run_client.py
    ```
    Diga "Jarvis" e, após o sinal sonoro, faça seu comando.

### Base de Conhecimento (RAG)
Para que o Jarvis responda a perguntas sobre seus documentos, coloque arquivos (`.txt`, `.pdf`, `.md`) na pasta `knowledge_base/sources` e execute o indexador:
```bash
python knowledge_base/indexer.py
```

>>>>>>> 83502db (commit)
