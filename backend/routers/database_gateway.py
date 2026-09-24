import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.database import get_db
from backend.schemas.governance import ControlledSQLRequest, ControlledSQLResponse

router = APIRouter(prefix="/api/v1/database", tags=["Controlled Database API"])

# Forbidden SQL keywords for mutation protection
FORBIDDEN_KEYWORDS = [
    r"\bINSERT\b", r"\bUPDATE\b", r"\bDELETE\b", r"\bDROP\b",
    r"\bALTER\b", r"\bCREATE\b", r"\bTRUNCATE\b", r"\bREPLACE\b",
    r"\bATTACH\b", r"\bDETACH\b", r"\bPRAGMA\b", r"\bVACUUM\b",
    r"\bEXEC\b", r"\bEXECUTE\b", r"\bGRANT\b", r"\bREVOKE\b"
]

@router.post("/query", response_model=ControlledSQLResponse)
def execute_controlled_readonly_query(
    payload: ControlledSQLRequest,
    db: Session = Depends(get_db)
):
    query_str = payload.query.strip()

    # Verify query is read-only
    for pattern in FORBIDDEN_KEYWORDS:
        if re.search(pattern, query_str, re.IGNORECASE):
            raise HTTPException(
                status_code=403,
                detail="Forbidden: Write operations and schema mutations are strictly blocked. Use typed mutation APIs instead."
            )

    # Enforce SELECT / WITH clause
    if not (query_str.upper().startswith("SELECT") or query_str.upper().startswith("WITH") or query_str.upper().startswith("EXPLAIN")):
        raise HTTPException(
            status_code=400,
            detail="Invalid query: Controlled SQL gateway only permits read-only SELECT or WITH statements."
        )

    try:
        stmt = text(query_str)
        result = db.execute(stmt, payload.params or {})
        columns = list(result.keys()) if result.returns_rows else []
        rows = [dict(zip(columns, row)) for row in result.fetchall()] if result.returns_rows else []

        return ControlledSQLResponse(
            columns=columns,
            rows=rows,
            row_count=len(rows),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query execution error: {str(e)}")

