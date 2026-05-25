from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


class Settings(BaseSettings):
    app_name: str = "codex-agent-status-panel"
    app_version: str = "0.1.0"
    app_env: Literal["local", "test", "prod"] = "local"
    database_url: str = "sqlite:///./local_dev_agent_status_panel.db"
    api_token: str = "dev-token"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_database_url(self) -> "Settings":
        app_env_explicitly_set = "app_env" in self.model_fields_set

        if self.database_url.startswith("sqlite:///./local_dev_") and self.app_env not in {"local", "test"}:
            raise ValueError("APP_ENV must be local or test when using the default local SQLite database_url")
        if (
            self.api_token == "dev-token"
            and self.database_url != "sqlite:///./local_dev_agent_status_panel.db"
            and (not app_env_explicitly_set or self.app_env not in {"local", "test"})
        ):
            raise ValueError("API_TOKEN must not use the default dev token outside explicit local/test mode")

        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
