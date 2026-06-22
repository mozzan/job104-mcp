"""Translate human-readable filters into 104 query params. No network."""
from __future__ import annotations

from .codes import load_area, load_jobcat, CodeTable

# 104 order codes: 15=relevance, 16=newest, 13=salary floor high→low.
# (order=11 is NOT a salary sort — it is roughly the default order and surfaces
# many 待遇面議 jobs at the top, so do not use it for salary.)
_SORT = {"relevance": "15", "date": "16", "salary": "13"}
_JOB_TYPE = {"全職": "1", "兼職": "2", "高階": "3", "派遣": "4", "接案": "5"}


class UnknownCodeError(Exception):
    def __init__(self, kind: str, query: str, suggestions: list[str]):
        self.kind = kind
        self.query = query
        self.suggestions = suggestions
        hint = ("；".join(suggestions)) if suggestions else "（找不到相近選項）"
        super().__init__(f"找不到{kind} '{query}'，你是不是指：{hint}")


def _resolve(names: list[str], table: CodeTable, kind: str) -> list[str]:
    codes: list[str] = []
    for name in names:
        matches = table.lookup(name, limit=5)
        if not matches:
            raise UnknownCodeError(kind, name, [])
        exact = next((m for m in matches if m[1] == name), None)
        if exact is None:
            # no exact name; surface suggestions so the AI can retry precisely
            raise UnknownCodeError(kind, name, [m[1] for m in matches])
        codes.append(exact[0])
    return codes


def build_search_params(
    *, keyword, area, jobcat, salary_min, job_type, remote,
    is_new, exp_years, edu, sort, page, page_size,
) -> dict:
    params: dict[str, str] = {
        "order": _SORT.get(sort, "15"),
        "page": str(page),
        "pagesize": str(page_size),
    }
    if keyword:
        params["keyword"] = keyword
        params["kwop"] = "7"
    if area:
        params["area"] = ",".join(_resolve(area, load_area(), "area"))
    if jobcat:
        params["jobcat"] = ",".join(_resolve(jobcat, load_jobcat(), "jobcat"))
    if salary_min is not None:
        params["scmin"] = str(salary_min)
        params["scstrict"] = "1"
    if remote:
        params["remoteWork"] = "1,2"  # 1=完全遠端, 2=部分遠端; include both
    if is_new:
        params["isnew"] = "7"
    if job_type and job_type in _JOB_TYPE:
        params["wt"] = _JOB_TYPE[job_type]
    if exp_years is not None:
        params["jobexp"] = str(exp_years)
    if edu:
        params["edu"] = str(edu)
    return params
