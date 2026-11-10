"""基于 Pydantic Settings 的统一配置管理。"""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 大模型
    OPENAI_API_KEY: str = ""
    BASE_URL: str = "https://api.openai.com/v1"
    MODEL_NAME: str = "gpt-4o-mini"
    TEMPERATURE: float = 0.3

    # JWT 鉴权
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # LangSmith 可观测性
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "health-agent"

    # 服务
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = False

    # 数据库与向量库
    DB_PATH: str = "./health_agent.db"
    CHROMA_PERSIST_DIR: str = "./chroma_db"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
