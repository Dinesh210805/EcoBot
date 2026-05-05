from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM APIs
    groq_api_key: str
    gemini_api_key: str
    exa_api_key: str

    # Classifier
    classifier_mode: str = "ollama"  # "ollama" | "groq"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "ecobot-classifier"

    # Groq model names
    groq_response_model: str = "llama3-70b-8192"
    groq_vision_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    groq_classifier_model: str = "llama3-70b-8192"

    # Databases
    sqlite_db_path: str = "./data/ecobot.db"
    chroma_db_path: str = "./embeddings/chroma_db"

    # ChromaDB collection names
    chroma_disposal_collection: str = "disposal_guides"
    chroma_facts_collection: str = "env_facts"
    chroma_products_collection: str = "product_kb"

    # RAG
    rag_top_k: int = 3
    rag_similarity_threshold: float = 0.70
    exa_search_num_results: int = 3

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    rate_limit: str = "60/minute"

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    max_batch_size: int = 20
    max_image_size_mb: int = 10
    upload_dir: str = "./tmp/uploads"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def use_ollama(self) -> bool:
        return self.classifier_mode == "ollama"


@lru_cache
def get_settings() -> Settings:
    return Settings()
