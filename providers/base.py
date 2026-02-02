# providers/base.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Dict, Any


@dataclass(frozen=True)
class TagRow:
    EQP_NO: str
    EQP_NAME: str
    EQP_TAG_CODE: str
    SENSOR_TYPE: str
    SITE: Optional[str] = None
    BUILDING: Optional[str] = None
    ROOM: Optional[str] = None


@dataclass(frozen=True)
class TrendRow:
    EQP_NO: str
    TRND_DATE: str  # 'YYYY-MM-DD HH:MM'
    TRND_VALUE: str


class BaseProvider:
    """
    (KR) EGMS가 의존하는 Provider 계약(Interface)입니다.
         SQLite → LakeProvider로 바꿔도, 아래 함수 시그니처는 유지합니다.
    (EN) Provider interface contract. Keep this stable to allow swapping providers.
    """

    def list_tags(
        self,
        site: Optional[str] = None,
        building: Optional[str] = None,
        room: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[TagRow]:
        raise NotImplementedError

    def get_tags_by_eqp_nos(self, eqp_nos: Sequence[str]) -> List[TagRow]:
        raise NotImplementedError

    def get_latest_trends(self, eqp_nos: Sequence[str]) -> List[TrendRow]:
        raise NotImplementedError

    def upsert_trends_for_minute(self, trnd_date_minute: Optional[str] = None) -> int:
        """
        (KR) 현재 분(trnd_date_minute)에 대해 EQP_NO별 1행씩 upsert 합니다.
        (EN) Upsert one trend row per EQP_NO for given minute.
        """
        raise NotImplementedError
