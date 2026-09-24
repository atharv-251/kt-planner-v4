# KT Planner — REST API Reference & Integration Guide

Base URL: `http://localhost:8000/api/v1`

Interactive Swagger UI: `http://localhost:8000/docs`  
ReDoc Documentation: `http://localhost:8000/redoc`

---

## 1. Transitions API

### `POST /transitions`
Creates a new transition project shell.

**Request Body (`application/json`)**:
```json
{
  "name": "Retail Banking Modernization KT",
  "category": "development_and_ams",
  "start_date": "2026-09-20",
  "end_date": "2026-10-30",
  "total_duration_days": 60,
  "shadow_days": 10,
  "reverse_shadow_days": 10,
  "daily_kt_hours": 5.0,
  "primary_country": "India",
  "timezone": "Asia/Kolkata"
}
```

**Response (`200 OK`)**:
```json
{
  "id": "c1f7b88d-56a8-48b4-934c-687f7a29e46a",
  "name": "Retail Banking Modernization KT",
  "category": "development_and_ams",
  "status": "draft",
  "start_date": "2026-09-20",
  "end_date": "2026-10-30",
  "total_duration_days": 60,
  "shadow_days": 10,
  "reverse_shadow_days": 10,
  "available_kt_days": 40,
  "daily_kt_hours": 5.0,
  "target_capacity_hours": 200.0,
  "primary_country": "India",
  "timezone": "Asia/Kolkata",
  "created_at": "2026-09-21T01:00:00.000Z",
  "updated_at": "2026-09-21T01:00:00.000Z"
}
```

---

### `PUT /transitions/{id}/settings`
Updates project timeline parameters and recalculates capacity targets dynamically.

**Request Body (`application/json`)**:
```json
{
  "total_duration_days": 65,
  "shadow_days": 10,
  "reverse_shadow_days": 10,
  "daily_kt_hours": 5.0,
  "primary_country": "CzechRepublic"
}
```

---

## 2. Documents & Extraction API

### `POST /transitions/{id}/upload`
Uploads an intake workbook (`.xlsx`, `.docx`, `.pdf`, `.json`).

**Request (`multipart/form-data`)**:
- `file`: Binary file upload

**Response (`200 OK`)**:
```json
{
  "id": "e812ab56-11f4-411a-82ef-2940c31278ab",
  "transition_id": "c1f7b88d-56a8-48b4-934c-687f7a29e46a",
  "file_name": "KT_Planning_Workbook.xlsx",
  "file_size": 34816,
  "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "uploaded_at": "2026-09-21T01:05:00.000Z"
}
```

---

### `POST /transitions/{id}/extract`
Triggers external document extraction adapter or processes the pre-loaded canonical workbook.

**Response (`200 OK`)**:
```json
{
  "status": "success",
  "message": "Documents extracted successfully from canonical transition adapter.",
  "project_name": "Test Application Name KT",
  "total_topics": 15
}
```

---

## 3. Project Profile API (Agent 1)

### `POST /transitions/{id}/profile/generate`
Invokes **Agent 1 (Project Profile Agent)** to synthesize project attributes, evidence citations, and gap warnings.

**Response (`200 OK`)**:
```json
{
  "id": "b1a52e67-8321-4d37-975e-5b1285496ac7",
  "transition_id": "c1f7b88d-56a8-48b4-934c-687f7a29e46a",
  "project_name": "Test Application Name KT",
  "business_purpose": "Supports documented business processes with AMS 2-level support.",
  "criticality": "Business-critical with defined SLAs.",
  "technology_stack": ["Java 17 / Spring Boot", "Azure Cloud Services", "Azure Key Vault"],
  "environments": ["Azure Dev/Test", "Azure UAT", "Azure Production"],
  "support_model": "AMS 2 Application Group",
  "integrations": ["API-based external integrations", "File storage data exchange"],
  "dependencies": ["Database connectivity and Azure networking", "External APIs"],
  "kpis_slas": ["Response: P1 < 15m, Resolution < 4h", "Availability 99.9%"],
  "risks_constraints": ["Security vulnerability management", "DR and HA misconfiguration"],
  "evidence_citations": ["KT_Planning_Workbook.xlsx :: Worksheet: Topics"],
  "evidence_gaps": ["No detailed functional module list provided."],
  "is_approved": false
}
```

---

### `POST /transitions/{id}/profile/approve`
Formally signs off on the project profile.

**Request Body**:
```json
{
  "approved_by": "Transition Lead Architect",
  "comments": "Scope and technology stack confirmed with client."
}
```

---

## 4. Knowledge Hierarchy API (Agents 2 & 4)

### `POST /transitions/{id}/hierarchy/generate`
Invokes **Agent 2 (Knowledge Graph Agent)** to generate the 6-tier taxonomy:
`Application → Domain → Capability → Process → Topic → Subtopic`.

---

### `GET /transitions/{id}/hierarchy?view=nested`
Returns the hierarchical tree structure for React Flow and tree table rendering.

**Response (`200 OK`)**:
```json
[
  {
    "id": "app-001",
    "node_type": "application",
    "name": "Test Application Name",
    "category": "core_application",
    "estimated_hours": 0.0,
    "children": [
      {
        "id": "dom-001",
        "node_type": "domain",
        "name": "Architecture & Development Domain",
        "children": [
          {
            "id": "cap-001",
            "node_type": "capability",
            "name": "Java Architecture Capability",
            "children": [
              {
                "id": "sub-001",
                "node_type": "subtopic",
                "name": "Java Frameworks & Layered Design",
                "estimated_hours": 4.0,
                "recommended_method": "workshop",
                "category": "technical",
                "children": []
              }
            ]
          }
        ]
      }
    ]
  }
]
```

---

### `POST /transitions/{id}/hierarchy/decompose`
Invokes **Agent 4 (Topic Decomposition Agent)** to expand operational modules until $\text{Generated Capacity} \ge \text{Target Capacity}$.

**Response (`200 OK`)**:
```json
{
  "message": "Successfully expanded 10 operational modules (42.0 hours).",
  "modules_added": [
    "Incident Triage & Simulation Lab",
    "Disaster Recovery Failover & High Availability Live Drill"
  ],
  "new_capacity_status": {
    "target_capacity_hours": 200.0,
    "generated_hours": 200.0,
    "balance_ratio_percent": 100.0,
    "status": "BALANCED"
  }
}
```

---

## 5. KT Levels API (Agent 3)

### `POST /transitions/{id}/levels/evaluate`
Invokes **Agent 3 (KT Level Agent)** to independently evaluate every topic for L1/L2/L3 objectives, outcomes, and evidence justifications.

---

### `PUT /transitions/{id}/levels/{evalId}`
Updates an individual topic's KT level scope, objectives, or expected outcome.

---

## 6. Stakeholders & Calendar Import API

### `POST /transitions/{id}/stakeholders`
Registers a new SME or team participant.

---

### `POST /transitions/{id}/stakeholders/{smeId}/calendar-csv?mask_subjects=false`
Uploads an Outlook CSV calendar file.

**Supported Headers**: `Subject`, `Start Date`, `Start Time`, `End Date`, `End Time`, `All day event`, `Reminder on/off`.

---

## 7. Availability & Schedular API

### `POST /transitions/{id}/schedule/auto-build`
Executes the deterministic, conflict-free scheduling engine.

**Request Body**:
```json
{
  "daily_start_hour": 10,
  "daily_max_hours": 5.0,
  "auto_assign_smes": true
}
```

---

### `GET /transitions/{id}/schedule/fullcalendar`
Returns formatted session slots ready for FullCalendar rendering with color coding and conflict flags.

---

## 8. Governance & Validation API (Agents 5 & 6)

### `GET /transitions/{id}/validation`
Runs deterministic governance verification scorecard.

**Response (`200 OK`)**:
```json
{
  "overall_status": "PASS",
  "score_percent": 100.0,
  "total_checks": 5,
  "passed_checks": 5,
  "failed_checks": 0,
  "checks": [
    {
      "check_name": "Holiday & Weekend Adherence",
      "category": "calendar",
      "passed": true,
      "severity": "info",
      "message": "All scheduled sessions strictly respect bank holidays in India and weekends."
    }
  ]
}
```

---

### `POST /transitions/{id}/refine`
Invokes **Agent 5 (Refinement Agent)** to translate natural language user prompts into atomic JSON patches.

**Request Body**:
```json
{
  "prompt": "Increase duration of CI/CD pipeline session to 4 hours and assign to Dev Sharma"
}
```

---

## 9. Controlled Read-Only Database API

### `POST /database/query`
Enterprise read-only SQL gateway for reporting tools and agents.

**Request Body**:
```json
{
  "query": "SELECT node_type, count(*) as count FROM knowledge_nodes WHERE transition_id = :t_id GROUP BY node_type",
  "params": {
    "t_id": "c1f7b88d-56a8-48b4-934c-687f7a29e46a"
  }
}
```

**Security Enforcement**:
- `SELECT`, `WITH`, and `EXPLAIN` statements are permitted.
- `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`, `REPLACE`, `ATTACH`, `DETACH`, `PRAGMA`, and `VACUUM` return `HTTP 403 Forbidden`.

---

## 10. Exports API

### `GET /transitions/{id}/export/xlsx`
Streams the 8-sheet Master Transition Workbook (`.xlsx`).

### `GET /transitions/{id}/export/csv`
Streams the raw calendar schedule (`.csv`).

