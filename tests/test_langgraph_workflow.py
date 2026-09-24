from backend.database import SessionLocal, Base, engine
from backend.models.transition import Transition, RawExtraction
from backend.ai.workflow import kt_planner_app
from backend.config import SAMPLE_EXTRACT_PATH
import json

def test_langgraph_workflow_execution():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Create transition shell
        t = Transition(name="LangGraph Test Transition")
        db.add(t)
        db.commit()

        # Ingest raw extraction payload
        with open(SAMPLE_EXTRACT_PATH, "r", encoding="utf-8") as f:
            payload = json.load(f)

        raw = RawExtraction(
            transition_id=t.id,
            raw_json_payload=payload,
            normalized_payload=payload,
        )
        db.add(raw)
        db.commit()

        # Execute compiled LangGraph StateGraph
        initial_state = {
            "transition_id": t.id,
            "current_stage": "start",
            "status_message": "Starting workflow",
            "errors": [],
        }

        final_state = kt_planner_app.invoke(initial_state)

        assert final_state["current_stage"] == "quality_validated"
        assert len(final_state["errors"]) == 0
        assert "Quality validated by Agent 6" in final_state["status_message"]
    finally:
        db.close()

