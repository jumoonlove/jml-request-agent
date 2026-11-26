"""Tests for the rule checks. These run without an API key: python -m pytest -q"""
import json
from datetime import date
from pathlib import Path

from agent import build_script, upn_for
from guardrails import check_request, clean_name

POLICY = json.loads((Path(__file__).parent / "policy.json").read_text())
TODAY = date(2026, 11, 26)


def joiner(**kw):
    base = {"action": "joiner", "full_name": "Sarah Kim", "department": "Finance",
            "role": "Analyst", "date": "2026-12-07", "date_text": "7 December", "all_people_mentioned": ["Sarah Kim"],
            "extra_access": [], "_request_text": "Sarah Kim joins Finance as Analyst on 7 December"}
    base.update(kw)
    return base


def test_good_joiner_passes():
    assert check_request(joiner(), POLICY, TODAY) == []


def test_unknown_department_blocked():
    assert check_request(joiner(department="Marketing"), POLICY, TODAY)


def test_admin_request_blocked():
    probs = check_request(joiner(extra_access=["Global Admin"]), POLICY, TODAY)
    assert any("Privileged" in p for p in probs)


def test_missing_date_blocked():
    assert check_request(joiner(date=None), POLICY, TODAY)


def test_past_start_date_blocked():
    assert check_request(joiner(date="2026-01-01"), POLICY, TODAY)


def test_first_name_only_blocked():
    assert check_request(joiner(full_name="Sarah"), POLICY, TODAY)


def test_leaver_passes_without_department():
    req = {"action": "leaver", "full_name": "Tom Lee", "department": None, "role": None,
           "date": "2026-11-30", "date_text": "this Friday", "all_people_mentioned": ["Tom Lee"], "extra_access": [],
           "_request_text": "Tom Lee's last day is this Friday"}
    assert check_request(req, POLICY, TODAY) == []


def test_two_people_blocked():
    req = joiner(all_people_mentioned=["Jin Park", "Jane O'Brien"])
    assert any("2 people" in p for p in check_request(req, POLICY, TODAY))


def test_guessed_date_blocked():
    # AI gave a date, but the words it quoted are not in the request
    assert check_request(joiner(date_text="the same day"), POLICY, TODAY)
    assert check_request(joiner(date_text=None), POLICY, TODAY)


def test_vague_date_blocked():
    # "the same day" IS in the text, but it points to a date that is not there
    req = joiner(date_text="the same day", _request_text="add Jane O'Brien as an Analyst in Finance from the same day")
    assert any("depends on" in p for p in check_request(req, POLICY, TODAY))
    assert check_request(joiner(date_is_clear=False), POLICY, TODAY)


def test_missing_role_message():
    assert "Role is missing for Finance." in check_request(joiner(role=None), POLICY, TODAY)


def test_apostrophe_name_is_safe():
    assert upn_for("Jane O'Brien") == "jane.obrien@contoso.onmicrosoft.com"
    script = build_script(joiner(full_name="Jane O'Brien"))
    assert "'Jane O''Brien'" in script


def test_name_capitalised():
    assert clean_name("Jin park") == "Jin Park"
    assert clean_name("jane o'brien") == "Jane O'brien"
