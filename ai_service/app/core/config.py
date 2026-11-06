from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore",
    }

    app_name: str = "Home Loan Assistant"
    database_url: str = ""
    knowledge_snapshot_dir: str = "./data/snapshots"
    embedding_base_url: str = ""
    embedding_model: str = ""
    embedding_dimensions: int = 1536
    llm_api_key: str = ""
    data_encryption_key_base64: str = ""
    llm_base_url: str = ""
    llm_model: str = ""
    llm_timeout_seconds: float = 45.0

    @property
    def embedding_api_key(self) -> str:
        return self.llm_api_key

def get_settings() -> Settings:
    return Settings()
