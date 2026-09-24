from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_full_kt_planner_api_workflow():
    # 1. Create transition
    t_resp = client.post(
        "/api/v1/transitions",
        json={
            "name": "Integration Test Transition",
            "category": "development_and_ams",
            "start_date": "2026-09-21",
            "end_date": "2026-10-31",
            "total_duration_days": 60,
            "shadow_days": 10,
            "reverse_shadow_days": 10,
            "daily_kt_hours": 5.0,
            "primary_country": "India",
        }
    )
    assert t_resp.status_code == 200
    transition = t_resp.json()
    t_id = transition["id"]
    assert transition["available_kt_days"] == 40
    assert transition["target_capacity_hours"] == 200.0

    # 2. Trigger extraction
    ext_resp = client.post(f"/api/v1/transitions/{t_id}/extract")
    assert ext_resp.status_code == 200
    assert ext_resp.json()["status"] == "success"

    # 3. Generate project profile
    prof_resp = client.post(f"/api/v1/transitions/{t_id}/profile/generate")
    assert prof_resp.status_code == 200
    profile = prof_resp.json()
    assert profile["project_name"] != ""

    # Approve profile
    appr_resp = client.post(
        f"/api/v1/transitions/{t_id}/profile/approve",
        json={"approved_by": "Transition Lead"}
    )
    assert appr_resp.status_code == 200
    assert appr_resp.json()["is_approved"] is True

    # 4. Generate knowledge hierarchy
    hier_resp = client.post(f"/api/v1/transitions/{t_id}/hierarchy/generate")
    assert hier_resp.status_code == 200
    assert hier_resp.json()["total_nodes"] > 10

    # Verify hierarchy
    get_hier = client.get(f"/api/v1/transitions/{t_id}/hierarchy?view=nested")
    assert get_hier.status_code == 200
    assert len(get_hier.json()) > 0

    # 5. Evaluate KT levels
    lvl_resp = client.post(f"/api/v1/transitions/{t_id}/levels/evaluate")
    assert lvl_resp.status_code == 200
    assert lvl_resp.json()["total_evaluated"] > 0

    # 6. Balance capacity via decomposition
    decomp_resp = client.post(f"/api/v1/transitions/{t_id}/hierarchy/decompose")
    assert decomp_resp.status_code == 200

    # 7. Add SME
    sme_resp = client.post(
        f"/api/v1/transitions/{t_id}/stakeholders",
        json={
            "name": "Dev Sharma",
            "email": "dev.sharma@example.com",
            "role": "sme",
            "primary_domain": "technical",
        }
    )
    assert sme_resp.status_code == 200

    # 8. Auto-build schedule
    sched_resp = client.post(
        f"/api/v1/transitions/{t_id}/schedule/auto-build",
        json={"daily_start_hour": 10, "daily_max_hours": 5.0, "auto_assign_smes": True}
    )
    assert sched_resp.status_code == 200
    assert sched_resp.json()["total_sessions"] > 0

    # Verify FullCalendar feed
    fc_resp = client.get(f"/api/v1/transitions/{t_id}/schedule/fullcalendar")
    assert fc_resp.status_code == 200
    assert len(fc_resp.json()) > 0

    # 9. Validation Report
    val_resp = client.get(f"/api/v1/transitions/{t_id}/validation")
    assert val_resp.status_code == 200
    val_data = val_resp.json()
    assert "overall_status" in val_data
    assert val_data["score_percent"] > 50.0

    # 10. Test XLSX Export
    xlsx_resp = client.get(f"/api/v1/transitions/{t_id}/export/xlsx")
    assert xlsx_resp.status_code == 200
    assert len(xlsx_resp.content) > 1000

    # 11. Test CSV Export
    csv_resp = client.get(f"/api/v1/transitions/{t_id}/export/csv")
    assert csv_resp.status_code == 200
    assert "Session Title" in csv_resp.text

