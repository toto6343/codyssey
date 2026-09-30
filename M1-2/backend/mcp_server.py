import os

import httpx
from mcp.server.fastmcp import FastMCP

# 로컬 테스트: http://localhost:8000 / 배포 후: Render 주소
API = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

mcp = FastMCP("boxoffice-assistant")


def _get(path: str, **params):
    r = httpx.get(f"{API}{path}", params=params or None, timeout=60)  # Render 콜드스타트 대비
    r.raise_for_status()
    return r.json()


@mcp.tool()
def get_data_summary() -> dict:
    """주말 박스오피스 기간/개수/기본 통계/추세 요약 조회"""
    return _get("/api/data/summary")


@mcp.tool()
def get_statistics() -> dict:
    """월별 통계, 중앙값, 표준편차, 직전 주 대비 증감률, 4주 이동평균 조회"""
    return _get("/api/data/statistics")


@mcp.tool()
def list_conversations() -> list:
    """저장된 대화 목록 조회"""
    return _get("/api/conversations")


@mcp.tool()
def get_conversation(conversation_id: str) -> dict:
    """특정 대화의 전체 메시지 조회"""
    return _get(f"/api/conversations/{conversation_id}")


if __name__ == "__main__":
    mcp.run()  # stdio 방식