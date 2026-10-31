import os
import unittest
from unittest.mock import patch

os.environ.setdefault('EMAIL_ENCRYPTION_KEY', 'test-only')
from app.schemas.discovery import SearchPlan
from app.services.crawl_service import rank_by_plan
from app.services.job_sources import ats_feeds
from app.services.original_posting import find_original_posting, is_aggregator


class FeedTests(unittest.TestCase):
    def test_workable_keeps_pakistan_jobs_and_existing_identity(self):
        data = {'jobs': [
            {'title': 'AI Engineer', 'shortcode': 'ABC123', 'employment_type': 'Full-time', 'telecommuting': False,
             'published_on': '2026-10-22', 'application_url': 'https://apply.workable.com/j/ABC123/apply', 'description': '<p>Build LLM apps</p>',
             'locations': [{'city': 'Lahore', 'region': 'Punjab', 'country': 'Pakistan'}]},
            {'title': 'Sales Lead', 'shortcode': 'XYZ', 'locations': [{'city': 'Riyadh', 'country': 'Saudi Arabia'}]},
        ]}
        with patch.object(ats_feeds, '_get', return_value=data):
            jobs = ats_feeds.search_workable_feed('devsinc-17', 'Devsinc')
        self.assertEqual([j['title'] for j in jobs], ['AI Engineer'])
        job = jobs[0]
        self.assertEqual(job['url'], 'https://apply.workable.com/devsinc-17/j/ABC123/')
        self.assertEqual(job['external_id'], 'workable:devsinc-17:https://apply.workable.com/devsinc-17/j/ABC123/')
        self.assertEqual((job['employment_type'], job['posted_at'], job['description']), ('full_time', '2026-10-22', 'Build LLM apps'))

    def test_greenhouse_uses_first_published_and_unescapes_content(self):
        data = {'jobs': [{'id': 1, 'title': 'Backend Engineer', 'location': {'name': 'Hybrid - Lahore'}, 'absolute_url': 'https://boards.greenhouse.io/x/jobs/1',
                          'first_published': '2026-09-18T10:00:00-04:00', 'updated_at': '2026-10-22T00:00:00Z', 'content': '&lt;p&gt;Python &amp; Go&lt;/p&gt;'},
                         {'id': 2, 'title': 'US Role', 'location': {'name': 'San Francisco, CA'}}]}
        with patch.object(ats_feeds, '_get', return_value=data):
            jobs = ats_feeds.search_greenhouse('x', 'X')
        self.assertEqual(len(jobs), 1)
        self.assertEqual((jobs[0]['posted_at'], jobs[0]['description'], jobs[0]['work_mode']), ('2026-09-18', 'Python & Go', 'hybrid'))

    def test_lever_and_ashby_parse(self):
        lever = [{'id': 'a', 'text': 'Engineer', 'categories': {'commitment': 'Intern', 'allLocations': ['Lahore']}, 'country': 'PK',
                  'workplaceType': 'onsite', 'createdAt': 1792700000000, 'hostedUrl': 'https://jobs.lever.co/x/a', 'descriptionPlain': 'Role'}]
        with patch.object(ats_feeds, '_get', return_value=lever):
            job = ats_feeds.search_lever('x', 'X')[0]
        self.assertEqual((job['employment_type'], job['work_mode'], job['location']), ('internship', 'onsite', 'Lahore'))
        ashby = {'jobs': [{'id': 'b', 'title': 'Analyst', 'isListed': True, 'employmentType': 'FullTime', 'workplaceType': 'OnSite',
                           'address': {'postalAddress': {'addressLocality': 'Lahore', 'addressCountry': 'Pakistan'}},
                           'jobUrl': 'https://jobs.ashbyhq.com/x/b', 'publishedAt': '2026-09-08T09:17:24Z', 'descriptionPlain': 'Role'},
                          {'id': 'c', 'title': 'Hidden', 'isListed': False, 'location': 'Lahore'}]}
        with patch.object(ats_feeds, '_get', return_value=ashby):
            jobs = ats_feeds.search_ashby('x', 'X')
        self.assertEqual([(j['title'], j['location'], j['posted_at']) for j in jobs], [('Analyst', 'Lahore, Pakistan', '2026-09-08')])

    def test_ranking_prefers_planned_roles_by_whole_word(self):
        plan = SearchPlan(roles=['AI Engineer'], skills=['Python'])
        jobs = [{'title': 'Account Executive – Spanish Speaking', 'description': 'maintain email campaigns'},
                {'title': 'Senior AI Engineer', 'description': 'Python'}]
        self.assertEqual(rank_by_plan(jobs, plan)[0]['title'], 'Senior AI Engineer')


class OriginalPostingTests(unittest.TestCase):
    def test_aggregator_detection(self):
        self.assertTrue(is_aggregator('https://pk.jooble.org/jdp/1'))
        self.assertTrue(is_aggregator('https://pk.linkedin.com/jobs/view/x'))
        self.assertFalse(is_aggregator('https://careers.techxaro.com/jobs/ai-intern'))

    def test_accepts_employer_domain_or_named_ats_board_only(self):
        results = [{'url': 'https://pk.indeed.com/viewjob?jk=1', 'title': 'AI Engineer Intern - Techxaro'},
                   {'url': 'https://boards.greenhouse.io/othercorp/jobs/9', 'title': 'AI Engineer Intern'},
                   {'url': 'https://techxaro.com/careers/ai-engineer-intern', 'title': 'AI Engineer Intern | Techxaro'}]
        url = find_original_posting('AI Engineer Intern', 'Techxaro Pvt Ltd', search=lambda *a, **k: results)
        self.assertEqual(url, 'https://techxaro.com/careers/ai-engineer-intern')
        ats = [{'url': 'https://jobs.lever.co/techxaro/abc', 'title': 'AI Engineer Intern'}]
        self.assertEqual(find_original_posting('AI Engineer Intern', 'Techxaro', search=lambda *a, **k: ats), ats[0]['url'])

    def test_requires_role_match_and_specific_title(self):
        careers_index = [{'url': 'https://techxaro.com/careers', 'title': 'Careers at Techxaro', 'content': 'Join our team'}]
        self.assertIsNone(find_original_posting('AI Engineer Intern', 'Techxaro', search=lambda *a, **k: careers_index))
        self.assertIsNone(find_original_posting('Job', 'Cloudelligent', search=lambda *a, **k: self.fail('should not search')))


class CareersIndexTests(unittest.TestCase):
    def test_follows_careers_index_to_the_role_link(self):
        results = [{'url': 'https://cloudelligent.com/careers', 'title': 'Careers - Join the Dream Team | Cloudelligent'}]
        page = '<a href="/careers/devops-engineer">DevOps Engineer</a><a href="/careers/ai-engineer-intern">AI Engineer Intern</a>'
        url = find_original_posting('AI Engineer Intern', 'Cloudelligent', search=lambda *a, **k: results,
                                    fetch=lambda u: (page, 'https://cloudelligent.com/careers'))
        self.assertEqual(url, 'https://cloudelligent.com/careers/ai-engineer-intern')

    def test_index_without_matching_role_gives_nothing(self):
        results = [{'url': 'https://cloudelligent.com/careers', 'title': 'Careers'}]
        url = find_original_posting('AI Engineer Intern', 'Cloudelligent', search=lambda *a, **k: results,
                                    fetch=lambda u: ('<a href="/careers/sales">Sales Manager</a>', 'https://cloudelligent.com/careers'))
        self.assertIsNone(url)
