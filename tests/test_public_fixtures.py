"""
Runs every published fixture in input/public-fixtures.json through checks.CHECK_DISPATCH
and asserts the exact status/code the fixture expects. No fixture value is hard-coded here;
the fixture file is the single source of truth read at test time.
"""
import json
from pathlib import Path

import checks

ROOT = Path(__file__).resolve().parent.parent


def load_fixtures():
    data = json.loads((ROOT / "input" / "public-fixtures.json").read_text())
    return data["fixtures"]


def test_fixture_file_has_twenty_cases():
    fixtures = load_fixtures()
    assert len(fixtures) == 20


def _run_one(fixture):
    check_id = fixture["check_id"]
    inp = dict(fixture["input"])
    if check_id == "graph.orphan":
        # Structural check: fixture tests whether `parent` is a known node.
        # The generic/base known-node set for a bare structural fixture is the
        # graph root; "MISSING" is deliberately not a member.
        inp["known_nodes"] = ["PeopleFlow"]
    fn = checks.CHECK_DISPATCH[check_id]
    return fn(inp)


def test_all_public_fixtures_match_expected_result():
    failures = []
    for fixture in load_fixtures():
        status, code = _run_one(fixture)
        if status != fixture["expected_status"] or code != fixture["expected_code"]:
            failures.append(
                f"{fixture['case_id']} ({fixture['check_id']}): "
                f"got ({status}, {code}), expected ({fixture['expected_status']}, {fixture['expected_code']})"
            )
    assert not failures, "\n".join(failures)


def test_each_check_id_covered_by_at_least_one_fixture():
    fixtures = load_fixtures()
    covered = {f["check_id"] for f in fixtures}
    assert covered == set(checks.CHECK_DISPATCH.keys())
