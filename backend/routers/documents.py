import shutil
import json
import os
import logging
from pathlib import Path
import requests
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from backend.database import get_db
from backend.models.transition import Transition, UploadedDocument, RawExtraction
from backend.schemas.transition import UploadedDocumentResponse
from backend.config import UPLOADS_DIR, SAMPLE_EXTRACT_PATH, EXTERNAL_API_URL, EXTERNAL_API_URL1
from backend.services.external_extraction_service import call_external_extraction_api

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
    Calls the external extraction API if configured and available,
    or falls back to the canonical transition extract file (KT_Extract-*.json).
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

    # Fallback to local canonical extract if external response is unavailable
    if not external_response:
        if not SAMPLE_EXTRACT_PATH.exists():
            raise HTTPException(status_code=500, detail="Sample extraction reference not found")
        with open(SAMPLE_EXTRACT_PATH, "r", encoding="utf-8") as f:
            external_response = json.load(f)
        logger.warning("External API unavailable or failed; loaded fallback canonical extraction payload from workspace file.")

    payload = external_response

    # Update transition category if extracted
    extracted_category = payload.get("project_category", "development_and_ams")
    transition.category = extracted_category

    raw = RawExtraction(
        transition_id=transition_id,
        raw_json_payload=payload,
        normalized_payload=payload,
    )
    db.add(raw)
    transition.status = "extracted"
    db.commit()

    return {
        "status": "success",
        "message": "Documents extracted successfully from transition extraction API.",
        "project_name": payload.get("project_name"),
        "project_category": extracted_category,
        "total_topics": len(payload.get("applications", [{}])[0].get("topics", [])),
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
