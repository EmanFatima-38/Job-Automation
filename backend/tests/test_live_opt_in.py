"""Explicit opt-in smoke tests; no email delivery. May consume API quota."""
import os
import unittest


@unittest.skipUnless(os.environ.get('APPLYPILOT_LIVE_TESTS') == '1', 'Live APIs require APPLYPILOT_LIVE_TESTS=1')
class LiveTests(unittest.TestCase):
    def test_remotive_live_contract(self):
        from app.services.job_sources.remotive_client import search_remotive
        rows = search_remotive('Python', limit=1)
        self.assertIsInstance(rows, list)
        self.assertTrue(rows, 'Live source returned no jobs; cannot validate its listing contract')
        for row in rows:
            self.assertTrue(row['external_id'])
            self.assertTrue(row['url'].startswith('https://'))
            self.assertTrue(row['title'])

    @unittest.skipUnless(os.environ.get('APPLYPILOT_PAID_TESTS') == '1', 'Paid search requires APPLYPILOT_PAID_TESTS=1')
    def test_tavily_live_contract(self):
        from app.services.job_sources.vacancy_search import search_vacancies
        rows = search_vacancies('Python internship Pakistan careers', limit=1)
        self.assertTrue(rows, 'No vacancy candidates returned; useful discovery is unverified')
        for row in rows:
            self.assertTrue(row['url'].startswith('https://'))
            self.assertTrue(row['title'])
