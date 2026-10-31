from fastapi import APIRouter
from app.api.v1 import discovery

from app.api.v1 import (
    applications,
    auth,
    crawl,
    dashboard,
    documents,
    email_account,
    jobs,
    matches,
    profile,
    resumes,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(resumes.router)
api_router.include_router(jobs.router)
api_router.include_router(matches.router)
api_router.include_router(documents.router)
api_router.include_router(applications.router)
api_router.include_router(dashboard.router)
api_router.include_router(crawl.router)
api_router.include_router(profile.router)
api_router.include_router(email_account.router)

api_router.include_router(discovery.router)
