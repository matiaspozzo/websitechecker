import logging
from contextlib import asynccontextmanager
from pathlib import Path

import aiohttp
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import scheduler
from app.api.router import api_router
from app.checks import runner
from app.checks.heartbeat import check_startup_downtime
from app.checks.registry import load_all_checkers
from app.database import SessionLocal
from app.logging_conf import configure_logging
from app.notifiers.telegram import start_bot, stop_bot

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    load_all_checkers()

    session = aiohttp.ClientSession(
        headers={"User-Agent": runner.USER_AGENT}, timeout=aiohttp.ClientTimeout(total=10)
    )
    runner.set_http_session(session)

    db = SessionLocal()
    try:
        scheduler.sync_all_sites(db)
    finally:
        db.close()

    scheduler.start()

    try:
        await check_startup_downtime()
    except Exception:
        logger.exception("Startup downtime check failed")

    try:
        await start_bot()
    except Exception:
        logger.exception("Failed to start Telegram bot polling")

    yield

    await stop_bot()
    scheduler.shutdown()
    await session.close()


def create_app() -> FastAPI:
    app = FastAPI(title="SiteWatch", lifespan=lifespan)
    app.include_router(api_router)

    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    if STATIC_DIR.exists():

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(full_path: str) -> FileResponse:
            candidate = STATIC_DIR / full_path
            if candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()
