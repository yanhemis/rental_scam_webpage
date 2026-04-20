from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["demo"])

BASE_DIR = Path(__file__).resolve().parents[1]
DEMO_HTML_PATH = BASE_DIR / "static" / "admin-monitor.html"


@router.get("/demo/admin-monitor")
async def admin_monitor_page():
    return FileResponse(DEMO_HTML_PATH)
