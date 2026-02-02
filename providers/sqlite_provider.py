# providers/sqlite_provider.py
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import List, Optional, Sequence

from .base import BaseProvider, TagRow, TrendRow


def _now_minute_str() -> str:
    # 'YYYY-MM-DD HH:MM' (분까지만)
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _now_second_str() -> str:
    # 'YYYY-MM-DD HH:MM:SS' (created/updated용)
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _make_sparse_series(sensor_type: str, eqp_tag_code: str) -> str:
    """
    (KR) TRND_VALUE: '0:값;12:값;45:값' 형식의 성긴 문자열 생성
         - 전압 레벨: GCB=154kV, BTR/VCB=6.6kV, LTR/ACB/TIE=220V
    (EN) Generate sparse 'sec:value;...' series string with realistic ranges.
    """
    import random

    def pick_points() -> list[int]:
        # 꼭 0~60 전부 필요 없으므로 2~5개만 선택
        base = [0, 12, 24, 45, 57]
        k = random.choice([2, 2, 3, 3, 4, 5])
        pts = sorted(random.sample(base, k=k))
        if pts[0] != 0:
            pts = [0] + pts
        return pts

    pts = pick_points()

    # 전압 레벨 결정
    is_gcb = eqp_tag_code.startswith("GCB_")
    is_btr = eqp_tag_code.startswith("BTR_")
    is_vcb = eqp_tag_code.startswith("VCB_")
    is_ltr = eqp_tag_code.startswith("LTR_")
    is_acb = eqp_tag_code.startswith("ACB_")
    is_tie = eqp_tag_code.startswith("TIE_")

    # 레벨별 기본값/범위
    if sensor_type == "VOLTAGE":
        if is_gcb:
            lo, hi = 153000, 155500  # 154kV 근처
            values = [random.randint(lo, hi) for _ in pts]
        elif is_btr or is_vcb:
            lo, hi = 6400, 6900      # 6.6kV 근처
            values = [random.randint(lo, hi) for _ in pts]
        else:
            # LTR/ACB/TIE 포함: 220V 근처
            values = [round(random.uniform(210.0, 235.0), 1) for _ in pts]

    elif sensor_type == "CURRENT":
        if is_gcb:
            lo, hi = 10, 300
        elif is_btr or is_vcb:
            lo, hi = 50, 1200
        else:
            lo, hi = 50, 3000
        values = [random.randint(lo, hi) for _ in pts]

    elif sensor_type == "POWER":
        # kW 스케일 숫자(해석은 UI에서)
        if is_gcb:
            lo, hi = 500, 30000
        elif is_btr or is_vcb:
            lo, hi = 200, 20000
        else:
            lo, hi = 5, 5000
        values = [random.randint(lo, hi) for _ in pts]

    elif sensor_type in ("TEMP", "OIL_TEMP"):
        if is_btr or is_ltr:
            lo, hi = 35.0, 95.0
        else:
            lo, hi = 25.0, 70.0
        values = [round(random.uniform(lo, hi), 1) for _ in pts]

    elif sensor_type == "LF":
        # 0.10 ~ 0.95
        values = [round(random.uniform(0.10, 0.95), 2) for _ in pts]

    elif sensor_type == "STATUS":
        # 대부분 1 유지, 가끔 토글
        if random.random() < 0.03:
            # 토글 이벤트성
            # 예: 0:1;24:0;45:0;57:1
            seq = []
            state = 1
            flip_at = random.choice([24, 45])
            for s in pts:
                if s == flip_at:
                    state = 0
                seq.append((s, state))
            # 마지막 복귀 확률
            if 57 in pts and random.random() < 0.7:
                seq = [(s, (1 if s == 57 else v)) for s, v in seq]
            return ";".join(f"{s}:{v}" for s, v in seq)
        else:
            values = [1 for _ in pts]

    elif sensor_type == "TRIP":
        # 기본 0, 극소수만 1 찍고 복귀
        if random.random() < 0.005:
            # 1을 한 번 찍고 복귀
            onesec = random.choice([12, 24, 45])
            seq = []
            for s in pts:
                seq.append((s, 1 if s == onesec else 0))
            return ";".join(f"{s}:{v}" for s, v in seq)
        else:
            values = [0 for _ in pts]

    else:
        values = [0 for _ in pts]

    return ";".join(f"{s}:{v}" for s, v in zip(pts, values))


class SQLiteProvider(BaseProvider):
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def list_tags(
        self,
        site: Optional[str] = None,
        building: Optional[str] = None,
        room: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[TagRow]:
        where = []
        params = []

        if site:
            where.append("SITE = ?")
            params.append(site)
        if building:
            where.append("BUILDING = ?")
            params.append(building)
        if room:
            where.append("ROOM = ?")
            params.append(room)

        sql = """
        SELECT EQP_NO, EQP_NAME, EQP_TAG_CODE, SENSOR_TYPE, SITE, BUILDING, ROOM
        FROM TB_TAG_INFO
        """
        if where:
            sql += " WHERE " + " AND ".join(where)

        sql += " ORDER BY EQP_NO"

        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        else:
            sql += " LIMIT -1 OFFSET ?"
            params.append(offset)

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        return [TagRow(**dict(r)) for r in rows]

    def get_tags_by_eqp_nos(self, eqp_nos: Sequence[str]) -> List[TagRow]:
        if not eqp_nos:
            return []

        placeholders = ",".join(["?"] * len(eqp_nos))
        sql = f"""
        SELECT EQP_NO, EQP_NAME, EQP_TAG_CODE, SENSOR_TYPE, SITE, BUILDING, ROOM
        FROM TB_TAG_INFO
        WHERE EQP_NO IN ({placeholders})
        """

        with self._connect() as conn:
            rows = conn.execute(sql, list(eqp_nos)).fetchall()

        return [TagRow(**dict(r)) for r in rows]

    def get_latest_trends(self, eqp_nos: Sequence[str]) -> List[TrendRow]:
        if not eqp_nos:
            return []

        placeholders = ",".join(["?"] * len(eqp_nos))

        # 같은 EQP_NO에 여러 row가 있을 수 있으니 TRND_DATE 최대값만 가져오기
        sql = f"""
        SELECT b.EQP_NO, b.TRND_DATE, b.TRND_VALUE
        FROM TB_TREND_INFO b
        JOIN (
            SELECT EQP_NO, MAX(TRND_DATE) AS MAX_DATE
            FROM TB_TREND_INFO
            WHERE EQP_NO IN ({placeholders})
            GROUP BY EQP_NO
        ) m
        ON b.EQP_NO = m.EQP_NO AND b.TRND_DATE = m.MAX_DATE
        """

        with self._connect() as conn:
            rows = conn.execute(sql, list(eqp_nos)).fetchall()

        return [TrendRow(**dict(r)) for r in rows]

    def upsert_trends_for_minute(self, trnd_date_minute: Optional[str] = None) -> int:
        """
        (KR) TB_TAG_INFO의 모든 EQP_NO에 대해
             TB_TREND_INFO(EQP_NO, TRND_DATE) 기준으로 upsert
        """
        trnd_date = trnd_date_minute or _now_minute_str()
        now_ts = _now_second_str()

        with self._connect() as conn:
            tags = conn.execute("""
                SELECT EQP_NO, EQP_TAG_CODE, SENSOR_TYPE
                FROM TB_TAG_INFO
                ORDER BY EQP_NO
            """).fetchall()

            upserted = 0
            for r in tags:
                eqp_no = r["EQP_NO"]
                eqp_tag_code = r["EQP_TAG_CODE"]
                sensor_type = r["SENSOR_TYPE"]
                series = _make_sparse_series(sensor_type, eqp_tag_code)

                # 1) 존재 여부 확인
                exists = conn.execute(
                    "SELECT 1 FROM TB_TREND_INFO WHERE EQP_NO=? AND TRND_DATE=? LIMIT 1",
                    (eqp_no, trnd_date),
                ).fetchone()

                if exists:
                    # UPDATE
                    # (전하 테이블에 UPDATED_AT이 없으면 아래 컬럼/값 제거)
                    conn.execute(
                        """
                        UPDATE TB_TREND_INFO
                        SET TRND_VALUE = ?, UPDATED_AT = ?
                        WHERE EQP_NO = ? AND TRND_DATE = ?
                        """,
                        (series, now_ts, eqp_no, trnd_date),
                    )
                else:
                    # INSERT
                    # (전하 테이블에 CREATED_AT/UPDATED_AT이 없으면 아래 컬럼/값 제거)
                    conn.execute(
                        """
                        INSERT INTO TB_TREND_INFO (EQP_NO, TRND_DATE, TRND_VALUE, CREATED_AT, UPDATED_AT)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (eqp_no, trnd_date, series, now_ts, now_ts),
                    )

                upserted += 1

        return upserted
