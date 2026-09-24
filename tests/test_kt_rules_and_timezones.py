import pytest
from datetime import date
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.timezone_service import TimezoneService
from backend.services.scheduling_service import SchedulingService

client = TestClient(app)

def test_timezone_lookup_and_dst():
    # US (EDT in Summer/Fall) vs India (IST, no DST)
    us_tz = TimezoneService.get_timezone_for_country("United States")
    assert us_tz == "America/New_York"
    
    in_tz = TimezoneService.get_timezone_for_country("India")
    assert in_tz == "Asia/Kolkata"

    # DST test: July (EDT is UTC-4) vs January (EST is UTC-5)
    summer_date = date(2026, 7, 15)
    winter_date = date(2026, 1, 15)

    is_summer_dst, offset_summer = TimezoneService.is_dst_active(us_tz, summer_date)
    is_winter_dst, offset_winter = TimezoneService.is_dst_active(us_tz, winter_date)

    assert is_summer_dst is True
    assert offset_summer == -4.0
    assert is_winter_dst is False
    assert offset_winter == -5.0

def test_shift_overlap_calculation():
    # India (IST = UTC+5.5) and UK (BST in summer = UTC+1.0)
    target_date = date(2026, 7, 15)
    result = TimezoneService.calculate_shift_overlap(
        sme_country="United Kingdom",
        receiver_country="India",
        sme_shift_start="08:00",
        sme_shift_end="17:00",
        receiver_shift_start="08:00",
        receiver_shift_end="17:00",
        target_date=target_date,
    )

    assert result["overlap_hours"] > 0
    assert "sme_utc_offset" in result
    assert "receiver_utc_offset" in result
    assert result["sme_dst_active"] is True
    assert result["overlap_window_sme"] is not None
    assert result["overlap_window_receiver"] is not None

def test_kt_rules_validation():
    # Rule 1: L1 SME can teach only L1 topics to L1 receivers
    valid, _ = SchedulingService.validate_kt_rules("L1", "L1", "L1")
    assert valid is True

    valid, msg = SchedulingService.validate_kt_rules("L1", "L2", "L1")
    assert valid is False
    assert "cannot teach L2 topic" in msg

    valid, msg = SchedulingService.validate_kt_rules("L1", "L1", "L2")
    assert valid is False
    assert "cannot teach L2 receiver" in msg

    # Rule 2: L2 SME can teach L1 or L2 topics to L1 or L2 receivers
    valid, _ = SchedulingService.validate_kt_rules("L2", "L1", "L1")
    assert valid is True
    valid, _ = SchedulingService.validate_kt_rules("L2", "L2", "L1")
    assert valid is True
    valid, _ = SchedulingService.validate_kt_rules("L2", "L2", "L2")
    assert valid is True
    valid, msg = SchedulingService.validate_kt_rules("L2", "L3", "L2")
    assert valid is False
    assert "cannot teach L3 topic" in msg

    # Rule 3: L3 SME can teach L1, L2, or L3 topics to L1, L2, or L3 receivers (with receiver <= topic)
    valid, _ = SchedulingService.validate_kt_rules("L3", "L3", "L3")
    assert valid is True
    valid, _ = SchedulingService.validate_kt_rules("L3", "L2", "L2")
    assert valid is True
    valid, _ = SchedulingService.validate_kt_rules("L3", "L3", "L1")
    assert valid is True
    # Receiver L3 attending L1 topic: receiver level (3) > topic level (1) -> violates receiver <= topic
    valid, msg = SchedulingService.validate_kt_rules("L3", "L1", "L3")
    assert valid is False
    assert "cannot receive L1 topic" in msg

def test_api_shift_overlap_and_domain_hours():
    # Create transition
    t_resp = client.post(
        "/api/v1/transitions",
        json={
            "name": "Overlap and Hours Transition",
            "category": "development_and_ams",
            "sme_country": "United States",
            "receiver_country": "India",
            "start_date": "2026-09-21",
            "end_date": "2026-10-31",
            "total_duration_days": 40,
            "shadow_days": 5,
            "reverse_shadow_days": 5,
            "daily_kt_hours": 4.0,
        }
    )
    assert t_resp.status_code == 200
    t_data = t_resp.json()
    t_id = t_data["id"]
    assert t_data["sme_timezone"] == "America/New_York"
    assert t_data["receiver_timezone"] == "Asia/Kolkata"

    # Test shift overlap endpoint
    overlap_resp = client.get(f"/api/v1/transitions/{t_id}/shift-overlap")
    assert overlap_resp.status_code == 200
    overlap_data = overlap_resp.json()
    assert overlap_data["sme_country"] == "United States"
    assert overlap_data["receiver_country"] == "India"
    assert "sme_dst_active" in overlap_data

    # Generate hierarchy
    client.post(f"/api/v1/transitions/{t_id}/extract")
    client.post(f"/api/v1/transitions/{t_id}/profile/generate")
    client.post(f"/api/v1/transitions/{t_id}/profile/approve", json={"approved_by": "Test Lead"})
    hier_resp = client.post(f"/api/v1/transitions/{t_id}/hierarchy/generate")
    assert hier_resp.status_code == 200

    # Test domain hours editable update endpoint
    cap_before = client.get(f"/api/v1/transitions/{t_id}/export/capacity").json()
    cat_breakdown = cap_before.get("category_breakdown", {})
    assert len(cat_breakdown) > 0
    first_domain = list(cat_breakdown.keys())[0]
    
    # Scale first domain to 80.0 hours
    update_domain_resp = client.put(
        f"/api/v1/transitions/{t_id}/domain-hours",
        json={"domain_hours": {first_domain: 80.0}}
    )
    assert update_domain_resp.status_code == 200
    domain_data = update_domain_resp.json()
    assert domain_data["status"] == "success"
    assert "capacity" in domain_data
    assert domain_data["capacity"]["category_breakdown"][first_domain] == 80.0

def test_stakeholder_role_and_level_validation():
    # Create transition
    t_resp = client.post(
        "/api/v1/transitions",
        json={
            "name": "Stakeholder Validation Transition",
            "category": "development",
            "sme_country": "Germany",
            "receiver_country": "Poland",
        }
    )
    t_id = t_resp.json()["id"]

    # Generate and set profile intended levels to ['L1', 'L2']
    client.post(f"/api/v1/transitions/{t_id}/extract")
    client.post(f"/api/v1/transitions/{t_id}/profile/generate")
    client.put(
        f"/api/v1/transitions/{t_id}/profile",
        json={"intended_levels": ["L1", "L2"], "project_category": "development"}
    )

    # Valid SME creation
    sme_resp = client.post(
        f"/api/v1/transitions/{t_id}/stakeholders",
        json={"name": "Alice SME", "email": "alice@corp.com", "role": "sme", "level": "L2"}
    )
    assert sme_resp.status_code == 200
    assert sme_resp.json()["role"] == "sme"
    assert sme_resp.json()["level"] == "L2"

    # Valid Receiver creation
    rcv_resp = client.post(
        f"/api/v1/transitions/{t_id}/stakeholders",
        json={"name": "Bob Receiver", "email": "bob@corp.com", "role": "receiver", "level": "L1"}
    )
    assert rcv_resp.status_code == 200
    assert rcv_resp.json()["role"] == "receiver"
    assert rcv_resp.json()["level"] == "L1"

    # Invalid Level (L3 is not in intended_levels ['L1', 'L2'])
    inv_lvl_resp = client.post(
        f"/api/v1/transitions/{t_id}/stakeholders",
        json={"name": "Charlie L3", "email": "charlie@corp.com", "role": "sme", "level": "L3"}
    )
    assert inv_lvl_resp.status_code == 400
    assert "not in the selected intended levels" in inv_lvl_resp.json()["detail"]


def test_intended_levels_strictly_prevents_l3_topics_and_sessions():
    """
    Verifies that when only L1 and L2 are selected during profile review:
    1. TopicDecompositionAgent does NOT generate L3 topics/evaluations.
    2. KTLevelAgent evaluates topics without L3.
    3. Auto-scheduler strictly generates only L1 and L2 sessions (no L3).
    4. No L2 SME or Receiver is assigned to non-existent L3 sessions.
    """
    t_resp = client.post(
        "/api/v1/transitions",
        json={
            "name": "Intended Levels Strict L1 L2 Transition",
            "category": "development",
            "sme_country": "India",
            "receiver_country": "India",
            "start_date": "2026-10-01",
            "end_date": "2026-11-15",
            "total_duration_days": 45,
            "daily_kt_hours": 4.0,
        }
    )
    t_id = t_resp.json()["id"]

    # Extract documents and generate profile
    client.post(f"/api/v1/transitions/{t_id}/extract")
    client.post(f"/api/v1/transitions/{t_id}/profile/generate")

    # Set intended_levels to ['L1', 'L2'] during Profile Review
    update_prof = client.put(
        f"/api/v1/transitions/{t_id}/profile",
        json={"intended_levels": ["L1", "L2"], "project_category": "development"}
    )
    assert update_prof.status_code == 200
    assert update_prof.json()["intended_levels"] == ["L1", "L2"]

    # Generate hierarchy
    client.post(f"/api/v1/transitions/{t_id}/hierarchy/generate")

    # Run KT Level evaluation
    eval_resp = client.post(f"/api/v1/transitions/{t_id}/levels/evaluate")
    assert eval_resp.status_code == 200

    # Run Topic Decomposition (Capacity)
    decomp_resp = client.post(f"/api/v1/transitions/{t_id}/hierarchy/decompose")
    assert decomp_resp.status_code == 200

    # Verify that NO evaluation contains L3
    evals = client.get(f"/api/v1/transitions/{t_id}/levels").json()
    assert len(evals) > 0
    for ev in evals:
        assert "L3" not in ev["level_scope"], f"Evaluation {ev['node_name']} has L3 in scope: {ev['level_scope']}"

    # Add L1 and L2 stakeholders
    client.post(
        f"/api/v1/transitions/{t_id}/stakeholders",
        json={"name": "SME L1", "email": "sme1@test.com", "role": "sme", "level": "L1"}
    )
    client.post(
        f"/api/v1/transitions/{t_id}/stakeholders",
        json={"name": "SME L2", "email": "sme2@test.com", "role": "sme", "level": "L2"}
    )
    client.post(
        f"/api/v1/transitions/{t_id}/stakeholders",
        json={"name": "Rcv L1", "email": "rcv1@test.com", "role": "receiver", "level": "L1"}
    )
    client.post(
        f"/api/v1/transitions/{t_id}/stakeholders",
        json={"name": "Rcv L2", "email": "rcv2@test.com", "role": "receiver", "level": "L2"}
    )

    # Auto-schedule sessions
    sched_resp = client.post(
        f"/api/v1/transitions/{t_id}/schedule/auto-build",
        json={"daily_start_hour": 10, "daily_max_hours": 4.0, "auto_assign_smes": True}
    )
    assert sched_resp.status_code == 200

    sessions = client.get(f"/api/v1/transitions/{t_id}/schedule").json()
    assert len(sessions) > 0

    # Verify that NO session has level L3
    for s in sessions:
        assert s["level"] in ["L1", "L2"], f"Session '{s['session_title']}' has unexpected level {s['level']}"
        assert s["level"] != "L3", f"L3 session '{s['session_title']}' was generated despite intended_levels=['L1', 'L2']"

    # Verify quality validation passes compliance check
    val_report = client.get(f"/api/v1/transitions/{t_id}/validation").json()
    rule_check = next((c for c in val_report["checks"] if c["check_name"] == "KT Planning Rules Compliance"), None)
    assert rule_check is not None
    assert rule_check["passed"] is True

