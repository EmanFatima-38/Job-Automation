import os
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault('EMAIL_ENCRYPTION_KEY', 'test-only')

from app.services.job_mapping import html_to_text
from app.services import application_service, followup_service
from app.services.resume_service import _apply_profile_defaults
from app.ai.schemas.resume_profile_schema import ResumeProfile
from app.services.job_sources.remoteok_client import _map_employment_type


class PreservationTests(unittest.TestCase):
    def test_html_description_is_readable(self):
        self.assertEqual(html_to_text('<p>Python</p><p>FastAPI</p>'), 'Python\nFastAPI')

    def test_internship_classification(self):
        self.assertEqual(_map_employment_type(['intern']), 'internship')

    def test_manual_profile_is_preserved(self):
        user = MagicMock(country='Pakistan', city='Karachi', search_keywords='Intern')
        db = MagicMock()
        db.get.return_value = user
        profile = ResumeProfile(summary='', skills=[], experience=[], education=[], city='Lahore', target_roles=['Engineer'])
        _apply_profile_defaults(db, 'user', profile)
        self.assertEqual(user.city, 'Karachi')
        self.assertEqual(user.search_keywords, 'Intern')

    def test_duplicate_application_rejected(self):
        db = MagicMock()
        db.scalar.return_value = object()
        with self.assertRaises(application_service.DuplicateApplicationError):
            application_service.create_application(db, 'user', MagicMock(job_id='job'))

    def test_no_followup_without_email_account(self):
        with patch.object(followup_service, 'get_email_account', return_value=None), patch.object(followup_service, 'send_email') as send:
            self.assertEqual(followup_service.run_followups_for_user(MagicMock(), MagicMock()), [])
            send.assert_not_called()
