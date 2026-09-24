import os
import json
import io
import openpyxl
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

BASE_DIR = Path(__file__).resolve().parent.parent
PDF_1_PATH = BASE_DIR / "docs" / "Demo_01_AMS_Application_Profile.pdf"
PDF_2_PATH = BASE_DIR / "docs" / "Demo_02_Development_Application_Profile.pdf"
MOCK_JSON_PATH = BASE_DIR / "KT_Extract-1789932244532.json"

def test_full_pipeline_with_two_pdf_documents():
    assert PDF_1_PATH.exists(), f"Missing {PDF_1_PATH}"
    assert PDF_2_PATH.exists(), f"Missing {PDF_2_PATH}"
    assert MOCK_JSON_PATH.exists(), f"Missing {MOCK_JSON_PATH}"

    # Load fallback mock data for comparison
    with open(MOCK_JSON_PATH, "r", encoding="utf-8") as f:
        mock_data = json.load(f)
    mock_app_names = [a.get("application_name") for a in mock_data.get("applications", [])]
    mock_topics = set()
    for a in mock_data.get("applications", []):
        for t in a.get("topics", []):
            mock_topics.add(t.get("topic"))

    # 1. Create Transition Project
    create_resp = client.post(
        "/api/v1/transitions",
        json={
            "name": "Live Two PDF End-to-End Transition",
            "category": "development_and_ams",
            "sme_country": "United States",
            "receiver_country": "India",
            "start_date": "2026-09-21",
            "end_date": "2026-11-30",
            "total_duration_days": 70,
            "shadow_days": 10,
            "reverse_shadow_days": 10,
            "daily_kt_hours": 5.0,
        }
    )
    assert create_resp.status_code == 200
    t_id = create_resp.json()["id"]

    # 2. Upload both PDF documents from docs folder
    with open(PDF_1_PATH, "rb") as f1:
        up1 = client.post(
            f"/api/v1/transitions/{t_id}/upload",
            files={"file": ("Demo_01_AMS_Application_Profile.pdf", f1, "application/pdf")}
        )
        assert up1.status_code == 200

    with open(PDF_2_PATH, "rb") as f2:
        up2 = client.post(
            f"/api/v1/transitions/{t_id}/upload",
            files={"file": ("Demo_02_Development_Application_Profile.pdf", f2, "application/pdf")}
        )
        assert up2.status_code == 200

    docs_list = client.get(f"/api/v1/transitions/{t_id}/documents").json()
    assert len(docs_list) == 2

    # 3. Trigger Extraction via External API
    ext_resp = client.post(f"/api/v1/transitions/{t_id}/extract")
    assert ext_resp.status_code == 200
    ext_result = ext_resp.json()
    assert ext_result["status"] == "success"

    # 4. Detailed comparison: verify extracted data is from the live PDFs, NOT fallback mock JSON
    raw_resp = client.get(f"/api/v1/transitions/{t_id}/raw-extraction")
    assert raw_resp.status_code == 200
    extracted_data = raw_resp.json()

    extracted_project_name = extracted_data.get("project_name")
    extracted_apps = [a.get("application_name") for a in extracted_data.get("applications", [])]
    extracted_topics = []
    for a in extracted_data.get("applications", []):
        for t in a.get("topics", []):
            extracted_topics.append(t.get("topic"))

    print(f"\nExtracted Project Name: {extracted_project_name}")
    print(f"Extracted Apps: {extracted_apps}")
    print(f"Extracted Topics count: {len(extracted_topics)}")

    # Strict Assertions that mock data was NOT used:
    assert extracted_project_name != mock_data.get("project_name")
    assert "Test Application Name" not in extracted_apps
    assert "Orion Claims Operations Hub" in extracted_apps
    assert "Nova Fleet Insights Platform" in extracted_apps

    # Verify that extracted topics belong to the PDFs and are distinct from mock topics
    assert len(extracted_topics) > 0
    for topic in extracted_topics:
        assert topic not in mock_topics, f"Topic '{topic}' unexpectedly matches mock fallback!"
    
    # Specific topics expected from the two PDFs
    topic_text_blob = " ".join(extracted_topics)
    topic_text_lower = topic_text_blob.lower()
    assert "orion" in topic_text_lower
    assert "nova" in topic_text_lower

    # 5. Generate and Approve Profile
    prof_gen = client.post(f"/api/v1/transitions/{t_id}/profile/generate")
    assert prof_gen.status_code == 200
    appr_resp = client.post(f"/api/v1/transitions/{t_id}/profile/approve", json={"approved_by": "Transition Architect"})
    assert appr_resp.status_code == 200

    # 6. Generate Knowledge Hierarchy and verify 6-tier structure
    hier_resp = client.post(f"/api/v1/transitions/{t_id}/hierarchy/generate")
    assert hier_resp.status_code == 200
    nodes = client.get(f"/api/v1/transitions/{t_id}/hierarchy?view=nested").json()
    assert len(nodes) > 0

    # 7. Evaluate KT Levels
    lvl_resp = client.post(f"/api/v1/transitions/{t_id}/levels/evaluate")
    assert lvl_resp.status_code == 200

    # 8. Register Stakeholders with same-level and higher-level members
    sme1_resp = client.post(
        f"/api/v1/transitions/{t_id}/stakeholders",
        json={"name": "Alice L1 SME", "email": "alice.l1@corp.com", "role": "sme", "level": "L1"}
    )
    assert sme1_resp.status_code == 200
    sme2_resp = client.post(
        f"/api/v1/transitions/{t_id}/stakeholders",
        json={"name": "Bob L2 SME", "email": "bob.l2@corp.com", "role": "sme", "level": "L2"}
    )
    assert sme2_resp.status_code == 200

    rcv1_resp = client.post(
        f"/api/v1/transitions/{t_id}/stakeholders",
        json={"name": "Carol L1 Receiver", "email": "carol.l1@corp.com", "role": "receiver", "level": "L1"}
    )
    assert rcv1_resp.status_code == 200
    rcv2_resp = client.post(
        f"/api/v1/transitions/{t_id}/stakeholders",
        json={"name": "Dave L2 Receiver", "email": "dave.l2@corp.com", "role": "receiver", "level": "L2"}
    )
    assert rcv2_resp.status_code == 200

    # 9. Auto-Build Schedule and Verify Same-Level SME Assignment
    sched_resp = client.post(
        f"/api/v1/transitions/{t_id}/schedule/auto-build",
        json={"daily_start_hour": 10, "daily_max_hours": 5.0, "auto_assign_smes": True}
    )
    assert sched_resp.status_code == 200

    schedule = client.get(f"/api/v1/transitions/{t_id}/schedule").json()
    assert len(schedule) > 0

    # Verify Issue 3: For an L1 topic, the L1 SME must be chosen primarily over the L2 SME
    l1_sessions = [s for s in schedule if s["level"] == "L1"]
    assert len(l1_sessions) > 0
    for s in l1_sessions:
        assert s["sme_name"] == "Alice L1 SME", f"Expected same-level SME Alice for L1 topic, got {s['sme_name']}"

    # 10. Verify Issue 1: Receiver Country Holidays checked
    avail = client.get(f"/api/v1/transitions/{t_id}/availability").json()
    assert avail["sme_country"] == "United States"
    assert avail["receiver_country"] == "India"
    # Find Gandhi Jayanti (2026-10-02) in India
    oct2_days = [d for d in avail["days"] if d["date"] == "2026-10-02"]
    if oct2_days:
        assert oct2_days[0]["status"] == "BANK_HOLIDAY"
        assert "India" in oct2_days[0]["holiday_name"]

    # 11. Verify Issue 5: CSV and Excel Exports with Required & Optional attendees
    csv_resp = client.get(f"/api/v1/transitions/{t_id}/export/csv")
    assert csv_resp.status_code == 200
    csv_text = csv_resp.text
    assert "Required Attendees" in csv_text
    assert "Optional Attendees" in csv_text
    assert "Assigned SME" in csv_text
    assert "Assigned Receiver" in csv_text

    # Verify that in L1 session, L1 members are in Required Attendees and L2 members are in Optional Attendees
    lines = csv_text.strip().split("\r\n")
    if len(lines) < 2:
        lines = csv_text.strip().split("\n")
    headers = [h.strip() for h in lines[0].split(",")]
    req_idx = headers.index("Required Attendees")
    opt_idx = headers.index("Optional Attendees")
    lvl_idx = headers.index("Level")

    for line in lines[1:]:
        cols = [c.strip() for c in line.split(",")]
        if len(cols) > max(req_idx, opt_idx, lvl_idx):
            sess_lvl = cols[lvl_idx]
            req_att = cols[req_idx]
            opt_att = cols[opt_idx]
            if sess_lvl == "L1":
                assert "alice.l1@corp.com" in req_att
                assert "carol.l1@corp.com" in req_att
                assert "bob.l2@corp.com" in opt_att
                assert "dave.l2@corp.com" in opt_att

    # Verify Excel Master Package has "Required Attendees" and "Optional Attendees"
    xlsx_resp = client.get(f"/api/v1/transitions/{t_id}/export/xlsx")
    assert xlsx_resp.status_code == 200
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_resp.content))
    assert "KT Schedule" in wb.sheetnames
    ws = wb["KT Schedule"]
    excel_headers = [cell.value for cell in ws[3]]
    assert "Required Attendees" in excel_headers
    assert "Optional Attendees" in excel_headers
    assert "SME Assigned" in excel_headers
    assert "Receiver Assigned" in excel_headers
