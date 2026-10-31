import os
import unittest
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

os.environ.setdefault('EMAIL_ENCRYPTION_KEY', 'test-only')
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base
import app.models
from app.models.user import User
from app.models.resume import Resume
from app.models.job import Job
from app.models.match import Match
from app.models.crawl_run import CrawlRun
from app.models.opportunity_delivery import OpportunityDelivery
from app.ai.schemas.job_extraction_schema import JobExtraction
from app.ai.schemas.match_score_schema import MatchScore
from app.schemas.discovery import SearchPlan
from app.services.crawl_service import enqueue_search, execute_run
from app.services.discovery_store import store_candidate
from app.services.discovery_backlog import process_user_backlog, match_context
from app.services.opportunity_service import send_opportunities
from app.services.recommendation_policy import POLICY_VERSION


@compiles(JSONB, 'sqlite')
def jsonb_sqlite(type_, compiler, **kw):
    return 'JSON'


@contextmanager
def unlocked(*args):
    yield True


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', poolclass=StaticPool, connect_args={'check_same_thread': False})
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine, expire_on_commit=False)
        self.user = User(email='test@example.com', hashed_password='x', country='Pakistan', city='Lahore', search_keywords='Python', preferences={})
        self.db.add(self.user)
        self.db.commit()
        self.lock = patch('app.services.discovery_lock.discovery_lock', unlocked)
        self.lock.start()

    def tearDown(self):
        self.lock.stop()
        self.db.close()
        self.engine.dispose()

    def raw(self, index=1):
        return {'external_id': f'test:{index}', 'source': 'test', 'url': f'https://example.com/jobs/{index}', 'title': f'Python Intern {index}', 'company': 'Acme', 'location': 'Lahore', 'description': 'Python internship responsibilities and application instructions', 'employment_type': 'internship'}

    def resume(self):
        resume = Resume(user_id=self.user.id, original_filename='test.pdf', file_path='test.pdf', file_type='pdf', raw_text='Python', is_primary=True, parse_status='parsed', structured_profile={'summary': 'Python developer', 'skills': ['Python'], 'experience': [], 'education': []})
        self.db.add(resume)
        self.db.commit()
        return resume

    def test_cross_source_dedup_preserves_id(self):
        job, created = store_candidate(self.db, self.user.id, self.raw(), {})
        self.db.commit()
        second = {**self.raw(), 'external_id': 'other:123', 'url': self.raw()['url']+'?utm_source=foo'}
        same, created_again = store_candidate(self.db, self.user.id, second, {})
        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(job.id, same.id)

    def test_queue_idempotent(self):
        a = enqueue_search(self.db, self.user, 'internships')
        b = enqueue_search(self.db, self.user, 'jobs')
        self.assertEqual(a.id, b.id)

    def test_source_failure_preserves_success(self):
        run = enqueue_search(self.db, self.user, 'internships')
        def bad():
            raise RuntimeError('source unavailable')
        sources = [('good', 'python', lambda: [self.raw()]), ('bad', 'python', bad)]
        with patch('app.services.search_planner.build_plan', return_value=SearchPlan(roles=['Python'], queries=['Python internship'])), patch('app.services.crawl_service._sources', return_value=iter(sources)):
            result = execute_run(self.db, run)
        self.assertEqual(result.status, 'partial')
        self.assertEqual(result.jobs_created, 1)
        self.assertTrue(result.source_results[1]['error'])

    def test_all_sources_fail_is_failed(self):
        run = enqueue_search(self.db, self.user)
        def bad():
            raise RuntimeError('offline')
        with patch('app.services.search_planner.build_plan', return_value=SearchPlan()), patch('app.services.crawl_service._sources', return_value=iter([('bad', 'q', bad)])):
            self.assertEqual(execute_run(self.db, run).status, 'failed')

    def test_backlog_scores_more_than_first_six(self):
        self.resume()
        for i in range(9):
            job, _ = store_candidate(self.db, self.user.id, self.raw(i), {})
            job.extraction_status = 'extracted'
            job.research = {**job.research, 'evidence_version': POLICY_VERSION, 'last_verified_at': datetime.now(timezone.utc).isoformat(), 'is_job_posting': True}
        self.db.commit()
        result = MatchScore(score=80, matched_skills=['Python'], missing_skills=[], rationale='Relevant skills')
        with patch('app.services.match_service.score_match', return_value=result):
            process_user_backlog(self.db, self.user)
            process_user_backlog(self.db, self.user)
        self.assertEqual(len(list(self.db.scalars(select(Match)))), 9)

    def test_context_changes_when_cv_changes(self):
        resume = self.resume()
        job, _ = store_candidate(self.db, self.user.id, self.raw(), {})
        before = match_context(self.user, resume, job)
        resume.structured_profile = {**resume.structured_profile, 'skills': ['Python', 'FastAPI']}
        self.assertNotEqual(before, match_context(self.user, resume, job))

    def test_notification_requires_consent(self):
        with patch('app.services.opportunity_service.send_email') as send:
            self.assertEqual(send_opportunities(self.db, self.user), 0)
            send.assert_not_called()

    def test_notification_send_is_deduplicated(self):
        resume = self.resume()
        self.user.preferences = {'notifications_enabled': True}
        job, _ = store_candidate(self.db, self.user.id, self.raw(), {})
        job.research = {**job.research, 'state': 'active', 'verification_status': 'page_checked', 'is_job_posting': True, 'application_link_status': 'reachable', 'posted_at': datetime.now(timezone.utc).isoformat(), 'evidence_version': POLICY_VERSION, 'last_verified_at': datetime.now(timezone.utc).isoformat()}
        match = Match(job_id=job.id, resume_id=resume.id, match_score=90, matched_skills=['Python'], missing_skills=[], rationale='Relevant', context_hash=match_context(self.user, resume, job))
        self.db.add(match)
        self.db.commit()
        with patch('app.services.opportunity_service.get_email_account', return_value=MagicMock()), patch('app.services.opportunity_service.send_email') as send:
            self.assertEqual(send_opportunities(self.db, self.user), 1)
            self.assertEqual(send_opportunities(self.db, self.user), 0)
            send.assert_called_once()
            self.assertEqual(send.call_args.args[1], self.user.email)

    def test_cancelled_search_does_not_run(self):
        run = enqueue_search(self.db, self.user)
        run.status = 'cancelled'
        self.db.commit()
        with patch('app.services.search_planner.build_plan') as plan:
            self.assertEqual(execute_run(self.db, run).status, 'cancelled')
            plan.assert_not_called()

    def test_worker_recovers_abandoned_run(self):
        from app.services.crawl_service import process_search_queue
        run = enqueue_search(self.db, self.user)
        run.status = 'running'
        self.db.commit()
        with patch('app.services.crawl_service.SessionLocal', return_value=self.db):
            process_search_queue()
        with Session(self.engine) as db:
            self.assertEqual(db.get(CrawlRun, run.id).status, 'interrupted')

    def test_queue_dispatches_without_waiting_for_runs(self):
        from app.services.crawl_service import process_search_queue
        run = enqueue_search(self.db, self.user)
        pool = MagicMock()
        pool.busy.return_value = False
        with patch('app.services.crawl_service.SessionLocal', return_value=self.db), patch('app.services.crawl_service._pool', return_value=pool), \
             patch('app.services.crawl_service.execute_run') as execute:
            process_search_queue()
        execute.assert_not_called()
        pool.submit.assert_called_once()
        self.assertEqual(pool.submit.call_args.args[0], run.id)

    def test_backlog_yields_to_queued_search(self):
        self.resume()
        store_candidate(self.db, self.user.id, self.raw(), {})
        self.db.commit()
        enqueue_search(self.db, self.user)
        with patch('app.services.discovery_backlog.enrich_job') as enrich:
            process_user_backlog(self.db, self.user)
        enrich.assert_not_called()

    def test_one_unsavable_job_does_not_abort_backlog(self):
        self.resume()
        first, _ = store_candidate(self.db, self.user.id, self.raw(1), {})
        second, _ = store_candidate(self.db, self.user.id, self.raw(2), {})
        self.db.commit()
        calls = []
        def enrich(job):
            calls.append(job.id)
            if len(calls) == 1:
                raise RuntimeError('value too long')
            job.extraction_status = 'extracted'
            return job
        with patch('app.services.discovery_backlog.enrich_job', side_effect=enrich), patch('app.services.match_service.score_match', side_effect=RuntimeError('no AI')):
            process_user_backlog(self.db, self.user)
        self.assertEqual(len(calls), 2)
        failed = [j for j in (first, second) if j.id == calls[0]][0]
        self.assertEqual(failed.extraction_status, 'failed')
        self.assertTrue(failed.research['retry_after'])

    def test_application_survives_posting_expiration(self):
        from app.services.application_service import create_application, update_application
        from app.schemas.application import ApplicationCreate, ApplicationUpdate
        from app.models.application import Application
        job, _ = store_candidate(self.db, self.user.id, self.raw(), {})
        application = create_application(self.db, self.user.id, ApplicationCreate(job_id=job.id))
        update_application(self.db, self.user.id, application.id, ApplicationUpdate(status='applied'))
        job.research = {**job.research, 'state': 'expired'}
        self.db.commit()
        self.assertEqual(self.db.get(Application, application.id).status, 'applied')

    def test_manual_ingestion_uses_shared_enrichment(self):
        from app.services.job_service import ingest_job
        from app.schemas.job import JobCreate
        with patch('app.services.job_quality.extract_job', return_value=JobExtraction(title='Python Intern', requirements=['Python'], description_summary='Intern', is_job_posting=True)):
            job = ingest_job(self.db, self.user.id, JobCreate(source_type='text', raw_text='Python internship'))
        self.assertEqual(job.requirements, ['Python'])
        self.assertEqual(job.research['enrichment_state'], 'completed')

    def test_employer_followups_still_send_to_employer(self):
        from app.models.application import Application
        from app.services.followup_service import run_followups_for_user
        resume = self.resume()
        job, _ = store_candidate(self.db, self.user.id, self.raw(), {})
        job.contact_email = 'careers@example.org'
        application = Application(user_id=self.user.id, job_id=job.id, resume_id=resume.id, status='applied', applied_at=datetime.now(timezone.utc))
        self.db.add(application)
        self.db.commit()
        with patch('app.services.followup_service.get_email_account', return_value=MagicMock()), patch('app.services.followup_service._eligible_applications', return_value=[application]), patch('app.services.followup_service.generate_followup_email', return_value=('Follow up', 'Hello')), patch('app.services.followup_service.send_email') as send:
            application.applied_at = datetime.now(timezone.utc)
            result = run_followups_for_user(self.db, self.user)
            self.assertEqual(result[0].status, 'sent')
            self.assertEqual(send.call_args.args[1], 'careers@example.org')

    def test_search_api_queue_history_cancel_and_ownership(self):
        from fastapi.testclient import TestClient
        from app.main import app
        from app.database import get_db
        from app.api.deps import get_current_user
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.user
        try:
            client = TestClient(app)  # no lifespan: no scheduler or external services
            response = client.post('/api/v1/search', json={'intent': 'Find AI internships'})
            self.assertEqual(response.status_code, 202)
            run_id = response.json()['id']
            self.assertEqual(client.get('/api/v1/search/history').json()[0]['id'], run_id)
            other = User(email='other@example.com', hashed_password='x')
            self.db.add(other)
            self.db.commit()
            app.dependency_overrides[get_current_user] = lambda: other
            self.assertEqual(client.post(f'/api/v1/search/{run_id}/cancel').status_code, 404)
            app.dependency_overrides[get_current_user] = lambda: self.user
            cancelled = client.post(f'/api/v1/search/{run_id}/cancel')
            self.assertEqual(cancelled.json()['status'], 'cancelled')
            self.assertIsNotNone(cancelled.json()['finished_at'])
        finally:
            app.dependency_overrides.clear()

    def test_legacy_routes_still_registered(self):
        from app.main import app
        paths = app.openapi()['paths']
        for path in ['/api/v1/jobs', '/api/v1/resumes', '/api/v1/applications', '/api/v1/email-account', '/api/v1/crawl/run', '/api/v1/jobs/{job_id}/documents']:
            self.assertIn(path, paths)

    def test_failed_scoring_is_bounded(self):
        self.resume()
        for i in range(12):
            job, _ = store_candidate(self.db, self.user.id, self.raw(i), {})
            job.extraction_status = 'extracted'
            job.research = {**job.research, 'evidence_version': POLICY_VERSION, 'last_verified_at': datetime.now(timezone.utc).isoformat()}
        self.db.commit()
        with patch('app.services.match_service.score_match', side_effect=RuntimeError('API unavailable')) as score:
            process_user_backlog(self.db, self.user)
            self.assertEqual(score.call_count, 8)

    def test_duplicate_after_enrichment_preserves_rows(self):
        from app.services.discovery_store import reconcile_identity
        a, _ = store_candidate(self.db, self.user.id, self.raw(1), {})
        b, _ = store_candidate(self.db, self.user.id, self.raw(2), {})
        a.fingerprint = b.fingerprint = 'same-verified-identity'
        self.db.commit()
        reconcile_identity(self.db, a)
        reconcile_identity(self.db, b)
        duplicates = [j for j in (a, b) if j.research.get('duplicate_of')]
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(len(list(self.db.scalars(select(Job)))), 2)
