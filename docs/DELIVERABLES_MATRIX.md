# KT Planner — Deliverables & Governance Audit Matrix

## Section 15 Deliverables Compliance Matrix

The platform generates eight distinct deliverables defined in Section 15 of the master blueprint. All deliverables are compiled into the master OpenPyXL Excel package (`KT_Master_Plan.xlsx`) and companion raw schedule files:

| # | Deliverable Name | Target Audience | Primary Format | Key Data Attributes |
|---|---|---|---|---|
| **1** | **KT Master Plan** | Transition Program Director, Client Execs | Excel (Sheet 2) / JSON | 6-tier hierarchy (`Application → Domain → Capability → Process → Topic → Subtopic`), category, methods, estimated hours, weightage %, descriptions |
| **2** | **KT Schedule** | SMEs, Participants, Delivery Leads | Excel (Sheet 3) / CSV / FullCalendar | Session title, KT level (L1/L2/L3), calendar date, start/end times, duration hours, delivery mode, assigned SME, status |
| **3** | **Capacity Allocation Report** | Resource Managers, PMO | Excel (Sheet 1) / JSON | Gross duration, shadow/reverse-shadow offsets, net available KT days, target capacity hours, generated hours, balance ratio %, domain breakdown |
| **4** | **Level Coverage Report** | Quality Lead, Training Lead | Excel (Sheet 4) | Topic name, level scope (L1, L2, L3, combinations), applicability, learning objectives, measurable expected outcomes, justifications |
| **5** | **Validation Report** | Governance & Compliance Lead | Excel (Sheet 5) / JSON | Readiness scorecard, overall status (`PASS`, `CONDITIONAL_PASS`, `FAIL`), check-by-check pass/fail status, severity flags |
| **6** | **Source Traceability Matrix** | Auditors, Commercial Lead | Excel (Sheet 6) | Node type, topic name, category, intake worksheet citations, evidence verification rating |
| **7** | **Calendar Availability Report** | Scheduling Coordinators, Leads | Excel (Sheet 7) | Date-by-date calendar status, bank holiday names, working days vs non-working days, daily session load |
| **8** | **Version Audit Report** | Audit Committee, Transition Managers | Excel (Sheet 8) | Monotonic version number (v1, v2...), UTC timestamp, patch type, author / agent identifier, refinement prompt & JSON diff |

---

## Detailed Sheet Structures in Master Workbook (`.xlsx`)

### Sheet 1: Executive Transition Summary
Provides a high-level executive dashboard summarizing the contract baseline:
- Application title and classification
- Start & end dates with gross duration
- Shadow (10 days) and reverse-shadow (10 days) deductions
- Net productive KT days (40 days)
- Target capacity (200.0 hours) vs. Allocated capacity
- Criticality tier and AMS support model

### Sheet 2: KT Master Knowledge Hierarchy
Exhaustive hierarchical inventory across all 6 tiers:
- **Columns**: `Level Type`, `Topic / Subtopic Name`, `Category`, `Est. Hours`, `Delivery Method`, `Weightage %`, `Evidence Sources`, `Description`.

### Sheet 3: Confirmable Session Schedule
Calendar schedule ready for delivery execution:
- **Columns**: `Session Title`, `KT Level`, `Date`, `Day`, `Start Time`, `End Time`, `Duration (Hrs)`, `Delivery Mode`, `SME Assigned`, `Status`, `Conflicts`.

### Sheet 4: L1/L2/L3 Level Coverage Matrix
Detailed pedagogical mapping for adult learning governance:
- **Columns**: `Topic Name`, `Level Scope`, `Applicability`, `Learning Objective`, `Expected Outcome`, `Evidence Justification`.

### Sheet 5: Governance & Validation Scorecard
Authoritative audit checklist:
- **Columns**: `Governance Check`, `Category`, `Result`, `Severity`, `Compliance Message`.

### Sheet 6: Source Evidence Traceability Matrix
Traceability back to contract intake materials:
- **Columns**: `Node Type`, `Topic / Subtopic Name`, `Category`, `Source Document / Sheet Citation`, `Evidence Verification`.

### Sheet 7: Stakeholder & Holiday Calendar Availability
Daily calendar schedule and holiday compliance:
- **Columns**: `Date`, `Day of Week`, `Calendar Status`, `Bank Holiday / Leave Reason`, `Assigned Sessions`.

### Sheet 8: Version History & Refinement Audit Log
Historical audit trail of all manual and AI changes:
- **Columns**: `Version`, `Timestamp (UTC)`, `Patch Type`, `Author / Agent`, `Refinement Prompt / Details`.

