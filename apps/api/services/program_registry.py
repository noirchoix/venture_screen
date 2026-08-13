from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.config import BASE_DIR


class ProgramRegistry:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or (BASE_DIR / 'data')
        self._programs = self._read('programs.json')
        self._opportunities = self._read('opportunities.json')

    def _read(self, filename: str) -> list[dict[str, Any]]:
        return json.loads((self.data_dir / filename).read_text(encoding='utf-8'))

    def programs(self) -> list[dict[str, Any]]:
        return [dict(x) for x in self._programs]

    def program(self, program_id: str) -> dict[str, Any] | None:
        return next((dict(x) for x in self._programs if x['id'] == program_id), None)

    def opportunities(self) -> list[dict[str, Any]]:
        return [dict(x) for x in self._opportunities]
