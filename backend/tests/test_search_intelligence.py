import unittest
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from app.schemas.discovery import Preferences
from app.services.search_planner import fallback_plan, build_plan
from app.services.safe_fetch import validate_public_url, fetch_public_page, _download
from app.services.portfolio_service import refresh_portfolio, candidate_profile
from app.services.job_sources.vacancy_search import search_vacancies


class SearchIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.user = SimpleNamespace(country='Pakistan', city='Lahore', search_keywords='AI Engineer', preferences={}, portfolio_data={})

    def test_fallback_interprets_internship_geography_and_recency(self):
        p = fallback_plan(self.user, {'skills': ['Python']}, 'Find AI internships Lahore Islamabad Karachi remote Pakistan last seven days', Preferences())
        self.assertEqual(p.employment_types, ['internship'])
        self.assertEqual(p.max_age_days, 7)
        self.assertTrue(p.remote)
        self.assertIn('Karachi', p.locations)
        self.assertGreater(len(p.queries), 1)

    def test_planner_failure_has_queries(self):
        with patch('app.services.search_planner.parse_structured', side_effect=RuntimeError):
            self.assertTrue(build_plan(self.user, {}, 'Python backend jobs').queries)

    def test_private_url_rejected(self):
        with patch('socket.getaddrinfo', return_value=[(2, 1, 6, '', ('127.0.0.1', 443))]):
            with self.assertRaises(ValueError):
                validate_public_url('https://example.com')

    def test_unsafe_scheme_rejected(self):
        with self.assertRaises(ValueError):
            validate_public_url('file:///etc/passwd')

    def test_portfolio_failure_preserves_evidence(self):
        self.user.preferences = {'portfolio_urls': ['https://example.com']}
        self.user.portfolio_data = {'https://example.com': {'text': 'old evidence'}}
        with patch('app.services.portfolio_service.fetch_public_page', side_effect=ValueError('blocked')):
            result = refresh_portfolio(MagicMock(), self.user)
        self.assertEqual(result['https://example.com']['text'], 'old evidence')

    def test_vacancy_hit_is_unverified(self):
        with patch('app.services.job_sources.vacancy_search.tavily_search', return_value=[{'url': 'https://example.com/job/1', 'title': 'Intern'}]):
            self.assertEqual(search_vacancies('intern')[0]['verification_status'], 'unverified')

    def test_robots_disallow_stops_fetch(self):
        with patch('app.services.safe_fetch.validate_public_url'), patch('app.services.safe_fetch._download', return_value=('User-agent: *\nDisallow: /', 'https://example.com/robots.txt')) as download:
            with self.assertRaises(ValueError):
                fetch_public_page('https://example.com/jobs')
            self.assertEqual(download.call_count, 1)

    def test_redirect_target_is_validated(self):
        response = MagicMock(is_redirect=True, headers={'location': 'http://127.0.0.1/private'})
        with patch('app.services.safe_fetch.httpx.Client') as client, patch('app.services.safe_fetch.validate_public_url', side_effect=[None, ValueError('private')]) as validate:
            client.return_value.__enter__.return_value.stream.return_value.__enter__.return_value = response
            with self.assertRaises(ValueError):
                _download('https://example.com')
            self.assertEqual(validate.call_args.args[0], 'http://127.0.0.1/private')

    def test_response_size_is_bounded(self):
        response = MagicMock(is_redirect=False, headers={'content-type': 'text/html'})
        response.iter_bytes.return_value = [b'x' * 2_000_001]
        with patch('app.services.safe_fetch.httpx.Client') as client, patch('app.services.safe_fetch.validate_public_url'):
            client.return_value.__enter__.return_value.stream.return_value.__enter__.return_value = response
            with self.assertRaises(ValueError):
                _download('https://example.com')
