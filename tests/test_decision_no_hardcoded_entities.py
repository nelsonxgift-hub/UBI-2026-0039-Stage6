"""
Regression test for a real bug caught during review: decision.py originally had assigned-
case entity names (subprocessor names, a deletion job id, an access event id) typed as
literal strings in condition descriptions, so they survived unchanged even when the
underlying evidence changed. This test proves that can't silently happen again by running
the exact swap drill that caught it: rename every entity the decision conditions reference,
re-run the pipeline against the swapped copy, and assert none of the original names leak
into the regenerated decision text while the new names appear correctly.
"""
import copy
import json
import os
import shutil

import loaders
import pipeline
import graph_builder
import decision as decision_mod


def _make_scratch_writable(scratch):
    """shutil.copytree preserves source file permissions by default. Real evidence files
    are locked read-only (chmod 444) per the submission contract, so a naive copytree
    produces a scratch copy that is ALSO read-only -- these drills need to edit the copy,
    not the original, so the copy (not the source) must be made writable first."""
    for root, dirs, files in os.walk(scratch):
        for name in files:
            os.chmod(os.path.join(root, name), 0o644)


def test_decision_text_has_no_leftover_entity_names_after_replacement_export(tmp_path, monkeypatch):
    scratch = tmp_path / "input"
    shutil.copytree(loaders.INPUT_DIR, scratch)
    _make_scratch_writable(scratch)

    telemetry = json.loads((scratch / "vendor-telemetry.json").read_text())
    swapped = copy.deepcopy(telemetry)

    rename_map = {"QueueNorth": "RelayHub", "AssistWorks": "SupportBridge", "ArchiveLane": "ColdVaultEU"}
    for sp in swapped["subprocessors"]:
        if sp["name"] in rename_map:
            sp["name"] = rename_map[sp["name"]]
        if sp["parent"] in rename_map:
            sp["parent"] = rename_map[sp["parent"]]
    for job in swapped["deletion_jobs"]:
        if job["job_id"] == "DEL-710":
            job["job_id"] = "DEL-999"
    for ev in swapped["privileged_access"]:
        if ev["event_id"] == "PA-002":
            ev["event_id"] = "PA-777"

    (scratch / "vendor-telemetry.json").write_text(json.dumps(swapped, indent=2))
    monkeypatch.setattr(loaders, "INPUT_DIR", scratch)

    result = pipeline.run_pipeline()
    ac, _, _ = loaders.load_assurance_contract()
    tel, _, _ = loaders.load_telemetry()
    nodes, edges = graph_builder.build_graph(ac, tel)
    graph_findings = graph_builder.validate_graph(nodes, edges)
    dec = decision_mod.summarize(result["verdicts"], graph_findings, contract_value_usd=180000)

    full_text = json.dumps(dec)
    for stale_name in ("QueueNorth", "AssistWorks", "ArchiveLane", "DEL-710", "PA-002"):
        assert stale_name not in full_text, f"stale entity '{stale_name}' leaked into regenerated decision"

    for new_name in ("RelayHub", "SupportBridge", "ColdVaultEU", "DEL-999", "PA-777"):
        assert new_name in full_text, f"replacement entity '{new_name}' did not appear in regenerated decision"


def test_pipeline_does_not_crash_or_go_stale_when_exception_id_and_regions_change(tmp_path, monkeypatch):
    """
    Regression test for a second instance of the same underlying bug class, found on
    review of the first fix: pipeline.py looked up the SOC 2 alert-review exception by
    a hardcoded literal id ('EX-CC7.2') with no fallback, so renumbering that id in a
    replacement export raised an unhandled StopIteration and crashed the whole pipeline
    -- a strictly worse failure than stale text, since it produces no output at all.
    The fix matches on the exception's stable `condition` field instead of its arbitrary
    `id` label, and degrades to `insufficient` instead of crashing if no match exists.
    This test also swaps two subprocessor regions to prove COND-02 is genuinely live.
    """
    scratch = tmp_path / "input"
    shutil.copytree(loaders.INPUT_DIR, scratch)
    _make_scratch_writable(scratch)

    telemetry = json.loads((scratch / "vendor-telemetry.json").read_text())
    for sp in telemetry["subprocessors"]:
        if sp["id"] == "SP-02":
            sp["region"] = "ap-northeast-1"
        if sp["id"] == "SP-03":
            sp["region"] = "sa-east-1"
    (scratch / "vendor-telemetry.json").write_text(json.dumps(telemetry, indent=2))

    assurance = json.loads((scratch / "assurance-and-contract.json").read_text())
    for exc in assurance["assurance_report"]["exceptions"]:
        if exc["id"] == "EX-CC7.2":
            exc["id"] = "EX-CC7.9"
            exc["population"] = 60
            exc["failures"] = 22
    (scratch / "assurance-and-contract.json").write_text(json.dumps(assurance, indent=2))

    monkeypatch.setattr(loaders, "INPUT_DIR", scratch)

    # Must not raise. This is the assertion that would have caught the original bug --
    # the old code raised StopIteration here.
    result = pipeline.run_pipeline()

    ac, _, _ = loaders.load_assurance_contract()
    tel, _, _ = loaders.load_telemetry()
    nodes, edges = graph_builder.build_graph(ac, tel)
    graph_findings = graph_builder.validate_graph(nodes, edges)
    dec = decision_mod.summarize(result["verdicts"], graph_findings, contract_value_usd=180000)

    full_text = json.dumps(dec)
    assert "EX-CC7.2" not in full_text, "stale exception id 'EX-CC7.2' leaked into regenerated decision"
    assert "7 of 40" not in full_text, "stale exception counts '7 of 40' leaked into regenerated decision"
    assert "EX-CC7.9" in full_text, "new exception id 'EX-CC7.9' did not appear in regenerated decision"
    assert "22 of 60" in full_text, "new exception counts '22 of 60' did not appear in regenerated decision"
    assert "Philippines" not in full_text and "eu-west-1" not in full_text, \
        "stale region names leaked into regenerated COND-02 text"
    assert "ap-northeast-1" in full_text and "sa-east-1" in full_text, \
        "new region names did not appear in regenerated COND-02 text"


def test_no_crash_when_alert_review_exception_is_entirely_absent(tmp_path, monkeypatch):
    """If a replacement export removes the alert-review exception altogether (fully
    remediated vendor, or a different exception set), the pipeline must degrade to an
    `insufficient` verdict for that check, never crash and never silently report pass."""
    scratch = tmp_path / "input"
    shutil.copytree(loaders.INPUT_DIR, scratch)
    _make_scratch_writable(scratch)

    assurance = json.loads((scratch / "assurance-and-contract.json").read_text())
    assurance["assurance_report"]["exceptions"] = [
        e for e in assurance["assurance_report"]["exceptions"] if e.get("condition") != "alert_review_evidence_absent"
    ]
    (scratch / "assurance-and-contract.json").write_text(json.dumps(assurance, indent=2))
    monkeypatch.setattr(loaders, "INPUT_DIR", scratch)

    result = pipeline.run_pipeline()  # must not raise
    log07_verdicts = [v for v in result["verdicts"] if v["claim_id"] == "LOG-07" and v["check_id"] == "claim.contradicted_by_exception"]
    assert len(log07_verdicts) == 1
    assert log07_verdicts[0]["status"] == "insufficient"
    assert log07_verdicts[0]["status"] != "pass"
