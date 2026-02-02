from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles


# -----------------------------
# App / Templates / Static
# -----------------------------

app = FastAPI(title="EGMS")

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# If you have /static (css/js/img) folder, mount it. Safe even if folder doesn't exist.
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# -----------------------------
# UI Routes
# -----------------------------

@app.get("/", response_class=HTMLResponse)
@app.get("/ui/home", response_class=HTMLResponse)
def ui_home(request: Request):
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "app_title": "EGMS",
            "header_badge": "HOME",
            "current_page": "home",
        },
    )


@app.get("/ui/topology", response_class=HTMLResponse)
def ui_topology(request: Request):
    return templates.TemplateResponse(
        "topology.html",
        {
            "request": request,
            "app_title": "EGMS · 연결 정보",
            "header_badge": "TOPOLOGY",
            "current_page": "topology",
        },
    )


@app.get("/ui/equipment", response_class=HTMLResponse)
def ui_equipment(request: Request):
    return templates.TemplateResponse(
        "equipment.html",
        {
            "request": request,
            "app_title": "EGMS · 기준정보",
            "header_badge": "EQUIPMENT",
            "current_page": "equipment",
        },
    )


@app.get("/ui/data", response_class=HTMLResponse)
def ui_data(request: Request):
    return templates.TemplateResponse(
        "data.html",
        {
            "request": request,
            "app_title": "EGMS · 데이터 현황",
            "header_badge": "DATA",
            "current_page": "data",
        },
    )


@app.get("/ui/settings", response_class=HTMLResponse)
def ui_settings(request: Request):
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "app_title": "EGMS · 설정",
            "header_badge": "SETTINGS",
            "current_page": "settings",
        },
    )


# -----------------------------
# Minimal APIs (TEMP)
# - Purpose: Make UI grids render (no 404/500) while providers/DB are being wired.
# - Later: replace these with real providers/DB implementations.
# -----------------------------

@app.get("/api/equipments")
def api_get_equipments():
    """
    TEMP stub to prevent UI from being empty.
    equipment.html expects: { items: [ {eqp_no, eqp_name, type, building, location, parent_eqp_no}, ... ] }
    Enable with EGMS_STUB_API=1 (default ON).
    """
    enabled = os.getenv("EGMS_STUB_API", "1").strip() == "1"
    if not enabled:
        return JSONResponse(status_code=404, content={"detail": "stub api disabled"})

    items = [
        {
            "eqp_no": "00000001",
            "eqp_name": "VCB_2F11A",
            "type": "VCB",
            "building": "B1",
            "location": "E/R",
            "parent_eqp_no": "00000000",
        },
        {
            "eqp_no": "00000002",
            "eqp_name": "BTR_2F11",
            "type": "BTR",
            "building": "B1",
            "location": "E/R",
            "parent_eqp_no": "00000001",
        },
        {
            "eqp_no": "00000003",
            "eqp_name": "LTR_2F11",
            "type": "LTR",
            "building": "B1",
            "location": "E/R",
            "parent_eqp_no": "00000002",
        },
    ]
    return {"items": items}


@app.get("/api/equipment-data")
def api_equipment_data():
    """
    TEMP stub to prevent UI from being empty.
    data.html expects: { items: [ {eqp_no, eqp_name, status, voltage, current, temperature, load_rate, warning_level, updated_at}, ... ] }
    Enable with EGMS_STUB_API=1 (default ON).
    """
    enabled = os.getenv("EGMS_STUB_API", "1").strip() == "1"
    if not enabled:
        return JSONResponse(status_code=404, content={"detail": "stub api disabled"})

    rows = [
        {
            "eqp_no": "00000001",
            "eqp_name": "VCB_2F11A",
            "status": "ON",
            "voltage": "22890",
            "current": "120",
            "temperature": "36.2",
            "load_rate": "48.1",
            "warning_level": "NORMAL",
            "updated_at": "2026-02-02 21:00:00",
        },
        {
            "eqp_no": "00000002",
            "eqp_name": "BTR_2F11",
            "status": "ON",
            "voltage": "22890",
            "current": "115",
            "temperature": "41.7",
            "load_rate": "52.0",
            "warning_level": "NORMAL",
            "updated_at": "2026-02-02 21:00:00",
        },
        {
            "eqp_no": "00000003",
            "eqp_name": "LTR_2F11",
            "status": "ON",
            "voltage": "380",
            "current": "380",
            "temperature": "38.9",
            "load_rate": "61.3",
            "warning_level": "WATCH",
            "updated_at": "2026-02-02 21:00:00",
        },
    ]
    return {"items": rows}


# -----------------------------
# Health check
# -----------------------------

@app.get("/api/health")
def api_health():
    return {"ok": True, "app": "EGMS"}
