"""FastMCP stdio server exposing 104 job search tools."""
from __future__ import annotations

from dataclasses import asdict

from mcp.server.fastmcp import FastMCP

from .client import Client, Client104Error
from .codes import load_area, load_jobcat
from .models import SearchResult, JobDetail
from .params import build_search_params, UnknownCodeError

mcp = FastMCP("job104")
_client = Client()


@mcp.tool()
def search_jobs(
    keyword: str = "",
    area: list[str] | None = None,
    jobcat: list[str] | None = None,
    salary_min: int | None = None,
    job_type: str | None = None,
    remote: bool | None = None,
    is_new: bool = False,
    exp_years: int | None = None,
    edu: str | None = None,
    sort: str = "relevance",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """搜尋 104 職缺。area/jobcat 用中文名稱（如 ["台北市大安區"]、["軟體工程師"]），
    內部自動轉成 104 代碼；若名稱不明確會回傳建議選項。每筆結果的 detail_id 可傳給
    get_job_detail 取得完整內容。sort: relevance|date|salary。"""
    try:
        params = build_search_params(
            keyword=keyword, area=area or [], jobcat=jobcat or [],
            salary_min=salary_min, job_type=job_type, remote=remote,
            is_new=is_new, exp_years=exp_years, edu=edu,
            sort=sort, page=page, page_size=page_size,
        )
    except UnknownCodeError as exc:
        return {"error": str(exc), "kind": exc.kind, "suggestions": exc.suggestions}
    try:
        raw = _client.search(params)
    except Client104Error as exc:
        return {"error": f"104 查詢失敗：{exc}"}
    result = SearchResult.from_raw(raw)
    return {
        "total": result.total,
        "page": result.page,
        "has_next": result.has_next,
        "jobs": [asdict(j) for j in result.jobs],
    }


@mcp.tool()
def get_job_detail(detail_id: str) -> dict:
    """取得單一職缺的完整內容（職務說明、條件、薪資、地點）。
    detail_id 來自 search_jobs 結果的 detail_id 欄位。"""
    try:
        raw = _client.job_detail(detail_id)
    except Client104Error as exc:
        return {"error": f"104 查詢失敗：{exc}"}
    return asdict(JobDetail.from_raw(raw))


@mcp.tool()
def lookup_code(kind: str, query: str) -> list[dict]:
    """查 104 職類/地區代碼。kind: 'jobcat' 或 'area'。回傳 [{name, code}]。"""
    table = load_jobcat() if kind == "jobcat" else load_area()
    return [{"name": name, "code": code} for code, name in table.lookup(query)]


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
