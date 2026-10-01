"""Thin client for the 국가법령정보 공동활용 OPEN API (law.go.kr DRF)."""

import os
import time

import httpx
from dotenv import load_dotenv

BASE = "https://www.law.go.kr/DRF"

load_dotenv()


class LawAPIError(RuntimeError):
    pass


def _oc() -> str:
    oc = os.environ.get("LAW_OC")
    if not oc:
        raise LawAPIError("LAW_OC is not set (see .env.example)")
    return oc


def _get(endpoint: str, params: dict, retries: int = 3) -> httpx.Response:
    params = {"OC": _oc(), **params}
    for attempt in range(retries):
        try:
            resp = httpx.get(f"{BASE}/{endpoint}", params=params, timeout=30)
            resp.raise_for_status()
            # Auth failures come back as HTTP 200 with an error body.
            if "사용자 정보 검증에 실패" in resp.text[:500]:
                raise LawAPIError(f"OC rejected by law.go.kr: {resp.text[:200]}")
            return resp
        except httpx.HTTPError:
            if attempt == retries - 1:
                raise
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def search(target: str, query: str, **extra) -> list[dict]:
    """lawSearch.do as JSON; always returns a list of result rows."""
    resp = _get("lawSearch.do", {"target": target, "type": "JSON", "query": query, "display": 100, **extra})
    root = next(iter(resp.json().values()))
    rows = root.get(target if target != "eflaw" else "law", [])
    return rows if isinstance(rows, list) else [rows]


def service_xml(target: str, **params) -> bytes:
    """lawService.do as raw XML bytes (stored verbatim as the corpus snapshot)."""
    return _get("lawService.do", {"target": target, "type": "XML", **params}).content
