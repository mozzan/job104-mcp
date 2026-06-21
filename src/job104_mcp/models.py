"""Raw 104 JSON -> clean dataclasses. Tolerant of missing fields. No network."""
from __future__ import annotations

from dataclasses import dataclass

_NEGOTIABLE_HIGH = 9999999


def format_salary(low: int, high: int, s5: int) -> str:
    if not low or high >= _NEGOTIABLE_HIGH:
        return "待遇面議"
    if low == high:
        return f"月薪 {low:,} 元"
    return f"月薪 {low:,}~{high:,} 元"


def _job_url(d: dict) -> str:
    link = (d.get("link") or {}).get("job", "")
    if link.startswith("//"):
        return "https:" + link
    return link or ""


def _detail_id(d: dict) -> str:
    """The short code 104's detail endpoint keys on (last path segment of link.job)."""
    url = _job_url(d)
    return url.rstrip("/").split("/")[-1] if url else ""


@dataclass
class JobSummary:
    job_no: str
    detail_id: str
    job_name: str
    company: str
    salary: str
    location: str
    job_type: int
    remote: int
    applied_count: int
    snippet: str
    url: str
    appear_date: str

    @classmethod
    def from_raw(cls, d: dict) -> "JobSummary":
        return cls(
            job_no=d.get("jobNo", ""),
            detail_id=_detail_id(d),
            job_name=d.get("jobName", ""),
            company=d.get("custName", ""),
            salary=format_salary(
                d.get("salaryLow", 0), d.get("salaryHigh", 0), d.get("s5", 0)
            ),
            location=d.get("jobAddrNoDesc", ""),
            job_type=d.get("jobType", 0),
            remote=d.get("remoteWorkType", 0),
            applied_count=d.get("applyCnt", 0),
            snippet=d.get("descSnippet", "") or d.get("description", ""),
            url=_job_url(d),
            appear_date=d.get("appearDate", ""),
        )


@dataclass
class SearchResult:
    jobs: list[JobSummary]
    total: int
    page: int
    has_next: bool

    @classmethod
    def from_raw(cls, payload: dict) -> "SearchResult":
        pg = (payload.get("metadata") or {}).get("pagination") or {}
        current = pg.get("currentPage", 1)
        last = pg.get("lastPage", 1)
        return cls(
            jobs=[JobSummary.from_raw(d) for d in payload.get("data", [])],
            total=pg.get("total", 0),
            page=current,
            has_next=current < last,
        )


def _join_requirements(cond: dict) -> str:
    """Build a readable requirements line from the condition block."""
    parts: list[str] = []
    if cond.get("workExp"):
        parts.append(f"經驗：{cond['workExp']}")
    if cond.get("edu"):
        parts.append(f"學歷：{cond['edu']}")
    if cond.get("major"):
        parts.append(f"科系：{cond['major']}")
    other = cond.get("other")
    if isinstance(other, list):
        other = "；".join(str(x) for x in other if x)
    if other:
        parts.append(str(other))
    return "\n".join(parts)


@dataclass
class JobDetail:
    job_no: str
    job_name: str
    company: str
    description: str
    requirements: str
    salary: str
    location: str
    url: str

    @classmethod
    def from_raw(cls, payload: dict) -> "JobDetail":
        data = payload.get("data") or {}
        header = data.get("header") or {}
        jd = data.get("jobDetail") or {}
        cond = data.get("condition") or {}
        return cls(
            job_no=data.get("jobNo", ""),
            job_name=header.get("jobName", ""),
            company=header.get("custName", ""),
            description=jd.get("jobDescription", ""),
            requirements=_join_requirements(cond),
            salary=jd.get("salary", ""),
            location=jd.get("addressRegion", "") + jd.get("addressDetail", ""),
            url="",
        )
