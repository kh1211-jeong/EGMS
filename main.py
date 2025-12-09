# main.py
from fastapi import FastAPI, Request, Body, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from topology_provider import get_topology
from equipment_provider import list_equipments, update_equipments
from data_provider import list_data, bulk_update

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

@app.get("/ui/data")
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

@app.get("/ui/settings")
def ui_data_panel(request: Request):
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "app_title": "EGMS · 데이터 현황",
            "header_badge": "Settings",
            "current_page": "settings",
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


@app.get("/api/equipment-data")
def api_equipment_data():

    eqps = list_equipments()            # 설비 기본 정보 list
    data = list_data()                  # 데이터 dict (eqp_no -> 측정값)

    rows = []

    for eqp in eqps:
        eqp_no = eqp["eqp_no"]
        d = data.get(eqp_no, {})

        rows.append({
            "eqp_no": eqp_no,
            "eqp_name": eqp["eqp_name"],
            "status": d.get("status", ""),
            "voltage": d.get("voltage", ""),
            "current": d.get("current", ""),
            "temperature": d.get("temperature", ""),
            "load_rate": d.get("load_percentage", ""),
            "warning_level": d.get("warning_level", ""),
            "updated_at": d.get("last_update", "")
        })

    return {"items": rows}

@app.post("/api/equipment-data")
def api_equipment_data_update(payload: dict = Body(...)):
    """
    data.html에서 편집한 테이블 데이터를 저장
    요청 형식: { "items": [ {eqp_no, eqp_name, status, voltage, ...}, ... ] }
    """
    items = payload.get("items", [])
    if not isinstance(items, list):
        items = []

    data_dict = {}

    for row in items:
        eqp_no = row.get("eqp_no")
        if not eqp_no:
            continue

        data_dict[eqp_no] = {
            # data_provider 내부 저장 포맷에 맞게 매핑
            "status": row.get("status", ""),
            "temperature": row.get("temperature", ""),
            "load_percentage": row.get("load_rate", ""),   # 이름 매핑 주의
            "last_update": row.get("updated_at", ""),

            # 추가 필드(옵션)
            "voltage": row.get("voltage", ""),
            "current": row.get("current", ""),
            "warning_level": row.get("warning_level", ""),
        }

    bulk_update(data_dict)
    return {"ok": True, "count": len(data_dict)}

@app.get("/api/equipment-data/export")
def api_equipment_data_export():
    """
    data.html용 계측 데이터를 CSV로 내보내기
    헤더: EQP_NO,EQP_NAME,STATUS,VOLTAGE,CURRENT,TEMPERATURE,LOAD_RATE,WARNING_LEVEL,UPDATED_AT
    """
    eqps = list_equipments()
    data = list_data()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "EQP_NO", "EQP_NAME", "STATUS",
        "VOLTAGE", "CURRENT", "TEMPERATURE",
        "LOAD_RATE", "WARNING_LEVEL", "UPDATED_AT"
    ])

    for eqp in eqps:
        eqp_no = eqp["eqp_no"]
        d = data.get(eqp_no, {})

        writer.writerow([
            eqp_no,
            eqp["eqp_name"],
            d.get("status", ""),
            d.get("voltage", ""),
            d.get("current", ""),
            d.get("temperature", ""),
            d.get("load_percentage", ""),  # 내부는 load_percentage
            d.get("warning_level", ""),
            d.get("last_update", ""),
        ])

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename=\"equipment_data.csv\"'},
    )

@app.post("/api/equipment-data/import")
async def api_equipment_data_import(file: UploadFile = File(...)):
    """
    data.html에서 업로드한 CSV를 읽어서 equipment_data로 반영
    컬럼: EQP_NO,EQP_NAME,STATUS,VOLTAGE,CURRENT,TEMPERATURE,LOAD_RATE,WARNING_LEVEL,UPDATED_AT
    """
    raw = await file.read()
    text = raw.decode("utf-8-sig")

    reader = csv.DictReader(io.StringIO(text))
    data_dict = {}

    for row in reader:
        eqp_no = (row.get("EQP_NO") or "").strip()
        if not eqp_no:
            continue

        data_dict[eqp_no] = {
            "status": (row.get("STATUS") or "").strip(),
            "temperature": (row.get("TEMPERATURE") or "").strip(),
            "load_percentage": (row.get("LOAD_RATE") or "").strip(),
            "last_update": (row.get("UPDATED_AT") or "").strip(),
            "voltage": (row.get("VOLTAGE") or "").strip(),
            "current": (row.get("CURRENT") or "").strip(),
            "warning_level": (row.get("WARNING_LEVEL") or "").strip(),
        }

    bulk_update(data_dict)
    return {"ok": True, "count": len(data_dict)}
