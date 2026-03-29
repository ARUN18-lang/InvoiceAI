import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.mongo import MongoManager, ensure_indexes
from app.db.neo4j_client import Neo4jManager, ensure_graph_constraints
from app.plugins.analytics.router import router as analytics_router
from app.plugins.chat.managers.chat_manager import ChatManager
from app.plugins.chat.router import router as chat_router
from app.plugins.invoices.managers.invoice_manager import InvoiceManager
from app.plugins.invoices.router import router as invoices_router
from app.plugins.notifications.router import router as notifications_router
from app.plugins.workspaces.router import router as workspaces_router
from app.services.due_alert_service import DueAlertService
from app.services.graph_sync_service import GraphSyncService
from app.services.openai_client import OpenAIClientFactory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    mongo = MongoManager(settings)
    await mongo.connect()
    await ensure_indexes(mongo.database())

    neo4j = Neo4jManager(settings)
    await neo4j.connect()
    if neo4j.enabled:
        try:
            async with neo4j.session() as session:
                await ensure_graph_constraints(session)
        except Exception:
            logger.exception("Neo4j constraint bootstrap failed (check Neo4j version / permissions)")

    openai_factory = OpenAIClientFactory(settings)
    graph = GraphSyncService(neo4j)
    db = mongo.database()
    app.state.invoice_manager = InvoiceManager(
        db=db,
        settings=settings,
        openai_factory=openai_factory,
        neo4j_graph=graph,
    )
    app.state.chat_manager = ChatManager(
        db=db,
        settings=settings,
        openai_factory=openai_factory,
        graph=graph,
    )
    app.state.settings = settings
    app.state.mongo = mongo
    app.state.neo4j = neo4j
    app.state.scheduler = None

    if settings.scheduler_enabled:
        scheduler = AsyncIOScheduler()

        async def due_tick() -> None:
            try:
                await DueAlertService(mongo.database(), settings).run_due_checks()
            except Exception:
                logger.exception("Due alert scheduler tick failed")

        scheduler.add_job(due_tick, CronTrigger(hour=8, minute=0, timezone="UTC"))
        scheduler.start()
        app.state.scheduler = scheduler
        await due_tick()

    yield

    sch = getattr(app.state, "scheduler", None)
    if sch is not None:
        sch.shutdown(wait=False)

    await neo4j.disconnect()
    await mongo.disconnect()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Smart Invoice Digitizer API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(workspaces_router, prefix=settings.api_prefix)
    app.include_router(invoices_router, prefix=settings.api_prefix)
    app.include_router(chat_router, prefix=settings.api_prefix)
    app.include_router(analytics_router, prefix=settings.api_prefix)
    app.include_router(notifications_router, prefix=settings.api_prefix)

    @app.get("/health")
    async def health():
        return {"status": "ok", "api_prefix": settings.api_prefix}

    return app


app = create_app()
