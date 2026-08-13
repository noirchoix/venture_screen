from __future__ import annotations

import io
import zipfile
from services.document_service import DocumentService


def test_zip_extracts_safe_repository_files_and_skips_traversal():
    buff=io.BytesIO()
    with zipfile.ZipFile(buff,'w') as z:
        z.writestr('repo/README.md','# Startup\nEvidence here')
        z.writestr('repo/src/main.py','print("hello")')
        z.writestr('../escape.py','bad = True')
        z.writestr('repo/node_modules/pkg/index.js','ignored')
    text,warnings,sha=DocumentService().extract('repo.zip',buff.getvalue(),'application/zip')
    assert 'README.md' in text
    assert 'src/main.py' in text
    assert 'escape.py' not in text
    assert any('unsafe ZIP path' in w for w in warnings)
    assert len(sha) == 64
