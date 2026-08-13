from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.config import settings


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class VentureStore:
    def __init__(self, db_path: Path | None = None):
        self.db_path = Path(db_path or settings.db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        conn.execute('PRAGMA journal_mode = WAL')
        conn.execute('PRAGMA synchronous = NORMAL')
        return conn

    def _init_db(self) -> None:
        with self._lock, self.connect() as conn:
            conn.executescript(
                '''
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    text_content TEXT NOT NULL,
                    warnings_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS screenings (
                    id TEXT PRIMARY KEY,
                    startup_name TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS companies (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    one_liner TEXT NOT NULL DEFAULT '',
                    problem TEXT NOT NULL DEFAULT '',
                    customer TEXT NOT NULL DEFAULT '',
                    product TEXT NOT NULL DEFAULT '',
                    business_model TEXT NOT NULL DEFAULT '',
                    industry TEXT NOT NULL DEFAULT '',
                    geography_json TEXT NOT NULL DEFAULT '[]',
                    url TEXT NOT NULL DEFAULT '',
                    source TEXT NOT NULL,
                    source_url TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_companies_source ON companies(source);
                CREATE INDEX IF NOT EXISTS idx_screenings_created_at ON screenings(created_at);
                '''
            )

    def put_document(
        self,
        document_id: str,
        filename: str,
        media_type: str,
        sha256: str,
        text_content: str,
        warnings: list[str],
    ) -> None:
        with self._lock, self.connect() as conn:
            conn.execute(
                '''INSERT OR REPLACE INTO documents
                   (id, filename, media_type, sha256, text_content, warnings_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (document_id, filename, media_type, sha256, text_content, json.dumps(warnings), utcnow()),
            )

    def get_documents(self, ids: list[str]) -> list[dict[str, Any]]:
        if not ids:
            return []
        placeholders = ','.join('?' for _ in ids)
        with self.connect() as conn:
            rows = conn.execute(
                f'SELECT * FROM documents WHERE id IN ({placeholders})', ids
            ).fetchall()
        by_id = {row['id']: dict(row) for row in rows}
        result = []
        for doc_id in ids:
            row = by_id.get(doc_id)
            if row:
                row['warnings'] = json.loads(row.pop('warnings_json'))
                result.append(row)
        return result

    def save_screening(self, screening_id: str, startup_name: str, request: dict[str, Any], response: dict[str, Any]) -> None:
        with self._lock, self.connect() as conn:
            conn.execute(
                '''INSERT INTO screenings(id, startup_name, request_json, response_json, created_at)
                   VALUES (?, ?, ?, ?, ?)''',
                (screening_id, startup_name, json.dumps(request), json.dumps(response), response['created_at']),
            )

    def get_screening(self, screening_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute('SELECT response_json FROM screenings WHERE id = ?', (screening_id,)).fetchone()
        return json.loads(row['response_json']) if row else None

    def screening_count(self) -> int:
        with self.connect() as conn:
            return int(conn.execute('SELECT COUNT(*) FROM screenings').fetchone()[0])

    def upsert_companies(self, companies: list[dict[str, Any]], replace_source: str | None = None) -> int:
        with self._lock, self.connect() as conn:
            if replace_source:
                conn.execute('DELETE FROM companies WHERE source = ?', (replace_source,))
            count = 0
            for company in companies:
                conn.execute(
                    '''INSERT INTO companies
                       (id,name,one_liner,problem,customer,product,business_model,industry,geography_json,url,source,source_url,updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(id) DO UPDATE SET
                         name=excluded.name,
                         one_liner=excluded.one_liner,
                         problem=excluded.problem,
                         customer=excluded.customer,
                         product=excluded.product,
                         business_model=excluded.business_model,
                         industry=excluded.industry,
                         geography_json=excluded.geography_json,
                         url=excluded.url,
                         source=excluded.source,
                         source_url=excluded.source_url,
                         updated_at=excluded.updated_at''',
                    (
                        company['id'], company['name'], company.get('one_liner',''), company.get('problem',''),
                        company.get('customer',''), company.get('product',''), company.get('business_model',''),
                        company.get('industry',''), json.dumps(company.get('geography') or []), company.get('url',''),
                        company.get('source','user_import'), company.get('source_url',''), utcnow(),
                    ),
                )
                count += 1
        return count

    def list_companies(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute('SELECT * FROM companies ORDER BY name').fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item['geography'] = json.loads(item.pop('geography_json'))
            item.pop('updated_at', None)
            result.append(item)
        return result

    def company_count(self) -> int:
        with self.connect() as conn:
            return int(conn.execute('SELECT COUNT(*) FROM companies').fetchone()[0])
