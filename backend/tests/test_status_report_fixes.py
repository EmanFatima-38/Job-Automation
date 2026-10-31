"""Regression tests for the fixes from the 23 October 2026 status report."""
import os
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('EMAIL_ENCRYPTION_KEY', 'test-only')
from app.ai.schemas.job_extraction_schema import JobExtraction
from app.services.browser_policy import RenderBudgetExhausted, browser_session, fetch_rendered_page
from app.services.job_mapping import html_to_text, repair_text
from app.services.job_quality import current_plan, enrich_job, preferences_hash
from app.services.job_sources.generic_company_scraper import _careers_score
from app.services.safe_fetch import decode_body
from app.services.work_pool import WorkPool


class WorkPoolTests(unittest.TestCase):
    def test_slow_item_does_not_block_other_keys(self):
        pool = WorkPool('test', 2)
        release, done = threading.Event(), threading.Event()
        pool.submit('slow-user', release.wait, 5)
        pool.submit('other-user', done.set)
        self.assertTrue(done.wait(2), 'second user waited behind the slow one')
        release.set()
        pool.shutdown()

    def test_in_flight_key_is_not_resubmitted(self):
        pool = WorkPool('test', 2)
        release = threading.Event()
        self.assertTrue(pool.submit('user', release.wait, 5))
        self.assertFalse(pool.submit('user', release.wait, 5))
        self.assertTrue(pool.busy('user'))
        release.set()
        for _ in range(50):
            if not pool.busy('user'):
                break
            time.sleep(0.02)
        self.assertFalse(pool.busy('user'))
        pool.shutdown()


class PlanFreshnessTests(unittest.TestCase):
    def test_plan_applies_only_while_preferences_unchanged(self):
        narrow = {'employment_types': ['internship'], 'cities': ['Lahore']}
        plan = {'employment_types': ['internship'], 'preferences_hash': preferences_hash(narrow)}
        job = SimpleNamespace(research={'search_plan': plan})
        self.assertEqual(current_plan(job, SimpleNamespace(preferences=narrow)), plan)
        broadened = {'employment_types': ['internship', 'full_time'], 'cities': ['Lahore']}
        self.assertIsNone(current_plan(job, SimpleNamespace(preferences=broadened)))

    def test_unrelated_preference_changes_keep_plan(self):
        prefs = {'cities': ['Lahore']}
        plan = {'preferences_hash': preferences_hash(prefs)}
        job = SimpleNamespace(research={'search_plan': plan})
        self.assertEqual(current_plan(job, SimpleNamespace(preferences={**prefs, 'notification_min_score': 90})), plan)

    def test_legacy_plan_without_hash_uses_current_preferences(self):
        job = SimpleNamespace(research={'search_plan': {'employment_types': ['internship']}})
        self.assertIsNone(current_plan(job, SimpleNamespace(preferences={})))


class EncodingTests(unittest.TestCase):
    def test_double_decoded_utf8_is_repaired(self):
        self.assertEqual(repair_text('United Kingdom: Â£134,600'), 'United Kingdom: £134,600')
        self.assertEqual(repair_text('Remote â€“ EU'), 'Remote – EU')
        self.assertEqual(repair_text('SÃ£o Paulo, MÃ¼nchen'), 'São Paulo, München')
        self.assertEqual(html_to_text('<p>ZÃ¼rich</p>'), 'Zürich')

    def test_correct_text_is_untouched(self):
        for text in ('São Paulo', 'Zürich – remote', 'Ã O', 'it’s 🚀'):
            self.assertEqual(repair_text(text), text)

    def test_declared_charset_is_used(self):
        self.assertEqual(decode_body('Café'.encode('cp1252'), 'text/html; charset=windows-1252'), 'Café')
        self.assertIn('Zürich', decode_body(b'<meta charset="iso-8859-1">Z\xfcrich'))
        self.assertEqual(decode_body('Zürich'.encode()), 'Zürich')
        self.assertEqual(decode_body(b'Z\xfcrich'), 'Zürich')


class CareersPageTests(unittest.TestCase):
    def test_policy_and_article_pages_are_never_chosen(self):
        for text, href in [('Terms of Service', 'https://x.com/terms-of-service'), ('Privacy', 'https://x.com/privacy'),
                           ('Career tips', 'https://x.com/blog/career-tips'), ('Join our team', 'https://x.com/about-us')]:
            self.assertEqual(_careers_score(text, href), 0, href)

    def test_careers_paths_and_ats_hosts_rank_highest(self):
        self.assertGreater(_careers_score('Careers', 'https://x.com/about/careers'), _careers_score('Work with us', 'https://x.com/team'))
        self.assertGreater(_careers_score('Jobs', 'https://boards.greenhouse.io/x'), _careers_score('Jobs', 'https://x.com/jobs'))


class RenderBudgetTests(unittest.TestCase):
    def job(self):
        return SimpleNamespace(source_url='https://apply.workable.com/acme/j/1/', research={}, raw_input_text='Python Intern at Acme',
                               title='Python Intern', company='Acme', location=None, salary_range=None, employment_type=None,
                               work_mode=None, contact_email=None, requirements=[], description_text=None, canonical_url=None,
                               extraction_status='pending', extraction_error=None, fingerprint=None)

    def test_exhausted_budget_defers_without_ai_call(self):
        with browser_session(max_renders=0):
            with self.assertRaises(RenderBudgetExhausted):
                with patch('app.services.browser_policy.validate_public_url'):
                    fetch_rendered_page('https://example.com/job')

        with patch('app.services.job_quality.fetch_public_page', return_value=('<div id="app"></div>', 'https://apply.workable.com/acme/j/1/')), \
             patch('app.services.job_quality.fetch_rendered_page', side_effect=RenderBudgetExhausted('used up')), \
             patch('app.services.job_quality.extract_job', return_value=JobExtraction(title='x', requirements=[], description_summary='x')) as extract:
            job = enrich_job(self.job())
        extract.assert_not_called()
        self.assertEqual(job.research['enrichment_state'], 'deferred')
        self.assertEqual(job.extraction_status, 'pending')
        self.assertTrue(job.research['retry_after'])
        self.assertNotIn('evidence_version', job.research)






class ColumnWidthTests(unittest.TestCase):
    def test_long_model_output_is_clipped_to_column(self):
        from app.services.job_quality import fit_column
        salary = '$190,500 USD annually (US); £134,600 GBP annually (UK); C$253,500 CAD annually (Canada); €157,350 EUR'
        self.assertEqual(len(fit_column('salary_range', salary)), 100)
        self.assertEqual(fit_column('salary_range', '$100k'), '$100k')
