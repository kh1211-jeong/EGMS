# data_provider.py
import json
from pathlib import Path
import random
from datetime import datetime

from equipment_provider import list_equipments  # 기존 파일 수정 없음, 여기서만 가져옴

DB_PATH = Path(__file__).with_name("equipments_data.json")

def _load_from_file():
    if DB_PATH.exists():
        try:
            with DB_PATH.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

# 메모리 캐시
_data = _load_from_file()
_initialized = False  # 자동 초기화가 이미 수행됐는지 여부


def _save_to_file():
    try:
        with DB_PATH.open("w", encoding="utf-8") as f:
            json.dump(_data, f, ensure_ascii=False, indent=2)
    except Exception:
        # 파일 쓰기 오류는 조용히 무시 (파일럿 단계)
        pass


def generate_fake_for(equipments):
    """
    설비 목록을 받아 더미 계측 데이터를 생성.
    """
    fake_data = {}

    for eqp in equipments:
        eqp_no = eqp.get("eqp_no")
        if not eqp_no:
            continue

        fake_data[eqp_no] = {
            "status": random.choice(["NORMAL", "WARN", "FAIL"]),

            "voltage": round(random.uniform(210, 245), 1),   # 예시: 저압 AC 기준
            "current": round(random.uniform(10, 300), 1),    # 예시: 임의 부하 전류
            "warning_level": random.choice(["NONE", "LOW", "MID", "HIGH"]),

            "temperature": round(random.uniform(25, 95), 1),
            "load_percentage": random.randint(0, 100),
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    return fake_data


def _ensure_initialized():
    """
    1) 이미 메모리에 데이터가 있으면 그대로 사용
    2) 파일에도 없고 메모리도 비어 있으면
       -> equipment_provider에서 설비 목록을 받아 더미 데이터 생성
       -> 파일에 저장
    """
    global _initialized, _data

    if _initialized:
        return

    _initialized = True

    # 이미 파일에서 로드된 데이터가 있으면 그대로 사용
    if _data:
        return

    equipments = list_equipments()
    if not equipments:
        # 설비가 없으면 할 수 있는 게 없으니 그냥 종료
        return

    _data = generate_fake_for(equipments)
    _save_to_file()


def list_data():
    """모든 설비의 상태/계측 데이터 반환 (최초 호출 시 자동 생성)"""
    _ensure_initialized()
    return _data


def get_data(eqp_no: str):
    """특정 설비의 계측 데이터 반환 (최초 호출 시 자동 생성)"""
    _ensure_initialized()
    return _data.get(eqp_no)


def update_data(eqp_no: str, values: dict):
    """특정 설비의 계측 데이터를 직접 갱신"""
    global _data
    _ensure_initialized()
    _data[eqp_no] = values
    _save_to_file()


def bulk_update(items: dict):
    """여러 설비 데이터를 한 번에 갱신"""
    global _data
    _data = items
    _save_to_file()
