# KT Planner — Enterprise Orchestration Platform

An AI-powered Transition Planning and Knowledge Transfer (KT) orchestration platform that converts uploaded transition documents into a fully validated, level-aware, conflict-free, and schedulable KT Plan.

---

## Documentation Suite (Enterprise Guides)

Complete technical, architectural, and operational manuals are available in the [`docs/`](file:///c:/Users/V6P5LAR/Downloads/KT_Planner_V4/docs) directory:

1. [**Architecture Blueprint (`docs/ARCHITECTURE.md`)**](file:///c:/Users/V6P5LAR/Downloads/KT_Planner_V4/docs/ARCHITECTURE.md):
   - Guiding principles, single deployable service topology, component layout, and security gateway.
2. [**Data Model & Relational Schema Reference (`docs/DATA_MODEL.md`)**](file:///c:/Users/V6P5LAR/Downloads/KT_Planner_V4/docs/DATA_MODEL.md):
   - Entity-Relationship Diagram (ERD), table specifications, column dictionaries, foreign keys, and indexes.
3. [**REST API Reference (`docs/API_REFERENCE.md`)**](file:///c:/Users/V6P5LAR/Downloads/KT_Planner_V4/docs/API_REFERENCE.md):
   - Endpoint reference across all 12 stages, JSON payloads, and Controlled Read-Only SQL API (`POST /api/v1/database/query`).
4. [**Deterministic Core Engines (`docs/DETERMINISTIC_ENGINES.md`)**](file:///c:/Users/V6P5LAR/Downloads/KT_Planner_V4/docs/DETERMINISTIC_ENGINES.md):
   - Mathematical equations, holiday exclusion logic (`holidays.json`), Outlook CSV parser, and conflict algorithms.
5. [**LangGraph Multi-Agent Architecture (`docs/AI_AGENT_WORKFLOW.md`)**](file:///c:/Users/V6P5LAR/Downloads/KT_Planner_V4/docs/AI_AGENT_WORKFLOW.md):
   - Compiled `StateGraph` pipeline, memory isolation principle, and detailed Agent 1 through 6 execution mechanics.
6. [**Deliverables & Governance Matrix (`docs/DELIVERABLES_MATRIX.md`)**](file:///c:/Users/V6P5LAR/Downloads/KT_Planner_V4/docs/DELIVERABLES_MATRIX.md):
   - Section 15 deliverables breakdown and column-by-column structure of the 8-sheet master Excel workbook.
7. [**Operations, Deployment & Runbook (`docs/OPERATIONS_RUNBOOK.md`)**](file:///c:/Users/V6P5LAR/Downloads/KT_Planner_V4/docs/OPERATIONS_RUNBOOK.md):
   - Installation guide, single-service deployment, backup/recovery, health checks, and troubleshooting runbook.

---

## Single Deployable Architecture

```
Browser (React 18 + TypeScript + Tailwind CSS + FullCalendar + React Flow)
   │ (HTTP REST / Controlled SQL Gateway)
   ▼
Uvicorn ASGI Server (:8000)
   ▼
FastAPI Application (backend/main.py)
   ├─► API Routers (/api/v1/...)
   ├─► Static SPA Hosting (frontend/dist)
   ├─► LangGraph AI Agents (Agents 1 through 6)
   ├─► Deterministic Business Engines (Holiday, Capacity, Availability, Schedular, Validation, Export)
   └─► Authoritative SQLite Database (kt_planner.db via SQLAlchemy)
```

---

## Quick Start Guide

### 1. Launch Single Deployable Service
Double-click [`run_kt_planner.bat`](file:///c:/Users/V6P5LAR/Downloads/KT_Planner_V4/run_kt_planner.bat) or run:
```powershell
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
Open your browser at **`http://localhost:8000`**.

### 2. Run Automated Verification Tests
```powershell
python -m pytest tests/ -v
# 13 passed in 6.81s
```

---

## Compliance With Blueprint Requirements

### Tab 14: Transcript-First KT Tracking

Choose the meeting date and a Teams `.vtt` file, then select **Read transcript**.
Previously uploaded transcripts can also be reviewed without uploading again.
The review extracts speakers, the timestamp span, discussion highlights, questions,
follow-up statements, potential concerns, and document mentions locally.
Evidence excerpts include the speaker and the containing speaker-turn time range.

Review the suggested activities and select **Confirm meeting**. Only activities
scheduled for the selected day are checked by default; additional keyword matches
are suggestions, not proof of coverage. Confirmation links the evidence to the
selected activities and changes planned activities to in progress. Reconfirming
the same transcript replaces its activity links without duplicating the meeting.
Other statuses, manual records, and final acceptance remain unchanged.

The **Meetings** view retains reviewed evidence; **Activities** provides search,
status filters, and optional corrections/sign-off. Extraction is deterministic,
not an LLM assessment: speakers are not a full attendance list, transcript duration
is not verified working time, questions may already be answered, and document
mentions do not prove delivery. VTT relative timestamps do not establish a calendar
date, so the meeting date is supplied by the reviewer.

Review API: `GET /api/v1/transitions/{id}/kt-tracker/transcripts/{document_id}/review?meeting_date=YYYY-MM-DD`.
Confirm using `POST` to the same path with `meeting_date` and `activity_ids`.

**AI follow-up analysis:** Select **AI analysis** in a transcript review or an
expanded saved meeting. The configured Agentic Blueprint LLM reviews the full
cleaned transcript for unresolved issues and risks, including later answers,
and proposes questions/actions for the next call. Findings include priority,
resolution uncertainty, and source quotes/timestamps. Human review is required;
the assessment does not change progress or acceptance. Successful results are
stored per transcript; **Run again** refreshes them. Provider failures retain any
previous result and do not fall back to fabricated AI output.

This action requires a valid `LLMAAS_API_KEY` and connectivity to the configured
LLM provider. Replace local setup credentials in the environment configuration
and restart the server; never share credentials in chat. Only clicking the action
sends transcript speech and speaker labels to that provider. The existing
**Read transcript** extraction remains local. Full transcripts above the analysis
size limit are rejected rather than silently truncated.

AI endpoint: `POST /api/v1/transitions/{id}/kt-tracker/transcripts/{document_id}/ai-analysis`
(`?refresh=true` for regeneration). The additive `kt_transcript_assessments` table
is created by the application's existing startup schema initialization.

### Tab 15: Executive Dashboard / Analytics

The read-only dashboard combines the preceding 14 stages for the selected transition.
Date range (scheduled dates, inclusive), domain, KT level, SME, receiver, and activity
status filters apply to delivery metrics, charts, session-linked findings, and CSV export.
The risk register also supports severity, source, and text search. Transition-wide
readiness, capacity, profile risks, validation checks, and unlinked AI assessments
are explicitly outside those delivery filters. Source links open the owning tab.

- Completion is `sum(planned hours * recorded progress / 100) / sum(planned hours)`.
   Cancelled sessions are excluded; no scheduled hours means N/A, not zero or complete.
   Sessions without tracker records use their schedule completion status, otherwise zero progress.
- Completed session count, actual hours, and explicit final acceptance are separate measures.
   Transcript links and invitation records do not prove attendance, delivery, or acceptance.
- The delivery chart is current progress grouped by scheduled date, not historical velocity.
   Overdue means an unfinished activity before today's date in the transition timezone.
- Blockers are recorded tracker text or an on-hold status. Other signals include recorded
   risks, overdue activities, missing participants, and saved scheduling conflicts.
   Import/Graph metadata is not itself a conflict. Validation checks are rule-based,
   not a fresh calendar availability computation.
- Saved AI findings are advisory, may be stale, and are counted once per transcript finding
   even when linked to multiple sessions. Signals from different sources may overlap.
   Mitigations are proposals, not agreed actions; no new AI call or status mutation occurs.

API: `GET /api/v1/transitions/{id}/analytics`, with optional `start_date`, `end_date`,
`domain`, `level`, `sme_id`, `receiver_id`, and `status` query parameters.
Verification: `python -m pytest tests/test_analytics.py -q` and the frontend build.

### Platform Requirements

- [x] **Single Source of Truth**: SQLite database (`kt_planner.db`) holds all projects, hierarchy, evaluations, and schedules.
- [x] **Holidays Management**: Strictly driven by `holidays.json`. Zero hardcoding in Python.
- [x] **Capacity Mathematics**: Available KT Days = Duration - Shadow - Reverse Shadow; 100% capacity balance required.
- [x] **6-Tier Taxonomy**: Application $\rightarrow$ Domain $\rightarrow$ Capability $\rightarrow$ Process $\rightarrow$ Topic $\rightarrow$ Subtopic.
- [x] **KT Level Evaluation**: L1, L2, L3, and composite combinations evaluated independently for all granular topics.
- [x] **Outlook Calendar Ingestion**: Standard CSV headers parsed with optional subject privacy masking.
- [x] **Conflict-Free Scheduling**: Sequencing L1 $\rightarrow$ L2 $\rightarrow$ L3 sessions, skipping weekends, bank holidays, and busy events.
- [x] **LangGraph AI Orchestrator**: Compiled `StateGraph` pipeline with Agents 1 through 6.
- [x] **Controlled Database Gateway**: `POST /api/v1/database/query` allows read-only `SELECT` queries while blocking mutations.
- [x] **Deliverables Package**: 8-sheet Master Excel Workbook (`.xlsx`) and calendar CSV stream.
