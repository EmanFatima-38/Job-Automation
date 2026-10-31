import unittest
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest.mock import patch
from app.ai.schemas.job_extraction_schema import JobExtraction
from app.services.job_quality import eligibility, enrich_job
from app.services.recommendation_policy import recommendation, remote_restriction, mandatory_evidence, POLICY_VERSION
from app.services.vacancy_evidence import page_kind, clean_page
from app.services.job_sources.vacancy_search import search_vacancies, directory_links
from app.services.discovery_backlog import match_context


class TrustPolicyTests(unittest.TestCase):
    def setUp(self):
        self.user=SimpleNamespace(preferences={'cities':['Lahore'],'remote_country':'Pakistan'},portfolio_data={})
        self.resume=SimpleNamespace(parse_status='parsed',structured_profile={'summary':'Python intern','skills':['Python'],'experience':[],'education':[]})
        self.job=SimpleNamespace(salary_range=None,title='Python Intern',company='Acme',location='Lahore',employment_type='internship',work_mode='onsite',requirements=['Python'],raw_input_text='Python internship',source_url='https://example.com/job/1',canonical_url='https://example.com/job/1',extraction_status='extracted',description_text='Python internship',research={'state':'active','is_job_posting':True,'verification_status':'page_checked','evidence_version':POLICY_VERSION,'posted_at':datetime.now(timezone.utc).isoformat(),'last_verified_at':datetime.now(timezone.utc).isoformat(),'application_link_status':'reachable'})
        self.match=SimpleNamespace(match_score=95,details={},context_hash=match_context(self.user,self.resume,self.job))

    def test_complete_evidence_can_recommend(self):
        self.assertEqual(recommendation(self.job,self.user,self.resume,self.match)['recommendation_status'],'recommended')

    def test_unverified_high_score_is_not_recommendation(self):
        self.job.research['verification_status']='unverified'
        self.assertEqual(recommendation(self.job,self.user,self.resume,self.match)['recommendation_status'],'needs_review')

    def test_future_and_old_dates_never_recommend(self):
        for days in (5,-50):
            self.job.research['posted_at']=(datetime.now(timezone.utc)+timedelta(days=days)).isoformat()
            self.assertNotEqual(recommendation(self.job,self.user,self.resume,self.match)['recommendation_status'],'recommended')

    def test_model_date_requires_source_evidence(self):
        from app.services.job_quality import date_has_evidence
        self.assertFalse(date_has_evidence('2026-10-23','Copyright 2026. Apply now.'))
        self.assertTrue(date_has_evidence('2026-10-23','Posted October 23, 2026'))
        self.assertTrue(date_has_evidence('2026-10-03','Posted October 3, 2026'))

    def test_missing_and_stale_match_never_recommend(self):
        self.assertNotEqual(recommendation(self.job,self.user,self.resume,None)['recommendation_status'],'recommended')
        self.match.context_hash='stale'
        self.assertNotEqual(recommendation(self.job,self.user,self.resume,self.match)['recommendation_status'],'recommended')

    def test_unreachable_application_never_recommends(self):
        self.job.research['application_link_status']='unverified'
        self.assertNotEqual(recommendation(self.job,self.user,self.resume,self.match)['recommendation_status'],'recommended')

    def test_five_years_is_explicit_concern(self):
        self.job.requirements=['Minimum 5 years of professional experience required']
        _,c=eligibility(self.job,{})
        self.assertTrue(any('5 years' in v for v in c))

    def test_preferred_experience_does_not_become_mandatory(self):
        self.job.requirements=['5 years experience preferred']
        self.assertEqual(mandatory_evidence(self.job)[1],[])

    def test_spelled_out_years_is_still_an_explicit_concern(self):
        self.job.requirements=['At least five years of experience required']
        self.assertTrue(any('5 years' in v for v in mandatory_evidence(self.job)[1]))

    def test_optional_experience_phrasings_do_not_become_mandatory(self):
        for text in ('5 years experience is a plus','5 years experience is a bonus','Ideally 5+ years of experience'):
            self.job.requirements=[text]
            self.assertEqual(mandatory_evidence(self.job)[1],[],text)

    def test_zero_years_minimum_is_not_a_concern(self):
        self.job.requirements=['Ideal for fresh graduates or candidates with 0-2 years of experience']
        self.assertEqual(mandatory_evidence(self.job)[1],[])

    def test_sufficient_cv_experience_resolves_the_years_concern(self):
        self.job.requirements=['Minimum 5 years of professional experience required']
        senior={'education':[],'experience':[{'title':'Senior Eng','company':'X','start_date':'2015','end_date':'2025'}]}
        junior={'education':[],'experience':[{'title':'Intern','company':'Y','start_date':'2024','end_date':'present'}]}
        self.assertEqual(mandatory_evidence(self.job,senior)[1],[])
        self.assertTrue(mandatory_evidence(self.job,junior)[1])

    def test_ca_is_not_treated_as_canada(self):
        # 'CA' is far more often the US state California in job postings; silently
        # treating it as Canada would wrongly tell a Canadian candidate they're eligible.
        self.assertIsNotNone(remote_restriction('CA residents only','Canada')[1])
        self.assertEqual(remote_restriction('Canada only','Canada'),(None,None))

    def test_enrollment_and_work_authorization_not_inferred(self):
        self.job.requirements=['Must be currently enrolled in computer science','US work authorization required']
        reasons=mandatory_evidence(self.job,self.resume.structured_profile)[1]
        self.assertEqual(len(reasons),2)

    def test_explicit_enrollment_evidence_resolves_enrollment_concern(self):
        self.job.requirements=['Currently enrolled in computer science']
        profile={'education':[{'degree':'Currently enrolled in BS Computer Science'}]}
        self.assertEqual(mandatory_evidence(self.job,profile)[1],[])

    def test_model_omitting_concerns_cannot_certify_enrollment(self):
        from app.ai.schemas.match_score_schema import MatchScore
        from app.ai.schemas.resume_profile_schema import ResumeProfile
        from app.ai.score_match import score_match
        profile=ResumeProfile(summary='Python intern',skills=['Python'],experience=[],education=[])
        job=JobExtraction(title='AI Intern',requirements=['Currently enrolled in computer science'],description_summary='Must be a current student.')
        inflated=MatchScore(score=95,matched_skills=['Currently enrolled (inferred)'],missing_skills=[],rationale='Strong fit')
        with patch('app.ai.score_match.parse_structured',return_value=inflated):
            result=score_match(profile,job)
        self.assertLessEqual(result.score,69)
        self.assertTrue(result.eligibility_concerns)
        self.assertEqual(result.matched_skills,[])

    def test_country_codes_and_explicit_exclusions(self):
        self.assertIsNotNone(remote_restriction('US','Pakistan')[0])
        self.assertIsNotNone(remote_restriction('{"name":"United States"}','Pakistan')[0])
        self.assertIsNotNone(remote_restriction('Worldwide except Pakistan','Pakistan')[0])
        self.assertEqual(remote_restriction('PK','Pakistan'),(None,None))
        self.assertEqual(remote_restriction('Worldwide','Pakistan'),(None,None))
        self.assertIsNotNone(remote_restriction('EMEA','Pakistan')[1])

    def test_failed_retrieval_is_unknown_not_definitely_nonvacancy(self):
        result=JobExtraction(title='Python Intern',company='Acme',requirements=[],description_summary='Snippet',is_job_posting=False)
        with patch('app.services.job_quality.fetch_public_page',side_effect=ValueError('blocked')),patch('app.services.job_quality.extract_job',return_value=result):
            enrich_job(self.job)
        self.assertIsNone(self.job.research['is_job_posting'])
        self.assertNotEqual(self.job.research['state'],'active')
        self.assertNotIn('Page is not an individual vacancy',eligibility(self.job,{})[0])

    def test_specific_vacancy_conflict_is_reviewable_not_rejected(self):
        html='<h1>Python Intern at Acme</h1><p>About the role: Acme is hiring a paid intern.</p><h2>What you will do</h2><p>Build Python prototypes with our team.</p><h2>Requirements</h2><p>Basic Python knowledge.</p>'
        result=JobExtraction(title='Python Intern',company='Acme',requirements=['Python'],description_summary='Intern',is_job_posting=False)
        with patch('app.services.job_quality.fetch_public_page',return_value=(html,self.job.source_url)),patch('app.services.job_quality.extract_job',return_value=result):
            enrich_job(self.job)
        self.assertIsNone(self.job.research['is_job_posting'])
        self.assertIn('classification_concern',self.job.research)
        self.assertNotIn('Page is not an individual vacancy',eligibility(self.job,{})[0])

    def test_reachable_link_establishes_active_even_when_model_self_report_is_null(self):
        # Real-world pattern found live: the model's own application_available field is
        # frequently null on ordinary pages even when a reachable apply link clearly
        # exists - the deterministic evidence must be enough on its own.
        html='<h1>Python Intern</h1><p>Acme requirements Python. Apply for this role. This vacancy has paid training and mentoring opportunities.</p><a href="/apply/123">Apply now</a>'
        target='<h1>Application for Python Intern</h1><p>Please enter your details to apply for the Acme internship position. We review all submitted applications.</p>'
        result=JobExtraction(title='Python Intern',company='Acme',requirements=['Python'],description_summary='Intern',is_job_posting=True,application_available=None)
        with patch('app.services.job_quality.fetch_public_page',side_effect=[(html,self.job.source_url),(target,'https://example.com/apply/123')]),patch('app.services.job_quality.extract_job',return_value=result):
            enrich_job(self.job)
        self.assertEqual(self.job.research['application_link_status'],'reachable')
        self.assertEqual(self.job.research['state'],'active')

    def test_reachable_apply_anchor_and_no_submission(self):
        html='<h1>Python Intern</h1><p>Acme requirements Python. Apply for this role. This vacancy has paid training and mentoring opportunities.</p><a href="/apply/123">Apply now</a>'
        target='<h1>Application for Python Intern</h1><p>Please enter your details to apply for the Acme internship position. We review all submitted applications.</p>'
        result=JobExtraction(title='Python Intern',company='Acme',requirements=['Python'],description_summary='Intern',is_job_posting=True,application_available=True)
        with patch('app.services.job_quality.fetch_public_page',side_effect=[(html,self.job.source_url),(target,'https://example.com/apply/123')]) as fetch,patch('app.services.job_quality.extract_job',return_value=result):
            enrich_job(self.job)
        self.assertEqual(fetch.call_count,2)
        self.assertEqual(self.job.research['application_link_status'],'reachable')


class VacancyDiscoveryTests(unittest.TestCase):
    def test_directories_and_articles_are_not_vacancy_candidates(self):
        for url in ['https://pk.indeed.com/q-python-jobs.html','https://www.glassdoor.com/Job/pakistan-SRCH_IL.htm','https://careers.microsoft.com/students','https://www.rozee.pk/job/jsearch/q/AI%20Engineer/ftFacets']:
            self.assertEqual(page_kind(url),'directory')
        self.assertEqual(page_kind('https://example.com/blog/ai-jobs'),'irrelevant')
        self.assertEqual(page_kind('https://www.threads.com/@someone/post/abc'),'irrelevant')
        self.assertEqual(page_kind('https://pk.linkedin.com/jobs/view/python-intern-123'),'candidate')

    def test_training_program_is_not_a_vacancy(self):
        from app.services.vacancy_evidence import is_training_program
        course_text = 'Cloud + MLOps Track\nCohort 12 Starts October 2026\nModule 01 - The Launchpad\nModule 02 - Core Skills\nApply for cohort 12'
        self.assertTrue(is_training_program(course_text))
        job_text = 'We are hiring a Software Engineer. Responsibilities: build features. Requirements: 2 years Python.'
        self.assertFalse(is_training_program(job_text))

    def test_training_program_page_is_classified_as_not_a_vacancy(self):
        html = ('<h1>Cloud + MLOps Track</h1><p>Run software and AI models in production. Every company that '
                'ships software needs someone to run it. Across three modules and 8 months you go from switching '
                'on a computer to running a monitored machine learning system on AWS.</p>'
                '<p>Module 01 - The Launchpad. Module 02 - Core Skills. Cohort 12 Starts October 2026.</p>'
                '<a href="#apply">Apply for cohort 12</a>')
        job = SimpleNamespace(title='Cloud + MLOps Track', company='Big Binary Trainings', location=None,
                               raw_input_text='', source_url='https://bbt.edu.pk/track-cloud-mlops', canonical_url=None,
                               research={}, requirements=[])
        result=JobExtraction(title='Cloud + MLOps Track',requirements=[],description_summary='Course',is_job_posting=None)
        with patch('app.services.job_quality.fetch_public_page',return_value=(html,'https://bbt.edu.pk/track-cloud-mlops')),patch('app.services.job_quality.extract_job',return_value=result):
            enrich_job(job)
        self.assertIs(job.research['is_job_posting'],False)

    def test_directory_expansion_keeps_individual_job_links(self):
        html='<a href="/jobs">All jobs</a><a href="/jobs/python-intern/123">Python Intern</a><a href="javascript:bad()">Apply now</a><a href="/blog/course">Python course</a>'
        self.assertEqual([r['url'] for r in directory_links(html,'https://example.com/careers')],['https://example.com/jobs/python-intern/123'])

    def test_native_date_filter_and_social_exclusion(self):
        rows=[{'url':'https://facebook.com/groups/jobs','title':'Job'}, {'url':'https://example.com/job/123','title':'Intern'}]
        with patch('app.services.job_sources.vacancy_search.tavily_search',return_value=rows) as search:
            hits=search_vacancies('Python internship after:2026-09-23',limit=1)
        self.assertEqual(len(hits),1)
        kwargs=search.call_args.kwargs
        self.assertEqual(kwargs['start_date'],'2026-09-23')
        self.assertNotIn('after:',search.call_args.args[0])
        self.assertIn('facebook.com',kwargs['exclude_domains'])

    def test_form_boilerplate_removed_but_role_preserved(self):
        cleaned=clean_page('<h1>AI Intern</h1><form>Premium Role payment login</form><p>Acme is hiring</p>')
        self.assertNotIn('Premium',cleaned)
        self.assertIn('Acme',cleaned)

    def test_how_to_apply_guide_is_not_application_destination(self):
        from app.services.vacancy_evidence import application_link
        self.assertIsNone(application_link('<a href="/how-to-apply">How to apply</a>','https://example.com/job/1'))

    def test_inline_cv_form_stays_on_vacancy_page(self):
        from app.services.vacancy_evidence import application_link
        self.assertEqual(application_link('<form method="post">Apply: upload CV<input type="file"/></form>','https://example.com/job/1'),'https://example.com/job/1')
