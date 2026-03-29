from fastapi import APIRouter, Query, Request

from app.deps import WorkspaceOidDep
from app.schemas.analytics import AnalyticsDashboard
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard", response_model=AnalyticsDashboard)
async def analytics_dashboard(
    request: Request,
    workspace_id: WorkspaceOidDep,
    top_vendors: int = Query(default=8, ge=1, le=50),
) -> AnalyticsDashboard:
    db = request.app.state.mongo.database()
    svc = AnalyticsService(db)
    return await svc.dashboard(workspace_id=workspace_id, top_vendors=top_vendors)
