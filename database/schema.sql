-- Tabela para armazenar informações e preferências do usuário.
-- Essencial para a personalização do assistente.
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    -- O campo JSONB é ideal para armazenar configurações flexíveis como nome,
    -- localização para previsão do tempo, unidades preferidas (métrica/imperial), etc.
    preferences JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabela para agrupar interações em sessões de conversa distintas.
-- Facilita a recuperação do histórico e a criação de resumos para a memória de longo prazo.
CREATE TABLE conversation_sessions (
    session_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    start_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- Um resumo gerado pelo LLM no final da sessão pode ser armazenado aqui
    -- para alimentar a memória de longo prazo de forma eficiente.
    summary TEXT,
    is_summarized BOOLEAN NOT NULL DEFAULT FALSE
);

-- Tabela principal para registrar cada mensagem trocada.
-- Esta é a base para a memória de curto e longo prazo.
CREATE TABLE conversation_history (
    message_id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES conversation_sessions(session_id),
    -- 'user', 'assistant', 'system', ou 'tool' para identificar a origem da mensagem.
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- Metadados como o modelo de IA utilizado, latência da resposta,
    -- ou detalhes de uma chamada de ferramenta podem ser armazenados aqui.
    metadata JSONB
);

-- Tabela para registrar as ferramentas (skills) disponíveis para o assistente.
-- Permite que o sistema seja dinamicamente extensível.
CREATE TABLE tools (
    tool_id SERIAL PRIMARY KEY,
    -- Nome único da função, ex: 'get_current_weather', 'send_email'.
    name VARCHAR(255) UNIQUE NOT NULL,
    -- Descrição em linguagem natural que o LLM usará para decidir quando usar a ferramenta.
    description TEXT NOT NULL,
    -- Um JSON Schema definindo os parâmetros que a ferramenta aceita.
    parameters_schema JSONB,
    is_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabela para registrar cada vez que uma ferramenta é utilizada pelo agente.
-- Crucial para depuração e análise do comportamento do agente.
CREATE TABLE tool_usage_logs (
    log_id SERIAL PRIMARY KEY,
    -- Vincula a chamada da ferramenta à mensagem que a originou.
    message_id INTEGER NOT NULL REFERENCES conversation_history(message_id),
    tool_id INTEGER NOT NULL REFERENCES tools(tool_id),
    -- Os argumentos exatos passados para a ferramenta durante a chamada.
    call_parameters JSONB,
    -- O resultado (output) retornado pela ferramenta.
    output TEXT,
    -- 'success' ou 'error' para monitorar a confiabilidade das ferramentas.
    status VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabela para gerenciar tarefas agendadas, como lembretes e alarmes.
CREATE TABLE scheduled_tasks (
    task_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    task_description TEXT NOT NULL,
    due_time TIMESTAMP WITH TIME ZONE NOT NULL,
    -- 'pending', 'completed', 'missed'.
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabela para armazenar metadados sobre documentos na base de conhecimento (RAG).
-- Enquanto os vetores ficam no ChromaDB, esta tabela fornece o contexto relacional.
CREATE TABLE knowledge_base_documents (
    document_id SERIAL PRIMARY KEY,
    -- Caminho do arquivo, URL ou outro identificador único da fonte.
    source_path TEXT UNIQUE NOT NULL,
    -- 'pdf', 'txt', 'webpage', etc.
    document_type VARCHAR(50),
    -- Metadados como autor, data de criação do documento, etc.
    metadata JSONB,
    last_indexed_at TIMESTAMP WITH TIME ZONE,
    -- Nome da coleção no ChromaDB onde os vetores deste documento estão armazenados.
    chromadb_collection_name VARCHAR(255)
);

-- Inserir um usuário padrão para começar.
INSERT INTO users (username, preferences) VALUES ('igor', '{"name": "Usuário"}');