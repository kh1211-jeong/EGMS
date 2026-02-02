# jobs/run_trend_job.py
from __future__ import annotations

import time
from datetime import datetime

from providers.sqlite_provider import SQLiteProvider


DB_PATH = r"C:\Users\정기흔\EGMS\EGMS.db"


def minute_key() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def run_forever():
    p = SQLiteProvider(DB_PATH)

    last_minute = None
    while True:
        cur = minute_key()
        if cur != last_minute:
            n = p.upsert_trends_for_minute(cur)
            print(f"[OK] upserted={n} trnd_date={cur}")
            last_minute = cur

        # 초 단위 폴링: 1초씩 자고 분 바뀌면 실행
        time.sleep(1)


if __name__ == "__main__":
    run_forever()
