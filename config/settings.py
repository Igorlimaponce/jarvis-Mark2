from __future__ import annotations

from pathlib import Path
from typing import ClassVar
from dotenv import load_dotenv
from pydantic import Field, PostgresDsn, HttpUrl, AmqpDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


load_dotenv()
# --- Sub-modelos para Configurações Aninhadas ---

class AppSettings(BaseSettings):
    """Configurações gerais da aplicação."""
    wake_word: str = "jarvis"
    log_level: str = "INFO"
    summarizer_interval_seconds: int = 300  # <-- ADICIONE ESTA LINHA

class DBSettings(BaseSettings):
    """Configurações do banco de dados PostgreSQL."""
    model_config = SettingsConfigDict(env_prefix='POSTGRES_')

    HOST: str = "localhost"
    PORT: int = 5432
    USER: str
    PASSWORD: str
    DB: str


    @property
    def dsn(self) -> str:
        """Retorna a Data Source Name (DSN) para conexão com o banco."""
        return str(
            PostgresDsn.build(
                scheme="postgresql",
                username=self.USER,
                password=self.PASSWORD,
                host=self.HOST,
                port=self.PORT,
                path=self.DB,
            )
        )

class LLMSettings(BaseSettings):
    """Configurações para o serviço do LLM."""
    base_url: HttpUrl = "http://localhost:11434"
    model: str = "llama3:latest"
    temperature: float = 0.2

class STTSettings(BaseSettings):
    """Configurações para o serviço de Speech-to-Text."""
    model_path: str = "models/stt/vosk-model-small-pt-0.3"

class TTSSettings(BaseSettings):
    """Configurações para o serviço de Text-to-Speech."""
    model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2"
    speaker_wav: str = ""

class APISettings(BaseSettings):
    """Configurações para as APIs externas e internas."""
    orchestrator_url: HttpUrl = "http://localhost:8000"

class PorcupineSettings(BaseSettings):
    """Configurações para o detector de wake word Porcupine."""
    access_key: str
    keyword: str = "jarvis"

class RabbitMQSettings(BaseSettings):
    """Configurações para o message broker RabbitMQ."""
    # Ex: amqp://user:password@host:port/
    url: AmqpDsn = Field(..., alias='RABBITMQ_URL')


# --- Classe Principal de Configurações ---

class Settings(BaseSettings):
    """
    Agrega todas as configurações da aplicação, carregando-as de
    variáveis de ambiente e de um arquivo .env.
    """
    # Configura o Pydantic para ler de um arquivo .env e usar '__' como delimitador
    # para variáveis de ambiente aninhadas (ex: DB__HOST).
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env", env_nested_delimiter="__", env_file_encoding="utf-8", extra="ignore"
    )

    # Mapeia as variáveis de ambiente para as classes de configuração
    app: AppSettings = Field(default_factory=AppSettings)
    db: DBSettings = Field(default_factory=DBSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    stt: STTSettings = Field(default_factory=STTSettings)
    tts: TTSSettings = Field(default_factory=TTSSettings)
    api: APISettings = Field(default_factory=APISettings)
    porcupine: PorcupineSettings | None = None
    rabbitmq: RabbitMQSettings = Field(default_factory=RabbitMQSettings)

    # Variáveis de ambiente que não se encaixam em um grupo
    # (serão substituídas por referências diretas no docker-compose)
    stt_service_url: HttpUrl | None = None
    tts_service_url: HttpUrl | None = None
    llm_service_url: HttpUrl | None = None


# --- Instância Singleton ---
# Esta instância será importada e usada em toda a aplicação.
settings = Settings()

# --- Constantes Globais ---
# Para evitar a necessidade de recalcular o diretório raiz em vários lugares.
ROOT_DIR = Path(__file__).parent.parent
