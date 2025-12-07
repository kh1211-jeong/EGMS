# main.py
from fastapi import FastAPI, Request, Body, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from topology_provider import get_topology
from equipment_provider import list_equipments, update_equipments

import io
import csv

app = FastAPI(title="EGMS")

templates = Jinja2Templates(directory="templates")


# -----------------------------
# UI 라우트
# -----------------------------


@app.get("/", response_class=HTMLResponse)
@app.get("/ui/home", response_class=HTMLResponse)
def ui_home(request: Request):
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "app_title": "EGMS",
        },
    )


@app.get("/ui/topology", response_class=HTMLResponse)
def ui_topology(request: Request):
    return templates.TemplateResponse(
        "topology.html",
        {
            "request": request,
            "app_title": "EGMS",
        },
    )


@app.get("/ui/equipment", response_class=HTMLResponse)
def ui_equipment(request: Request):
    return templates.TemplateResponse(
        "equipment.html",
        {
            "request": request,
            "app_title": "EGMS",
        },
    )


# -----------------------------
# Topology API
# -----------------------------


@app.get("/api/topology")
def api_topology():
    data = get_topology()
    return data


# -----------------------------
# Equipment API (JSON 기반 CRUD + CSV Import/Export)
# -----------------------------


@app.get("/api/equipments")
def api_get_equipments():
    """
    설비 리스트 조회 (JSON)
    """
    return {"items": list_equipments()}


@app.post("/api/equipments")
def api_update_equipments(payload: dict = Body(...)):
    """
    설비 리스트 갱신 (파일럿용)
    요청 바디: { "items": [ {eqp_no, eqp_name, ...}, ... ] }
    """
    items = payload.get("items", [])
    if not isinstance(items, list):
        items = []

    update_equipments(items)
    return {"ok": True, "count": len(items)}


@app.get("/api/equipments/export")
def api_export_equipments():
    """
    설비 리스트를 CSV(엑셀 호환)로 내보내기
    """
    items = list_equipments()

    output = io.StringIO()
    writer = csv.writer(output)

    # 헤더
    writer.writerow(
        ["EQP_NO", "EQP_NAME", "TYPE", "BUILDING", "LOCATION", "PARENT_EQP_NO"]
    )

    # 데이터
    for item in items:
        writer.writerow(
            [
                item.get("eqp_no", ""),
                item.get("eqp_name", ""),
                item.get("type", ""),
                item.get("building", ""),
                item.get("location", ""),
                item.get("parent_eqp_no", ""),
            ]
        )

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="equipments.csv"'},
    )


@app.post("/api/equipments/import")
async def api_import_equipments(file: UploadFile = File(...)):
    """
    CSV(엑셀) 파일로부터 설비 리스트 가져오기.
    컬럼: EQP_NO, EQP_NAME, TYPE, BUILDING, LOCATION, PARENT_EQP_NO
    """
    raw = await file.read()
    text = raw.decode("utf-8-sig")  # BOM 있어도 안전하게 처리

    reader = csv.DictReader(io.StringIO(text))
    items = []

    for row in reader:
        items.append(
            {
                "eqp_no": row.get("EQP_NO", "").strip(),
                "eqp_name": row.get("EQP_NAME", "").strip(),
                "type": row.get("TYPE", "").strip(),
                "building": row.get("BUILDING", "").strip(),
                "location": row.get("LOCATION", "").strip(),
                "parent_eqp_no": row.get("PARENT_EQP_NO", "").strip(),
            }
        )

    update_equipments(items)
    return {"ok": True, "count": len(items)}
