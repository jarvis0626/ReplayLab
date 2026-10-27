from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    data_dir: Path = Path(__file__).resolve().parents[2] / "data"
    ai_provider: str = "mock"
    model_api_key: str = Field(default="", repr=False)
    meta_base_url: str = "https://api.meta.ai/v1"
    max_video_bytes: int = 100 * 1024 * 1024
    max_image_bytes: int = 10 * 1024 * 1024
    max_video_seconds: float = 120
    screen_local_interval: float = Field(default=2.0, ge=0, le=60)
    screen_meta_interval: float = Field(default=10.0, ge=0, le=120)
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173"
    )

    @property
    def origins(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(",") if value.strip()]
