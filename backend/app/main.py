from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import get_settings
from app.services.crawl_service import run_all_crawls, process_search_queue
from app.services.discovery_backlog import process_backlogs
from app.services.opportunity_service import run_opportunity_notifications
from app.services.followup_service import run_all_followups

settings = get_settings()
scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(
        run_all_crawls,
        "interval",
        hours=settings.crawl_interval_hours,
        id="crawl_all_users",
        replace_existing=True,
    )
    scheduler.add_job(
        run_all_followups,
        "interval",
        hours=settings.followup_interval_hours,
        id="followups_all_users",
        replace_existing=True,
    )
    scheduler.add_job(process_search_queue, 'interval', seconds=15, id='search_queue', replace_existing=True, max_instances=1, coalesce=True)
    scheduler.add_job(process_backlogs, 'interval', minutes=1, id='discovery_backlog', replace_existing=True, max_instances=1, coalesce=True)
    scheduler.add_job(run_opportunity_notifications, 'interval', minutes=15, id='opportunity_notifications', replace_existing=True, max_instances=1, coalesce=True)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)
    from app.services import crawl_service, discovery_backlog
    for pool in (crawl_service._search_pool, discovery_backlog._backlog_pool):
        if pool is not None:
            pool.shutdown()


app = FastAPI(title="ApplyPilot API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
