from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BASE_DIR.parents[1]


def _csv(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(',') if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv('VSI_APP_NAME', 'Venture Screening Intelligence')
    environment: str = os.getenv('VSI_ENVIRONMENT', 'development')
    api_prefix: str = os.getenv('VSI_API_PREFIX', '/api/v1')
    data_dir: Path = Path(os.getenv('VSI_DATA_DIR', str(PROJECT_ROOT / 'data')))
    max_upload_bytes: int = int(os.getenv('VSI_MAX_UPLOAD_BYTES', str(25 * 1024 * 1024)))
    max_document_chars: int = int(os.getenv('VSI_MAX_DOCUMENT_CHARS', '120000'))
    cors_origins: tuple[str, ...] = tuple(_csv('VSI_CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173'))
    llm_provider: str = os.getenv('VSI_LLM_PROVIDER', 'offline')
    llm_api_key: str = os.getenv('VSI_LLM_API_KEY', '')
    llm_model: str = os.getenv('VSI_LLM_MODEL', '')

    @property
    def db_path(self) -> Path:
        return self.data_dir / 'venture_screening.sqlite3'


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
