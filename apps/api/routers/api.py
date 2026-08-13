from __future__ import annotations

import hashlib
import uuid
from fastapi import APIRouter, File, HTTPException, UploadFile

from core.config import settings
from repositories.store import VentureStore
from schemas.models import (
    CompanyImportRequest, CompanyImportResponse, ExtractedDocument, HealthResponse,
    ScreeningRequest, ScreeningResponse, StartupPrefillRequest, StartupPrefillResponse,
)
from services.document_service import DocumentError, DocumentService
from services.prefill_service import StartupPrefillService
from services.program_registry import ProgramRegistry
from services.screening_service import ScreeningService


router = APIRouter()
store = VentureStore()
registry = ProgramRegistry()
documents = DocumentService(); prefill = StartupPrefillService()
screening = ScreeningService(store)


@router.get('/health', response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        ok=True,
        app_name=settings.app_name,
        environment=settings.environment,
        programs=len(registry.programs()),
        opportunities=len(registry.opportunities()),
        company_catalog=store.company_count(),
        screenings=store.screening_count(),
    )


@router.get('/programs')
def programs() -> list[dict]:
    return registry.programs()


@router.get('/opportunities')
def opportunities() -> list[dict]:
    return registry.opportunities()


@router.post('/evidence/upload', response_model=ExtractedDocument)
async def upload_evidence(file: UploadFile = File(...)) -> ExtractedDocument:
    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail='Uploaded file exceeds configured size limit.')
    filename = file.filename or 'upload'
    try:
        text, warnings, sha = documents.extract(filename, data, file.content_type or '')
    except (DocumentError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    document_id = 'doc_' + uuid.uuid4().hex[:14]
    store.put_document(document_id, filename, file.content_type or 'application/octet-stream', sha, text, warnings)
    return ExtractedDocument(
        document_id=document_id,
        filename=filename,
        media_type=file.content_type or 'application/octet-stream',
        chars=len(text),
        sha256=sha,
        text_preview=text[:1200],
        warnings=warnings,
    )


@router.post('/evidence/prefill', response_model=StartupPrefillResponse)
def prefill_startup(req: StartupPrefillRequest) -> StartupPrefillResponse:
    docs = store.get_documents(req.document_ids)
    found = {d['id'] for d in docs}
    missing = [doc_id for doc_id in req.document_ids if doc_id not in found]
    if missing:
        raise HTTPException(status_code=404, detail=f'Evidence document ids not found: {missing}')
    return prefill.extract(docs)


@router.post('/screenings', response_model=ScreeningResponse)
def create_screening(req: ScreeningRequest) -> ScreeningResponse:
    unknown = [pid for pid in req.startup.target_program_ids if registry.program(pid) is None]
    if unknown:
        raise HTTPException(status_code=422, detail=f'Unknown program ids: {unknown}')
    return screening.screen(req.startup, req.competitor_limit, req.opportunity_limit)


@router.get('/screenings/{screening_id}', response_model=ScreeningResponse)
def get_screening(screening_id: str) -> ScreeningResponse:
    result = store.get_screening(screening_id)
    if not result:
        raise HTTPException(status_code=404, detail='Screening not found.')
    return ScreeningResponse.model_validate(result)


@router.post('/companies/import', response_model=CompanyImportResponse)
def import_companies(req: CompanyImportRequest) -> CompanyImportResponse:
    inserted = screening.competitors.import_companies([c.model_dump(mode='json') for c in req.companies], req.replace_source)
    return CompanyImportResponse(inserted=inserted, catalog_size=store.company_count())
