import pytest
from job104_mcp.params import build_search_params, UnknownCodeError


def test_keyword_only():
    p = build_search_params(
        keyword="python", area=[], jobcat=[], salary_min=None,
        job_type=None, remote=None, is_new=False, exp_years=None,
        edu=None, sort="relevance", page=1, page_size=20,
    )
    assert p["keyword"] == "python"
    assert p["order"] == "15"
    assert p["page"] == "1"
    assert p["pagesize"] == "20"


def test_salary_sets_scstrict():
    p = build_search_params(
        keyword="", area=[], jobcat=[], salary_min=40000,
        job_type=None, remote=None, is_new=False, exp_years=None,
        edu=None, sort="salary", page=1, page_size=20,
    )
    assert p["scmin"] == "40000"
    assert p["scstrict"] == "1"
    assert p["order"] == "11"


def test_remote_and_isnew():
    p = build_search_params(
        keyword="x", area=[], jobcat=[], salary_min=None,
        job_type=None, remote=True, is_new=True, exp_years=None,
        edu=None, sort="date", page=1, page_size=20,
    )
    assert p["remoteWork"] == "1"
    assert p["isnew"] == "7"


def test_unknown_area_raises_with_suggestions():
    with pytest.raises(UnknownCodeError) as exc:
        build_search_params(
            keyword="", area=["火星市"], jobcat=[], salary_min=None,
            job_type=None, remote=None, is_new=False, exp_years=None,
            edu=None, sort="relevance", page=1, page_size=20,
        )
    assert exc.value.kind == "area"
    assert exc.value.query == "火星市"


def test_known_area_resolves_to_code():
    p = build_search_params(
        keyword="", area=["台北市大安區"], jobcat=[], salary_min=None,
        job_type=None, remote=None, is_new=False, exp_years=None,
        edu=None, sort="relevance", page=1, page_size=20,
    )
    assert p["area"].startswith("6001")
