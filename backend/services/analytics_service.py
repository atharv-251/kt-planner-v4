from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import json

from sqlalchemy.orm import Session

from backend.models.tracker import KTTrackingActivity, KTTranscriptAssessment
from backend.models.transition import Transition
from backend.services.capacity_service import CapacityService
from backend.services.teams_scheduler_service import invite_was_sent, valid_recipients
from backend.services.validation_service import ValidationService


def _percent(numerator: float, denominator: float) -> float | None:
    return round(100 * numerator / denominator, 1) if denominator else None


def _mitigation(text: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ('access', 'permission', 'credential')):
        return 'Assign an access owner, raise the required permission request, and verify access before the next session.'
    if any(word in lowered for word in ('document', 'runbook', 'mapping')):
        return 'Request the missing artifact from its owner and schedule a walkthrough with receiver acknowledgement.'
    return 'Assign an accountable owner, agree a target date, and verify the resolution in the next KT review.'


def build_analytics(db: Session, transition: Transition, filters: dict) -> dict:
    try:
        local_zone = ZoneInfo(transition.timezone or 'UTC')
    except ZoneInfoNotFoundError:
        local_zone = ZoneInfo('UTC')
    today = datetime.now(local_zone).date()
    nodes = {node.id: node for node in transition.knowledge_nodes}
    people = {person.id: person for person in transition.stakeholders}
    activities = {activity.session_id: activity for activity in db.query(KTTrackingActivity).filter_by(transition_id=transition.id).all()}
    rows = []
    for session in sorted(transition.sessions, key=lambda item: (item.scheduled_date, item.start_time, item.id)):
        activity = activities.get(session.id)
        status = activity.status if activity else ('completed' if session.status == 'completed' else 'cancelled' if session.status == 'cancelled' else 'planned')
        analysis = (activity.transcript_analysis or {}) if activity else {}
        evidence = analysis.get('manual_evidence') or {}
        node = nodes.get(session.node_id)
        domain = 'Unassigned'
        visited = set()
        while node and node.id not in visited:
            visited.add(node.id)
            if node.node_type == 'domain':
                domain = node.name
                break
            node = nodes.get(node.parent_id)
        flags = session.conflict_flags or []
        conflicts = flags if isinstance(flags, list) else flags.get('conflicts', [])
        recipients = valid_recipients([
            people[identifier].email for identifier in (session.sme_id, session.receiver_id) if identifier in people
        ] + (flags.get('source_recipients', []) if isinstance(flags, dict) else []))
        sent = invite_was_sent(
            session_id=session.id,
            start_at=datetime.combine(session.scheduled_date, session.start_time).replace(tzinfo=local_zone),
            end_at=datetime.combine(session.scheduled_date, session.end_time).replace(tzinfo=local_zone),
            recipients=recipients,
        ) if recipients else False
        progress = 100 if status == 'completed' else max(0, min(100, activity.progress_percent or 0)) if activity else 0
        transcript_ids = set((analysis.get('meeting_reviews') or {}).keys())
        if analysis.get('transcript_id'):
            transcript_ids.add(analysis['transcript_id'])
        if isinstance(evidence.get('transcript'), dict) and evidence['transcript'].get('id'):
            transcript_ids.add(evidence['transcript']['id'])
        rows.append({
            'id': session.id, 'title': session.session_title, 'date': session.scheduled_date.isoformat(),
            'domain': domain, 'level': session.level or 'Unassigned', 'mode': session.delivery_mode,
            'sme_id': session.sme_id or 'unassigned', 'receiver_id': session.receiver_id or 'unassigned',
            'sme': people[session.sme_id].name if session.sme_id in people else 'Unassigned',
            'receiver': people[session.receiver_id].name if session.receiver_id in people else 'Unassigned',
            'status': status, 'progress': progress, 'hours': max(0, session.duration_hours or 0),
            'blocker': (activity.blocker or '').strip() if activity else '',
            'risk': (activity.risk or '').strip() if activity else '',
            'tracked': activity is not None, 'accepted': bool(evidence.get('final_acceptance')),
            'readiness': evidence.get('readiness', 'not_assessed'),
            'shadowing': bool(evidence.get('shadowing_completed')),
            'reverse_shadowing': bool(evidence.get('reverse_shadowing_completed')),
            'actual_hours': evidence.get('actual_hours') or 0,
            'conflicts': conflicts, 'invited': sent, 'transcript_ids': sorted(transcript_ids),
            'overdue': session.scheduled_date < today and status not in ('completed', 'cancelled'),
        })
    active_rows = [row for row in rows if row['status'] != 'cancelled']
    selected = [row for row in active_rows if all(not filters.get(key) or row[key] == filters[key] for key in ('domain', 'level', 'sme_id', 'receiver_id', 'status'))
                and (not filters.get('start_date') or row['date'] >= filters['start_date'].isoformat())
                and (not filters.get('end_date') or row['date'] <= filters['end_date'].isoformat())]
    total_hours = sum(row['hours'] for row in selected)
    earned_hours = sum(row['hours'] * row['progress'] / 100 for row in selected)
    metrics = {
        'total': len(selected), 'completed': sum(row['status'] == 'completed' for row in selected),
        'completion_percent': _percent(earned_hours, total_hours),
        'planned_hours': round(total_hours, 2), 'earned_hours': round(earned_hours, 2),
        'actual_hours': round(sum(row['actual_hours'] for row in selected), 2),
        'accepted': sum(row['accepted'] for row in selected),
        'blocked': sum(bool(row['blocker']) or row['status'] == 'on_hold' for row in selected),
        'overdue': sum(row['overdue'] for row in selected),
        'conflicts': sum(bool(row['conflicts']) for row in selected),
        'invited': sum(row['invited'] for row in selected),
        'evidenced': sum(bool(row['transcript_ids']) for row in selected),
        'untracked': sum(not row['tracked'] for row in selected),
        'shadowing': sum(row['shadowing'] for row in selected),
        'reverse_shadowing': sum(row['reverse_shadowing'] for row in selected),
    }
    findings = []
    project_findings = []

    def finding(identifier, kind, severity, title, detail, action, source, step, owner='Unassigned', session_ids=None, evidence=None, certainty='Recorded'):
        return {'id': identifier, 'kind': kind, 'severity': severity, 'title': title, 'detail': detail,
                'action': action, 'source': source, 'step': step, 'owner': owner,
                'session_ids': session_ids or [], 'evidence': evidence or [], 'certainty': certainty}

    for row in selected:
        for field, kind, severity in [('blocker', 'blocker', 'high'), ('risk', 'risk', 'medium')]:
            if row[field]:
                findings.append(finding(f"{row['id']}:{field}", kind, severity, row[field], row['title'], _mitigation(row[field]), 'KT Tracker', 14, row['sme'], [row['id']]))
        if row['status'] == 'on_hold' and not row['blocker']:
            findings.append(finding(f"{row['id']}:hold", 'blocker', 'high', 'Activity on hold', row['title'], 'Confirm the hold reason and agree a restart date with the session owner.', 'KT Tracker', 14, row['sme'], [row['id']]))
        if row['overdue']:
            findings.append(finding(f"{row['id']}:overdue", 'risk', 'medium', 'Overdue KT activity', f"{row['title']} was scheduled for {row['date']}.", 'Confirm recorded progress and replan remaining coverage with the SME and receiver.', 'Schedule / Tracker', 14, row['sme'], [row['id']], certainty='Derived'))
        if row['conflicts']:
            findings.append(finding(f"{row['id']}:conflict", 'risk', 'high', 'Recorded scheduling conflict', str(row['conflicts']), 'Review participant availability and move the session to a conflict-free slot.', 'Schedule', 10, row['sme'], [row['id']], certainty='Recorded'))
        if row['sme_id'] == 'unassigned' or row['receiver_id'] == 'unassigned':
            findings.append(finding(f"{row['id']}:assignment", 'risk', 'medium', 'Missing participant assignment', row['title'], 'Assign a qualified SME and receiver and verify their availability.', 'People / Schedule', 4, row['sme'], [row['id']], certainty='Derived'))

    documents = {document.id: document for document in transition.documents}
    for assessment in db.query(KTTranscriptAssessment).filter_by(transition_id=transition.id).all():
        linked = [row['id'] for row in selected if assessment.document_id in row['transcript_ids']]
        all_linked = any(assessment.document_id in row['transcript_ids'] for row in rows)
        for index, item in enumerate((assessment.result or {}).get('findings', [])):
            entry = finding(f'{assessment.document_id}:{index}', item.get('kind', 'risk'), item.get('priority', 'medium'),
                            item.get('title', 'Transcript finding'), item.get('detail', ''), item.get('suggested_action', ''),
                            'AI transcript', 14, session_ids=linked, evidence=item.get('evidence'), certainty=f"AI / {item.get('status', 'uncertain')}")
            entry['document'] = documents[assessment.document_id].file_name if assessment.document_id in documents else 'Transcript'
            entry['analyzed_at'] = (assessment.result or {}).get('analyzed_at')
            entry['next_call_question'] = item.get('next_call_question', '')
            if linked:
                findings.append(entry)
            elif not all_linked:
                project_findings.append(entry)

    profile = transition.profile
    if profile:
        for index, risk in enumerate(profile.risks_constraints or []):
            text = risk if isinstance(risk, str) else json.dumps(risk, ensure_ascii=False)
            if text.strip().lower() in {'not identified in extracted evidence', 'not specified', 'unknown'}:
                project_findings.append(finding(f'profile:{index}', 'open_issue', 'medium', 'Risk assessment evidence missing',
                                                'The profile does not contain a documented risk assessment.',
                                                'Review risks with the transition lead and record the assessment in the project profile.',
                                                'Project Profile', 2, certainty='Evidence gap'))
                continue
            project_findings.append(finding(f'profile:{index}', 'risk', 'medium', text, 'Profile risk / constraint; current resolution is not recorded.', _mitigation(text), 'Project Profile', 2, certainty='Needs review'))
    capacity = CapacityService.evaluate_capacity_balance(db, transition.id)
    validation = ValidationService.run_full_validation(db, transition.id).model_dump()
    for check in validation['checks']:
        if check['check_name'] == 'Conflict-Free Availability':
            count = sum(bool(row['conflicts']) for row in active_rows)
            check.update(passed=count == 0, message=f'{count} active sessions have recorded conflict flags; import metadata is excluded.')
        if not check['passed']:
            project_findings.append(finding(f"validation:{check['check_name']}", 'risk', 'high' if check['severity'] == 'critical' else 'medium',
                                            check['check_name'], check['message'], capacity['recommendation'] if check['category'] == 'capacity' else 'Review the validation check, correct its source records, and validate again before publication.',
                                            'Validation', 11, certainty='Rule check'))
    priority = {'high': 0, 'medium': 1, 'low': 2}
    findings.sort(key=lambda item: (priority.get(item['severity'], 1), item['id']))
    project_findings.sort(key=lambda item: (priority.get(item['severity'], 1), item['id']))
    metrics['risk_findings'] = sum(item['kind'] != 'blocker' for item in findings)
    metrics['health'] = 'No data' if not selected else 'Blocked' if metrics['blocked'] else 'At risk' if findings else 'No recorded risks'

    domains = []
    for domain in sorted({row['domain'] for row in selected}):
        members = [row for row in selected if row['domain'] == domain]
        hours = sum(row['hours'] for row in members)
        earned = sum(row['hours'] * row['progress'] / 100 for row in members)
        domains.append({'name': domain, 'planned': round(hours, 2), 'earned': round(earned, 2), 'completion': _percent(earned, hours)})
    buckets = defaultdict(lambda: {'planned': 0, 'earned': 0, 'completed': 0})
    for row in selected:
        bucket = buckets[row['date']]
        bucket['planned'] += row['hours']
        bucket['earned'] += row['hours'] * row['progress'] / 100
        bucket['completed'] += row['status'] == 'completed'
    timeline = [{'date': day, **{key: round(value, 2) for key, value in values.items()}} for day, values in sorted(buckets.items())]
    parents = {node.parent_id for node in nodes.values() if node.parent_id}
    leaves = [node for node in nodes.values() if node.id not in parents]
    evaluated = {item.node_id for item in transition.kt_evaluations if item.learning_objective and item.expected_outcome}
    covered = len({node.id for node in leaves} & evaluated)
    source_docs = sum(not document.file_name.lower().endswith('.vtt') for document in documents.values())
    transcripts = len(documents) - source_docs
    checks_passed = sum(check['passed'] for check in validation['checks'])
    calendar_people = sum(bool(person.calendar_events) for person in people.values())
    invited = sum(row['invited'] for row in active_rows)
    tracked = sum(row['tracked'] for row in active_rows)
    stage_data = [
        (1, 'Document intake', f'{source_docs} source documents / {len(transition.raw_extractions)} extractions', bool(source_docs and transition.raw_extractions)),
        (2, 'Profile review', 'Approved' if profile and profile.is_approved else 'Awaiting approval' if profile else 'No profile', bool(profile and profile.is_approved)),
        (3, 'Transition settings', f'{transition.start_date} to {transition.end_date} / {transition.timezone}', bool(transition.start_date and transition.end_date and transition.end_date >= transition.start_date)),
        (4, 'SMEs & people', f'{len(people)} stakeholders / {sum(row["sme_id"] == "unassigned" or row["receiver_id"] == "unassigned" for row in active_rows)} sessions with unassigned participants', bool(people) and all(row['sme_id'] != 'unassigned' and row['receiver_id'] != 'unassigned' for row in active_rows)),
        (5, 'Knowledge hierarchy', f'{len(nodes)} nodes / {len(leaves)} leaf topics', bool(leaves)),
        (6, 'KT levels', f'{covered} of {len(leaves)} leaf topics evaluated', bool(leaves) and covered == len(leaves)),
        (7, 'Capacity', f"{capacity['generated_hours']}h curriculum / {capacity['target_capacity_hours']}h target", capacity['status'] == 'BALANCED'),
        (8, 'Session inventory', f'{len(active_rows)} active / {len(rows) - len(active_rows)} cancelled sessions', bool(active_rows)),
        (9, 'Availability', f'{calendar_people} of {len(people)} stakeholders with calendar records', bool(people) and calendar_people == len(people)),
        (10, 'Schedule', f'{sum(bool(row["conflicts"]) for row in active_rows)} active sessions with recorded conflicts', bool(active_rows) and not any(row['conflicts'] for row in active_rows)),
        (11, 'Validation', f'{checks_passed} of {len(validation["checks"])} checks passed', bool(validation['checks']) and checks_passed == len(validation['checks'])),
        (12, 'Publish & deliver', transition.status.replace('_', ' ').title(), transition.status == 'published'),
        (13, 'Teams invitations', f'{invited} of {len(active_rows)} active sessions with sent invitation records', bool(active_rows) and invited == len(active_rows)),
        (14, 'KT Tracker', f'{tracked} of {len(active_rows)} sessions tracked / {transcripts} transcripts', bool(active_rows) and tracked == len(active_rows)),
    ]
    return {
        'generated_at': datetime.now(timezone.utc).isoformat(), 'as_of': today.isoformat(),
        'transition': {'id': transition.id, 'name': transition.name, 'status': transition.status, 'timezone': str(local_zone)},
        'metrics': metrics, 'sessions': selected, 'findings': findings, 'project_findings': project_findings,
        'domains': domains, 'timeline': timeline,
        'status_distribution': [{'name': status, 'value': count} for status, count in sorted(Counter(row['status'] for row in selected).items())],
        'stages': [{'step': step, 'name': name, 'detail': detail, 'ready': ready} for step, name, detail, ready in stage_data],
        'capacity': capacity,
        'options': {'domains': sorted({row['domain'] for row in active_rows}), 'levels': sorted({row['level'] for row in active_rows}),
                    'statuses': sorted({row['status'] for row in active_rows}),
                    'smes': [{'id': identifier, 'name': name} for identifier, name in sorted({(row['sme_id'], row['sme']) for row in active_rows}, key=lambda item: item[1])],
                    'receivers': [{'id': identifier, 'name': name} for identifier, name in sorted({(row['receiver_id'], row['receiver']) for row in active_rows}, key=lambda item: item[1])]},
    }