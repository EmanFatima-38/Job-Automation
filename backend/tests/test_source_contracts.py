from io import BytesIO
import unittest
from unittest.mock import MagicMock, patch
from docx import Document
from app.parsers.docx_parser import extract_text_from_docx
from app.services.job_sources import adzuna_client, remoteok_client, remotive_client, jobicy_client
from app.services.search_planner import fallback_plan
from app.schemas.discovery import Preferences
from types import SimpleNamespace


class SourceTests(unittest.TestCase):
    def test_docx_project_text_is_preserved(self):
        stream = BytesIO()
        doc = Document()
        doc.add_paragraph('Project: RAG assistant using Python and FastAPI')
        doc.save(stream)
        stream.seek(0)
        self.assertIn('FastAPI', extract_text_from_docx(stream))

    def test_remote_feed_keeps_geography(self):
        response = MagicMock()
        response.json.return_value = [{'id': '1', 'position': 'Python developer', 'location': 'US only', 'description': 'Python', 'tags': []}]
        with patch.object(remoteok_client.httpx, 'get', return_value=response):
            rows = remoteok_client.search_remoteok('Python Backend')
        self.assertEqual(rows[0]['remote_eligibility'], 'US only')

    def test_remotive_internship_mapping(self):
        response = MagicMock()
        response.json.return_value = {'jobs': [{'id': 1, 'title': 'Intern', 'job_type': 'internship', 'candidate_required_location': 'Worldwide'}]}
        with patch.object(remotive_client.httpx, 'get', return_value=response):
            self.assertEqual(remotive_client.search_remotive('Intern')[0]['employment_type'], 'internship')

    def test_adzuna_country_normalization_and_pagination(self):
        response = MagicMock()
        response.json.return_value = {'results': []}
        with patch.object(adzuna_client.settings, 'adzuna_app_id', 'test'), patch.object(adzuna_client.settings, 'adzuna_app_key', 'test'), patch.object(adzuna_client.httpx, 'get', return_value=response) as get:
            adzuna_client.search_adzuna('United Kingdom', 'Python', page=2)
        self.assertIn('/gb/search/2', get.call_args.args[0])

    def test_jobicy_invalid_response_is_source_error(self):
        response = MagicMock()
        response.json.side_effect = ValueError('bad JSON')
        with patch.object(jobicy_client.httpx, 'get', return_value=response), self.assertRaises(jobicy_client.JobicyRequestError):
            jobicy_client.search_jobicy('Python')

    def test_remote_only_intent(self):
        user = SimpleNamespace(city='Lahore', country='Pakistan', search_keywords='AI')
        plan = fallback_plan(user, {}, 'Find remote AI internships', Preferences())
        self.assertEqual(plan.work_modes, ['remote'])
        self.assertNotIn('Lahore', plan.locations)

