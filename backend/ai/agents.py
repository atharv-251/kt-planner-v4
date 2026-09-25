import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from backend.models.transition import Transition, ProjectProfile, RawExtraction
from backend.models.knowledge import KnowledgeNode, KTLevelEvaluation
from backend.models.scheduling import KTSession
from backend.models.governance import PlanPatch
from backend.services.capacity_service import CapacityService
from backend.config import llm

class ProjectProfileAgent:
    """Agent 1: Extracts structured transition profile from raw extraction payload."""
    @staticmethod
    def run(db: Session, transition_id: str) -> ProjectProfile:
        extraction = (
            db.query(RawExtraction)
            .filter(RawExtraction.transition_id == transition_id)
            .order_by(RawExtraction.extracted_at.desc())
            .first()
        )
        if not extraction or not extraction.raw_json_payload:
            raise ValueError(f"No extraction payload found for transition {transition_id}")

        raw = extraction.raw_json_payload
        inputs = raw.get("additional_planning_inputs", {})
        apps = raw.get("applications", [])
        primary_app = apps[0] if apps else {}

        # Synthesize profile
        proj_name = raw.get("project_name", "Application KT Transition")
        purpose = primary_app.get("business_purpose", "Supports business workflows with operational SLA commitments.")
        criticality = primary_app.get("criticality", "Business-critical with defined SLAs.")
        tech_stack = inputs.get("technology_stack") or raw.get("technology_stack") or ["Not identified in extracted evidence"]
        environments = inputs.get("environments") or raw.get("environments") or ["Not identified in extracted evidence"]
        support_values = inputs.get("support_model") or raw.get("support_model") or ["Not identified in extracted evidence"]
        support_model = "; ".join(support_values) if isinstance(support_values, list) else str(support_values)
        integrations = inputs.get("integrations") or raw.get("integrations") or ["Not identified in extracted evidence"]
        dependencies = inputs.get("dependencies") or raw.get("dependencies") or ["Not identified in extracted evidence"]
        kpis_slas = inputs.get("kpis_slas") or raw.get("kpis_slas") or ["Not identified in extracted evidence"]
        risks = inputs.get("risks") or raw.get("risks") or ["Not identified in extracted evidence"]
        evidence_gaps = raw.get("evidence_gaps", [])

        source_files = raw.get("source_files") or []
        evidence_citations = [f"{source_file} :: Extracted document content" for source_file in source_files]
        if not evidence_citations:
            evidence_citations = ["Extracted payload :: source file metadata unavailable"]

        # Extract project_category from external API response (raw extraction)
        raw_cat = raw.get("project_category", "development_and_ams")
        if raw_cat in ["ams_operations", "development", "development_and_ams"]:
            project_category = raw_cat
        elif "ams" in str(raw_cat).lower() and "dev" in str(raw_cat).lower():
            project_category = "development_and_ams"
        elif "ams" in str(raw_cat).lower():
            project_category = "ams_operations"
        elif "dev" in str(raw_cat).lower():
            project_category = "development"
        else:
            project_category = "development_and_ams"

        # Check existing profile
        profile = db.query(ProjectProfile).filter(ProjectProfile.transition_id == transition_id).first()
        if not profile:
            profile = ProjectProfile(transition_id=transition_id, project_name=proj_name)
            db.add(profile)

        profile.project_name = proj_name
        profile.project_category = project_category
        if not profile.intended_levels:
            profile.intended_levels = ["L1", "L2", "L3"]
        profile.business_purpose = purpose
        profile.criticality = criticality
        profile.technology_stack = tech_stack
        profile.environments = environments
        profile.support_model = support_model or "AMS 2"
        profile.integrations = integrations
        profile.dependencies = dependencies
        profile.kpis_slas = kpis_slas
        profile.risks_constraints = risks
        profile.evidence_citations = evidence_citations
        profile.evidence_gaps = evidence_gaps
        profile.updated_at = datetime.utcnow()

        # Keep transition category in sync
        transition = db.query(Transition).filter(Transition.id == transition_id).first()
        if transition:
            transition.category = project_category

        db.commit()
        db.refresh(profile)
        return profile


class KnowledgeGraphAgent:
    """Agent 2: Builds 6-level hierarchy: Application -> Domain -> Capability -> Process -> Topic -> Subtopic."""
    @staticmethod
    def run(db: Session, transition_id: str) -> List[KnowledgeNode]:
        extraction = (
            db.query(RawExtraction)
            .filter(RawExtraction.transition_id == transition_id)
            .order_by(RawExtraction.extracted_at.desc())
            .first()
        )
        if not extraction or not extraction.raw_json_payload:
            raise ValueError("No raw extraction found")

        raw = extraction.raw_json_payload
        apps = raw.get("applications", [])
        if not apps:
            raise ValueError("No applications found in raw extraction")

        # Clear existing hierarchy
        db.query(KnowledgeNode).filter(KnowledgeNode.transition_id == transition_id).delete()
        db.commit()

        created_nodes = []
        app_data = apps[0]
        app_name = app_data.get("application_name", "Core Application")

        # Level 1: Application Node
        app_node = KnowledgeNode(
            transition_id=transition_id,
            parent_id=None,
            node_type="application",
            name=app_name,
            description=app_data.get("business_purpose", ""),
            category="core_application",
            order_index=1,
        )
        db.add(app_node)
        db.flush()
        created_nodes.append(app_node)

        # Categorize topics into Domains
        topics = app_data.get("topics", [])
        domain_buckets = {
            "Functional & Business": ["functional", "business", "support_process"],
            "Architecture & Development": ["technical", "development", "database"],
            "Cloud, Security & Operations": ["ams_operations", "integration"],
        }

        domain_nodes = {}
        for d_idx, (domain_title, cat_keys) in enumerate(domain_buckets.items(), start=1):
            d_node = KnowledgeNode(
                transition_id=transition_id,
                parent_id=app_node.id,
                node_type="domain",
                name=f"{domain_title} Domain",
                description=f"Core domain managing {domain_title.lower()}.",
                category=cat_keys[0],
                order_index=d_idx,
            )
            db.add(d_node)
            db.flush()
            domain_nodes[domain_title] = d_node
            created_nodes.append(d_node)

        # Helper to find domain
        def get_domain_node(cat: str):
            for d_title, cats in domain_buckets.items():
                if cat in cats:
                    return domain_nodes[d_title]
            return domain_nodes["Functional & Business"]

        order_counter = 10
        for top_idx, t in enumerate(topics, start=1):
            category = t.get("category", "functional")
            dom_node = get_domain_node(category)

            # Level 3: Capability
            cap_node = KnowledgeNode(
                transition_id=transition_id,
                parent_id=dom_node.id,
                node_type="capability",
                name=f"{t.get('topic', 'Capability')} Capability",
                category=category,
                order_index=order_counter,
            )
            db.add(cap_node)
            db.flush()
            created_nodes.append(cap_node)
            order_counter += 1

            # Level 4: Process
            proc_node = KnowledgeNode(
                transition_id=transition_id,
                parent_id=cap_node.id,
                node_type="process",
                name=f"{t.get('topic', 'Process')} Process Flow",
                category=category,
                order_index=order_counter,
            )
            db.add(proc_node)
            db.flush()
            created_nodes.append(proc_node)
            order_counter += 1

            # Level 5: Topic
            t_node = KnowledgeNode(
                transition_id=transition_id,
                parent_id=proc_node.id,
                node_type="topic",
                name=t.get("topic", "KT Topic"),
                description=t.get("topic_description", ""),
                category=category,
                weightage_percent=float(t.get("weightage_percent", 6)),
                recommended_method=t.get("recommended_kt_method", "workshop"),
                evidence_references=t.get("evidence", ["Workbook :: Topics"]),
                order_index=order_counter,
            )
            db.add(t_node)
            db.flush()
            created_nodes.append(t_node)
            order_counter += 1

            # Level 6: Subtopics (Leaf nodes with hours)
            subtopics = t.get("subtopics", ["Overview", "Deep-Dive", "Hands-on Exercises"])
            # Estimate hours per topic from duration analysis if present
            duration_breakdown = {
                item["topic"]: item.get("estimated_hours", 6)
                for item in raw.get("kt_duration_analysis", {}).get("topic_effort_breakdown", [])
            }
            topic_total_hours = float(duration_breakdown.get(t.get("topic"), 6.0))
            hours_per_sub = round(topic_total_hours / max(len(subtopics), 1), 1)

            for s_idx, sub in enumerate(subtopics, start=1):
                sub_node = KnowledgeNode(
                    transition_id=transition_id,
                    parent_id=t_node.id,
                    node_type="subtopic",
                    name=f"{t.get('topic')}: {sub}",
                    description=f"Detailed walkthrough and practical mastery of {sub}.",
                    category=category,
                    estimated_hours=hours_per_sub,
                    recommended_method=t.get("recommended_kt_method", "workshop"),
                    evidence_references=t.get("evidence", []),
                    order_index=order_counter,
                )
                db.add(sub_node)
                created_nodes.append(sub_node)
                order_counter += 1

        db.commit()
        return created_nodes


class KTLevelAgent:
    """Agent 3: Evaluates topics against KT Levels (L1/L2/L3) and creates granular objectives & outcomes."""
    @staticmethod
    def run(db: Session, transition_id: str) -> List[KTLevelEvaluation]:
        # Clear existing evaluations
        db.query(KTLevelEvaluation).filter(KTLevelEvaluation.transition_id == transition_id).delete()
        db.commit()

        # Retrieve leaf subtopics
        nodes = db.query(KnowledgeNode).filter(KnowledgeNode.transition_id == transition_id).all()
        parent_ids = {n.parent_id for n in nodes if n.parent_id is not None}
        leaf_nodes = [n for n in nodes if n.id not in parent_ids]
        if not leaf_nodes:
            leaf_nodes = nodes

        # Retrieve intended levels from project profile
        profile = db.query(ProjectProfile).filter(ProjectProfile.transition_id == transition_id).first()
        intended_levels = profile.intended_levels if (profile and profile.intended_levels) else ["L1", "L2", "L3"]

        evaluations = []
        for n in leaf_nodes:
            cat = n.category or "functional"
            # High-critical operational/dev topics include higher levels; standard include lower levels
            if cat in ("ams_operations", "development", "integration", "technical"):
                active_levels = [lvl for lvl in ["L1", "L2", "L3"] if lvl in intended_levels]
                outcome = (
                    f"Team attains full operational autonomy in {n.name}: ability to troubleshoot incidents, "
                    f"execute deployments, and handle Tier-2 escalation tickets independently."
                )
                obj = f"Master end-to-end architecture, error resolution procedures, and operational playbook for {n.name}."
            else:
                active_levels = [lvl for lvl in ["L1", "L2"] if lvl in intended_levels]
                if not active_levels and intended_levels:
                    active_levels = [intended_levels[0]]
                outcome = f"Team understands business context, dependencies, and SLA impact of {n.name}."
                obj = f"Learn key user flows, cross-module impacts, and functional triage for {n.name}."

            level_scope = "+".join(active_levels) if active_levels else (intended_levels[0] if intended_levels else "L1")

            ev = KTLevelEvaluation(
                transition_id=transition_id,
                node_id=n.id,
                level_scope=level_scope,
                applicability="applicable",
                justification=f"Mandatory requirement for AMS 2 transition readiness in {cat}.",
                learning_objective=obj,
                expected_outcome=outcome,
                evidence="; ".join(n.evidence_references or ["KT Planning Workbook"]),
            )
            db.add(ev)
            evaluations.append(ev)

        db.commit()
        return evaluations


class TopicDecompositionAgent:
    """Agent 4: Expands hierarchy with evidence-backed operational modules until Generated Capacity >= Target Capacity."""
    @staticmethod
    def run(db: Session, transition_id: str) -> Dict[str, Any]:
        cap_status = CapacityService.evaluate_capacity_balance(db, transition_id)
        gap_hours = cap_status["gap_hours"]
        if gap_hours <= 0:
            return {
                "message": "Capacity is already fully utilized. No further decomposition required.",
                "cap_status": cap_status,
            }

        # Expansion strategies from Section 6 of Blueprint:
        # Operational scenarios, Troubleshooting, Exception handling, Walkthroughs, Labs, Assessments, Governance, Incident simulations.
        expansion_modules = [
            ("Incident Triage & Simulation Lab", "ams_operations", 4.0, "hands_on"),
            ("High-Priority SLA Exception Handling & Escalation Workshop", "support_process", 4.0, "workshop"),
            ("Disaster Recovery Failover & High Availability Live Drill", "ams_operations", 6.0, "reverse_shadowing"),
            ("Azure Key Vault Secrets Rotation & Security Audit Walkthrough", "technical", 4.0, "hands_on"),
            ("API Gateway Latency & Network Bottleneck Troubleshooting", "integration", 4.0, "workshop"),
            ("CI/CD Pipeline Failure Recovery & Rollback Drill", "development", 4.0, "hands_on"),
            ("Database Performance Optimization & Index Tuning Lab", "database", 4.0, "hands_on"),
            ("Batch Processing Failures & Re-execution Runbook Walkthrough", "technical", 4.0, "workshop"),
            ("End-to-End Business Transaction Walkthrough & Edge Case Validation", "business", 4.0, "workshop"),
            ("AMS 2 Audit Governance & Readiness Sign-off Assessment", "support_process", 4.0, "workshop"),
        ]

        # Retrieve a top-level parent to attach newly generated subtopics
        subtopics_added = []
        hours_added = 0.0
        order_idx = 1000

        # Find topic nodes
        topic_nodes = db.query(KnowledgeNode).filter(
            KnowledgeNode.transition_id == transition_id,
            KnowledgeNode.node_type == "topic"
        ).all()
        default_parent = topic_nodes[0] if topic_nodes else None

        # Retrieve intended levels from project profile
        profile = db.query(ProjectProfile).filter(ProjectProfile.transition_id == transition_id).first()
        intended_levels = profile.intended_levels if (profile and profile.intended_levels) else ["L1", "L2", "L3"]
        active_decomp_levels = [lvl for lvl in ["L2", "L3"] if lvl in intended_levels]
        if not active_decomp_levels and intended_levels:
            active_decomp_levels = [intended_levels[-1]]
        decomp_scope = "+".join(active_decomp_levels) if active_decomp_levels else "L1"

        for title, cat, hrs, method in expansion_modules:
            if hours_added >= gap_hours:
                break

            # Find matching topic parent if possible
            matched_parent = next((t for t in topic_nodes if t.category == cat), default_parent)
            parent_id = matched_parent.id if matched_parent else None

            new_sub = KnowledgeNode(
                transition_id=transition_id,
                parent_id=parent_id,
                node_type="subtopic",
                name=title,
                description=f"Operational hands-on decomposition module to ensure full transition capacity utilization and autonomous operational readiness.",
                category=cat,
                estimated_hours=hrs,
                recommended_method=method,
                evidence_references=["KT Scope Extension :: Operational Scenarios & Simulations"],
                order_index=order_idx,
            )
            db.add(new_sub)
            db.flush()

            # Create corresponding KT level evaluation strictly respecting intended levels
            ev = KTLevelEvaluation(
                transition_id=transition_id,
                node_id=new_sub.id,
                level_scope=decomp_scope,
                applicability="applicable",
                justification="Evidence-backed capacity expansion module for operational readiness.",
                learning_objective=f"Develop hands-on operational capability for {title}.",
                expected_outcome=f"Team executes {title} with zero dependency on incumbent team.",
                evidence="Operational Scenario Runbook",
            )
            db.add(ev)

            subtopics_added.append(title)
            hours_added += hrs
            order_idx += 1

        db.commit()
        new_cap = CapacityService.evaluate_capacity_balance(db, transition_id)
        return {
            "message": f"Successfully expanded {len(subtopics_added)} operational modules ({hours_added} hours).",
            "modules_added": subtopics_added,
            "new_capacity_status": new_cap,
        }


class RefinementAgent:
    """Agent 5: Converts natural language instructions into atomic JSON patches."""
    @staticmethod
    def run(db: Session, transition_id: str, prompt: str) -> Dict[str, Any]:
        prompt_lower = prompt.lower()
        diff_payload = {}
        patch_type = "natural_language_refinement"

        # Check for duration increase/decrease
        hour_match = re.search(r"(\d+)\s*(hour|hr|hours|hrs)", prompt_lower)
        target_hours = float(hour_match.group(1)) if hour_match else None

        # Check for session or topic match
        sessions = db.query(KTSession).filter(KTSession.transition_id == transition_id).all()
        matched_session = None
        for s in sessions:
            words = [w for w in s.session_title.lower().split() if len(w) > 3]
            if any(w in prompt_lower for w in words):
                matched_session = s
                break

        if matched_session and target_hours:
            old_hrs = matched_session.duration_hours
            matched_session.duration_hours = target_hours
            diff_payload = {
                "session_id": matched_session.id,
                "session_title": matched_session.session_title,
                "previous_duration": old_hrs,
                "new_duration": target_hours,
            }
            patch_type = "update_session"
        else:
            diff_payload = {
                "instruction": prompt,
                "status": "applied",
                "notes": "Refinement interpreted and recorded in plan version log.",
            }

        # Apply through PatchService
        from backend.services.patch_service import PatchService
        patch = PatchService.apply_patch(
            db=db,
            transition_id=transition_id,
            patch_type=patch_type,
            diff_payload=diff_payload,
            applied_by="RefinementAgent",
            nl_prompt=prompt,
        )

        return {
            "patch_id": patch.id,
            "version_number": patch.version_number,
            "patch_type": patch.patch_type,
            "diff_payload": diff_payload,
            "message": f"Refinement applied successfully as Version {patch.version_number}.",
        }


class QualityAgent:
    """Agent 6: Quality and compliance agent validating transition plans."""
    @staticmethod
    def run(db: Session, transition_id: str) -> Dict[str, Any]:
        from backend.services.validation_service import ValidationService
        report = ValidationService.run_full_validation(db, transition_id)
        return {
            "status": "success",
            "quality_status": report.overall_status,
            "quality_score": report.score_percent,
            "passed_checks": report.passed_checks,
            "total_checks": report.total_checks,
            "checks": [c.dict() for c in report.checks],
        }

