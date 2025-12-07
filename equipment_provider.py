# equipment_provider.py
import json
from pathlib import Path

DB_PATH = Path(__file__).with_name("equipments.json")


def _load_from_file():
    """equipments.json이 존재하면 읽고, 없으면 빈 리스트 반환"""
    if DB_PATH.exists():
        try:
            with DB_PATH.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


# 메모리 캐시
_equipments = _load_from_file()


def list_equipments():
    """현재 설비 목록 반환"""
    return _equipments


def update_equipments(items):
    """설비 목록 갱신 + 파일 저장"""
    global _equipments
    _equipments = items

    try:
        with DB_PATH.open("w", encoding="utf-8") as f:
            json.dump(_equipments, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
