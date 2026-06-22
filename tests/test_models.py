import json
from pathlib import Path

from job104_mcp.models import SearchResult, JobDetail, JobSummary, format_salary

FIX = Path(__file__).parent / "fixtures"


def test_format_salary_range():
    assert format_salary(32000, 38000, 50) == "月薪 32,000~38,000 元"


def test_format_salary_negotiable():
    # truly negotiable: no floor and no ceiling
    assert format_salary(0, 9999999, 10) == "待遇面議"
    assert format_salary(0, 0, 50) == "待遇面議"


def test_format_salary_floor_only_is_not_negotiable():
    # real floor + 9999999 sentinel ceiling => "X 以上", NOT 面議
    assert format_salary(2200000, 9999999, 60) == "年薪 2,200,000 元以上"
    assert format_salary(55000, 9999999, 50) == "月薪 55,000 元以上"


def test_format_salary_hourly():
    assert format_salary(200, 220, 30) == "時薪 200~220 元"


def test_search_result_from_raw():
    payload = json.loads((FIX / "search_sample.json").read_text(encoding="utf-8"))
    result = SearchResult.from_raw(payload)
    assert isinstance(result, SearchResult)
    assert result.total == payload["metadata"]["pagination"]["total"]
    assert result.page == payload["metadata"]["pagination"]["currentPage"]
    assert result.has_next == (
        payload["metadata"]["pagination"]["currentPage"]
        < payload["metadata"]["pagination"]["lastPage"]
    )
    job = result.jobs[0]
    assert isinstance(job, JobSummary)
    assert job.job_no == payload["data"][0]["jobNo"]
    assert job.job_name == payload["data"][0]["jobName"]
    assert job.url.startswith("https://")
    # detail_id is the short code from link.job, used by get_job_detail
    assert job.detail_id == payload["data"][0]["link"]["job"].rstrip("/").split("/")[-1]


def test_job_detail_from_raw():
    payload = json.loads((FIX / "detail_sample.json").read_text(encoding="utf-8"))
    detail = JobDetail.from_raw(payload)
    assert isinstance(detail, JobDetail)
    assert detail.job_name
    assert detail.description


def test_from_raw_tolerates_missing_fields():
    result = SearchResult.from_raw({"data": [{}], "metadata": {}})
    assert result.jobs[0].job_no == ""
    assert result.total == 0
