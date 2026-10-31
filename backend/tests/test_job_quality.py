import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.services.job_quality import canonical_url, fingerprint, jsonld_job, eligibility, enrich_job
from app.ai.schemas.job_extraction_schema import JobExtraction


class QualityTests(unittest.TestCase):
    def job(self, **kwargs):
        data = dict(title='Python Intern', company='Acme', location='Lahore', raw_input_text='Python internship',
                    research={}, source_url='https://example.com/jobs/1', canonical_url=None,
                    employment_type='internship', work_mode='onsite')
        return SimpleNamespace(**{**data, **kwargs})

    def test_tracking_removed_identity_retained(self):
        self.assertEqual(canonical_url('https://EXAMPLE.com/job/?id=1&utm_source=a#apply'), 'https://example.com/job?id=1')

    def test_fingerprint_requires_location(self):
        self.assertIsNone(fingerprint('Engineer', 'Acme', None))

    def test_jsonld_graph(self):
        self.assertEqual(jsonld_job('<script type="application/ld+json">{"@graph":[{"@type":"JobPosting","title":"Intern"}]}</script>')['title'], 'Intern')

    def test_expired_filtered(self):
        rejected, _ = eligibility(self.job(research={'state': 'expired'}), {})
        self.assertTrue(rejected)

    def test_unknown_freshness_is_not_verified(self):
        _, concerns = eligibility(self.job(), {'max_age_days': 7})
        self.assertTrue(any('date unknown' in s for s in concerns))

    def test_employment_filter(self):
        rejected, _ = eligibility(self.job(employment_type='full_time'), {'employment_types': ['internship']})
        self.assertTrue(rejected)

    def test_no_active_claim_from_search_snippet(self):
        extraction = JobExtraction(title='Intern', requirements=[], description_summary='Intern', is_job_posting=True, application_available=True)
        with patch('app.services.job_quality.fetch_public_page', side_effect=ValueError('blocked')), patch('app.services.job_quality.extract_job', return_value=extraction):
            job = enrich_job(self.job())
        self.assertEqual(job.research['state'], 'unknown')
        self.assertEqual(job.research['verification_status'], 'unverified')

    def test_shared_listing_enrichment_preserves_its_own_snippet(self):
        # The generic company scraper gives every listing on a shared careers page the
        # same source_url. Re-fetching that page during enrichment must not overwrite each
        # listing's own distinct snippet with the shared page's full text - otherwise
        # several distinct real postings collapse into duplicate copies of just one of them.
        job = self.job(research={'shared_listing': True},
                        raw_input_text='AI Software Engineer, Cloud Platforms: own distinct snippet for this posting')
        extraction = JobExtraction(title='AI Software Engineer, Cloud Platforms', requirements=[], description_summary='x', is_job_posting=True)
        shared_page_html = '<h1>Careers at Acme</h1><p>Software Engineer, Advanced Analytics</p><p>AI Software Engineer, Embedded Systems</p>'
        with patch('app.services.job_quality.fetch_public_page', return_value=(shared_page_html, job.source_url)), patch('app.services.job_quality.extract_job', return_value=extraction) as extract:
            enrich_job(job)
        self.assertIn('own distinct snippet for this posting', job.raw_input_text)
        self.assertIn('own distinct snippet for this posting', extract.call_args.args[0])

    def test_short_static_fetch_falls_back_to_rendered_page(self):
        # A JS-rendered SPA or a bot-protection challenge shell (Cloudflare etc.) comes
        # back from a plain GET as a near-empty page - real content only shows up after
        # a browser actually runs the page's JavaScript. Confirmed live against a real
        # Workable-hosted posting during this audit.
        shell_html = '<div id="app"><div class="loader">Loading...</div></div>'
        # No distinct "Apply" anchor here - keeps this test isolated to the primary-page
        # fallback; the apply-link reachability fallback has its own dedicated test.
        rendered_html = '<h1>Python Intern</h1><p>Acme is hiring a paid Python intern. Requirements include Python and FastAPI experience. We offer mentoring and a supportive team.</p>'
        extraction = JobExtraction(title='Python Intern', company='Acme', requirements=['Python'], description_summary='Intern', is_job_posting=True)
        with patch('app.services.job_quality.fetch_public_page', return_value=(shell_html, 'https://apply.workable.com/acme/j/1/')) as static_fetch, \
             patch('app.services.job_quality.fetch_rendered_page', return_value=(rendered_html, 'https://apply.workable.com/acme/j/1/')) as rendered_fetch, \
             patch('app.services.job_quality.extract_job', return_value=extraction):
            job = enrich_job(self.job())
        static_fetch.assert_called_once()
        rendered_fetch.assert_called_once()
        self.assertIn('hiring a paid Python intern', job.raw_input_text)
        self.assertEqual(job.research['verification_status'], 'page_checked')

    def test_jsonld_deadline_overrides_model(self):
        extraction = JobExtraction(title='Intern', requirements=[], description_summary='Intern', deadline='2099-01-01', is_job_posting=True)
        html = '<script type="application/ld+json">{"@type":"JobPosting","validThrough":"2000-01-01"}</script>'
        # Body text here is intentionally short (JSON-LD only) - also exercises the
        # render-fallback path for short pages; a second render attempt here would reach
        # out to the real network in production, so it must be mocked in tests too, same
        # as the static fetch.
        with patch('app.services.job_quality.fetch_public_page', return_value=(html, 'https://example.com/jobs/1')), patch('app.services.job_quality.fetch_rendered_page', side_effect=ValueError('still blocked')), patch('app.services.job_quality.extract_job', return_value=extraction):
            job = enrich_job(self.job())
        self.assertEqual(job.research['state'], 'expired')
