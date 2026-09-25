from datetime import date, time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import backend.models
from backend.database import Base, get_db
from backend.models.knowledge import KnowledgeNode
from backend.models.scheduling import KTSession
from backend.models.stakeholder import Stakeholder
from backend.models.tracker import KTTrackingActivity, KTTranscriptAssessment
from backend.models.transition import ProjectProfile, Transition, UploadedDocument
from backend.routers.modules import router


@pytest.fixture
def analytics_client():
    engine = create_engine('sqlite://', poolclass=StaticPool, connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        application = FastAPI()
        application.include_router(router)
        application.dependency_overrides[get_db] = lambda: db
        db.add(Transition(id='analytics', name='Analytics test', timezone='UTC'))
        db.add(Transition(id='other', name='Other transition'))
        db.add(KnowledgeNode(id='domain', transition_id='analytics', name='Payments', node_type='domain'))
        db.add(KnowledgeNode(id='topic', transition_id='analytics', parent_id='domain', name='Settlement', node_type='topic'))
        db.flush()
        for identifier, hours, status, progress in [('done', 2, 'completed', 100), ('partial', 6, 'in_progress', 50), ('cancelled', 8, 'cancelled', 0)]:
            db.add(KTSession(id=identifier, transition_id='analytics', node_id='topic', session_title=identifier,
                             scheduled_date=date(2020, 1, 1), start_time=time(10), end_time=time(12),
                             duration_hours=hours, level='L1', conflict_flags={'source': 'teams_schedule_csv'}))
            db.flush()
            db.add(KTTrackingActivity(id=identifier, session_id=identifier, transition_id='analytics',
                                      activity_name=identifier, status=status, progress_percent=progress,
                                      blocker='Access pending' if identifier == 'partial' else '',
                                      transcript_analysis={'meeting_reviews': {'transcript': {}}, 'manual_evidence': {}}))
        db.add(UploadedDocument(id='transcript', transition_id='analytics', file_name='meeting.vtt', file_path='unused'))
        db.flush()
        db.add(KTTranscriptAssessment(document_id='transcript', transition_id='analytics', result={
            'findings': [{'title': 'Access risk', 'kind': 'risk', 'priority': 'high', 'status': 'uncertain',
                          'detail': 'Needs review', 'suggested_action': 'Confirm access', 'evidence': []}]}))
        db.commit()
        with TestClient(application) as client:
            yield client, db
    engine.dispose()


def test_analytics_is_read_only_and_hours_weighted(analytics_client):
    client, db = analytics_client
    before = db.query(KTTrackingActivity).count()
    response = client.get('/api/v1/transitions/analytics/analytics')
    assert response.status_code == 200
    result = response.json()
    assert result['metrics']['completion_percent'] == 62.5
    assert result['metrics']['planned_hours'] == 8
    assert result['metrics']['completed'] == 1
    assert result['metrics']['accepted'] == 0
    assert result['metrics']['blocked'] == 1
    assert result['metrics']['overdue'] == 1
    assert result['metrics']['conflicts'] == 0
    assert len([finding for finding in result['findings'] if finding['source'] == 'AI transcript']) == 1
    assert len(result['stages']) == 14
    assert db.query(KTTrackingActivity).count() == before
    assert db.get(KTTrackingActivity, 'partial').progress_percent == 50


def test_analytics_filters_and_empty_scope(analytics_client):
    client, db = analytics_client
    path = '/api/v1/transitions/analytics/analytics'
    assert client.get(path, params={'status': 'completed'}).json()['metrics']['completion_percent'] == 100
    assert client.get(path, params={'domain': 'Payments', 'level': 'L1'}).json()['metrics']['total'] == 2
    empty = client.get(path, params={'start_date': '2030-01-01'}).json()
    assert empty['metrics']['completion_percent'] is None
    assert empty['metrics']['total'] == 0
    assert empty['findings'] == []
    assert client.get(path, params={'start_date': '2030-01-01', 'end_date': '2020-01-01'}).status_code == 422
    assert client.get('/api/v1/transitions/other/analytics').json()['metrics']['total'] == 0
    assert client.get('/api/v1/transitions/missing/analytics').status_code == 404
    assert db.query(KTTrackingActivity).count() == 3


def test_analytics_untracked_zero_hours_and_inclusive_dates(analytics_client):
    client, db = analytics_client
    db.add(KTSession(id='untracked', transition_id='analytics', node_id='topic', session_title='Untracked session',
                     scheduled_date=date(2030, 1, 1), start_time=time(10), end_time=time(11), duration_hours=0))
    db.commit()
    response = client.get('/api/v1/transitions/analytics/analytics', params={'start_date': '2030-01-01', 'end_date': '2030-01-01'})
    assert response.status_code == 200
    result = response.json()
    assert result['metrics']['completion_percent'] is None
    assert result['metrics']['total'] == 1
    assert result['metrics']['untracked'] == 1
    assert result['sessions'][0]['status'] == 'planned'
    assert db.query(KTTrackingActivity).count() == 3


def test_analytics_people_filters_and_real_conflicts(analytics_client):
    client, db = analytics_client
    db.add_all([Stakeholder(id='sme', transition_id='analytics', name='Owner', role='sme'),
                Stakeholder(id='receiver', transition_id='analytics', name='Receiver', role='receiver')])
    db.flush()
    session = db.get(KTSession, 'partial')
    session.sme_id = 'sme'
    session.receiver_id = 'receiver'
    session.conflict_flags = ['SME calendar conflict']
    db.commit()
    result = client.get('/api/v1/transitions/analytics/analytics', params={'sme_id': 'sme', 'receiver_id': 'receiver'}).json()
    assert result['metrics']['total'] == 1
    assert result['metrics']['completion_percent'] == 50
    assert result['metrics']['conflicts'] == 1
    assert result['sessions'][0]['sme'] == 'Owner'
    assert result['sessions'][0]['receiver'] == 'Receiver'
    assert client.get('/api/v1/transitions/analytics/analytics', params={'sme_id': 'missing'}).json()['metrics']['total'] == 0


def test_missing_profile_risks_are_evidence_gaps(analytics_client):
    client, db = analytics_client
    db.add(ProjectProfile(transition_id='analytics', project_name='Analytics', risks_constraints=['Not identified in extracted evidence']))
    db.commit()
    result = client.get('/api/v1/transitions/analytics/analytics').json()
    finding = next(item for item in result['project_findings'] if item['source'] == 'Project Profile')
    assert finding['kind'] == 'open_issue'
    assert finding['certainty'] == 'Evidence gap'
    assert finding['title'] == 'Risk assessment evidence missing'