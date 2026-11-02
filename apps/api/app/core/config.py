from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    data_dir: Path = Path(__file__).resolve().parents[2] / "data"
    ai_provider: str = "mock"
    model_api_key: str = Field(default="", repr=False)
    meta_base_url: str = "https://api.meta.ai/v1"
    nvidia_api_key: str = Field(default="", repr=False)
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "meta/muse-glimmer-30b"
    nvidia_timeout_seconds: float = Field(default=45, ge=5, le=180)
    nvidia_max_tokens: int = Field(default=4096, ge=256, le=32768)
    nvidia_reasoning_effort: str = "low"
    max_video_bytes: int = 100 * 1024 * 1024
    max_image_bytes: int = 10 * 1024 * 1024
    max_video_seconds: float = 120
    screen_local_interval: float = Field(default=2.0, ge=0, le=60)
    screen_meta_interval: float = Field(default=10.0, ge=0, le=120)
    screen_nvidia_interval: float = Field(default=12.0, ge=0, le=120)
    verification_min_confidence: float = Field(default=0.75, ge=0.5, le=1)
    verification_digital_quality: float = Field(default=0.4, ge=0.1, le=1)
    verification_physical_quality: float = Field(default=0.65, ge=0.1, le=1)
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173"
    )

    @property
    def origins(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(",") if value.strip()]
