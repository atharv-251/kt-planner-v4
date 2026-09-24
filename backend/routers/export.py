from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.transition import Transition
from backend.services.export_service import ExportService
from backend.services.capacity_service import CapacityService

router = APIRouter(prefix="/api/v1/transitions/{transition_id}/export", tags=["Exports & Deliverables"])

@router.get("/xlsx")
def export_excel_package(transition_id: str, db: Session = Depends(get_db)):
    transition = db.query(Transition).filter(Transition.id == transition_id).first()
    if not transition:
        raise HTTPException(status_code=404, detail="Transition not found")

    excel_buffer = ExportService.generate_excel_master_package(db, transition_id)
    safe_name = transition.name.replace(" ", "_")
    filename = f"KT_Master_Plan_{safe_name}.xlsx"

    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/csv")
def export_csv_schedule(transition_id: str, db: Session = Depends(get_db)):
    transition = db.query(Transition).filter(Transition.id == transition_id).first()
    if not transition:
        raise HTTPException(status_code=404, detail="Transition not found")

    csv_data = ExportService.generate_schedule_csv(db, transition_id)
    safe_name = transition.name.replace(" ", "_")
    filename = f"KT_Schedule_{safe_name}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/capacity")
def get_capacity_report(transition_id: str, db: Session = Depends(get_db)):
    try:
        report = CapacityService.evaluate_capacity_balance(db, transition_id)
        return report
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

