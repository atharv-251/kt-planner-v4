import shutil
import os
import logging
import zipfile
from pathlib import Path
import requests
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from backend.database import get_db
from backend.models.transition import Transition, UploadedDocument, RawExtraction, ProjectProfile
from backend.schemas.transition import UploadedDocumentResponse
from backend.config import UPLOADS_DIR, EXTERNAL_API_URL, EXTERNAL_API_URL1
from backend.services.external_extraction_service import (
    call_external_extraction_api,
    extract_uploaded_documents_locally,
)

logger = logging.getLogger("kt_planner.extraction")
logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/api/v1/transitions/{transition_id}", tags=["Documents & Extraction"])

@router.post("/upload", response_model=UploadedDocumentResponse)
async def upload_document(
    transition_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    transition = db.query(Transition).filter(Transition.id == transition_id).first()
    if not transition:
        raise HTTPException(status_code=404, detail="Transition not found")

    target_path = UPLOADS_DIR / f"{transition_id}_{file.filename}"
    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = target_path.stat().st_size
    doc = UploadedDocument(
        transition_id=transition_id,
        file_name=file.filename,
        file_path=str(target_path),
        file_size=file_size,
        mime_type=file.content_type or "application/octet-stream",
    )
    db.add(doc)
    transition.status = "document_uploaded"
    db.commit()
    db.refresh(doc)
    return doc

@router.get("/documents", response_model=List[UploadedDocumentResponse])
def get_documents(transition_id: str, db: Session = Depends(get_db)):
    return db.query(UploadedDocument).filter(UploadedDocument.transition_id == transition_id).all()

@router.post("/extract")
def trigger_extraction(
    transition_id: str,
    db: Session = Depends(get_db)
):
    """
    Calls the external extraction API if configured and available, otherwise
    extracts supported uploaded document formats locally.
    """
    transition = db.query(Transition).filter(Transition.id == transition_id).first()
    if not transition:
        raise HTTPException(status_code=404, detail="Transition not found")

    external_response = None
    
    # Determine external API URL from env (handling "0" or unset)
    raw_api_url = EXTERNAL_API_URL if (EXTERNAL_API_URL and str(EXTERNAL_API_URL).strip() not in ("0", "")) else None
    if not raw_api_url:
        raw_api_url = EXTERNAL_API_URL1 if (EXTERNAL_API_URL1 and str(EXTERNAL_API_URL1).strip() not in ("0", "")) else None
    external_api_url = raw_api_url
    
    # Retrieve all uploaded documents for this transition
    docs = (
        db.query(UploadedDocument)
        .filter(UploadedDocument.transition_id == transition_id)
        .order_by(UploadedDocument.uploaded_at.asc())
        .all()
    )

    # Call external API with all uploaded files if configured
    if external_api_url and docs:
        external_response = call_external_extraction_api(
            external_api_url=external_api_url,
            docs=docs,
            timeout_seconds=600,
        )

    extraction_source = "external_api"
    if not external_response:
        try:
            external_response = extract_uploaded_documents_locally(docs)
            extraction_source = "local_document_parser"
        except (OSError, ValueError, zipfile.BadZipFile) as parse_error:
            logger.exception("Local document extraction failed")
            raise HTTPException(status_code=422, detail=str(parse_error)) from parse_error
        if not external_response:
            raise HTTPException(
                status_code=503,
                detail="No uploaded documents could be extracted. Configure EXTERNAL_API_URL or upload a supported file.",
            )

    payload = external_response
    total_topics = sum(
        len(application.get("topics", []))
        for application in payload.get("applications", [])
    )

    # Update transition category if extracted
    extracted_category = payload.get("project_category", "development_and_ams")
    transition.category = extracted_category

    raw = RawExtraction(
        transition_id=transition_id,
        raw_json_payload=payload,
        normalized_payload=payload,
    )
    db.add(raw)
    db.query(ProjectProfile).filter(ProjectProfile.transition_id == transition_id).delete(
        synchronize_session=False
    )
    transition.status = "extracted"
    db.commit()

    return {
        "status": "success",
        "message": "Documents extracted successfully.",
        "project_name": payload.get("project_name"),
        "project_category": extracted_category,
        "total_topics": total_topics,
        "extraction_source": payload.get("extraction_source", extraction_source),
    }

@router.get("/raw-extraction")
def get_raw_extraction(transition_id: str, db: Session = Depends(get_db)):
    raw = (
        db.query(RawExtraction)
        .filter(RawExtraction.transition_id == transition_id)
        .order_by(RawExtraction.extracted_at.desc())
        .first()
    )
    if not raw:
        raise HTTPException(status_code=404, detail="No extraction data found. Please trigger extraction first.")
    return raw.raw_json_payload
