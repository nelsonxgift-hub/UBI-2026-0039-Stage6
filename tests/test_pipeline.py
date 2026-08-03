import pipeline
import graph_builder
import decision as decision_mod
from loaders import load_assurance_contract, load_telemetry


def test_pipeline_runs_and_returns_verdicts():
    result = pipeline.run_pipeline()
    assert len(result["verdicts"]) > 0
    for v in result["verdicts"]:
        assert v["status"] in {"pass", "fail", "insufficient", "malformed"}
        assert v["artifact"]
        assert v["locator"]


def test_insufficient_is_never_silently_promoted_to_pass():
    result = pipeline.run_pipeline()
    # IAM-04 has no supplied evidence at all -- must surface as insufficient, never pass
    iam04 = [v for v in result["verdicts"] if v["claim_id"] == "IAM-04"]
    assert iam04
    assert all(v["status"] != "pass" for v in iam04)
    assert any(v["status"] == "insufficient" for v in iam04)


def test_broken_hash_chain_is_detected():
    result = pipeline.run_pipeline()
    hash_findings = [v for v in result["verdicts"] if v["check_id"] == "access.hash_chain"]
    assert any(v["status"] == "fail" and v["code"] == "HASH_CHAIN_BROKEN" for v in hash_findings)


def test_deletion_job_success_before_completion_is_detected():
    result = pipeline.run_pipeline()
    findings = [v for v in result["verdicts"] if v["check_id"] == "deletion.order"]
    assert any(v["code"] == "SUCCESS_BEFORE_COMPLETION" for v in findings)
    # It must NOT pass merely because status field says "success"
    assert not all(v["status"] == "pass" for v in findings)


def test_backup_purge_unproven_detected_for_del710():
    result = pipeline.run_pipeline()
    findings = [v for v in result["verdicts"] if v["check_id"] == "deletion.backup"]
    assert any(v["code"] == "BACKUP_PURGE_UNPROVEN" for v in findings)


def test_region_claim_contradicted_detected():
    result = pipeline.run_pipeline()
    findings = [v for v in result["verdicts"] if v["check_id"] == "location.claim"]
    assert any(v["code"] == "REGION_CLAIM_CONTRADICTED" for v in findings)


def test_undisclosed_subprocessors_detected():
    result = pipeline.run_pipeline()
    findings = [v for v in result["verdicts"] if v["check_id"] == "subprocessor.disclosed"]
    undisclosed = [v for v in findings if v["code"] == "UNDISCLOSED_SUBPROCESSOR"]
    assert len(undisclosed) == 3  # QueueNorth, AssistWorks, ArchiveLane


def test_every_verdict_ties_to_an_exact_locator_and_no_two_are_identical_locators_for_same_check():
    result = pipeline.run_pipeline()
    seen = set()
    for v in result["verdicts"]:
        key = (v["check_id"], v["locator"])
        assert key not in seen, f"duplicate locator for {key}"
        seen.add(key)


def test_pipeline_is_deterministic_across_runs():
    r1 = pipeline.run_pipeline()
    r2 = pipeline.run_pipeline()
    assert r1["verdicts"] == r2["verdicts"]
    assert r1["source_hashes"] == r2["source_hashes"]


def test_graph_accounts_for_every_subprocessor_edge():
    ac, _, _ = load_assurance_contract()
    tel, _, _ = load_telemetry()
    nodes, edges = graph_builder.build_graph(ac, tel)
    for sp in ac["subprocessors"]:
        assert sp["id"] in nodes
    for sp in tel["subprocessors"]:
        assert sp["id"] in nodes


def test_graph_has_no_unexpected_cycles_or_orphans():
    ac, _, _ = load_assurance_contract()
    tel, _, _ = load_telemetry()
    nodes, edges = graph_builder.build_graph(ac, tel)
    findings = graph_builder.validate_graph(nodes, edges)
    cycles = [f for f in findings if f["type"] == "cycle"]
    orphans = [f for f in findings if f["type"] == "orphan"]
    assert cycles == []
    assert orphans == []


def test_decision_has_executable_fail_closed_conditions_for_every_material_code():
    result = pipeline.run_pipeline()
    ac, _, _ = load_assurance_contract()
    tel, _, _ = load_telemetry()
    nodes, edges = graph_builder.build_graph(ac, tel)
    graph_findings = graph_builder.validate_graph(nodes, edges)
    dec = decision_mod.summarize(result["verdicts"], graph_findings, contract_value_usd=180000)

    assert dec["decision"] in {"approve", "conditional_approve", "defer", "reject"}
    for cond in dec["conditions"]:
        assert cond["owner"]
        assert cond["due_in_days"] > 0
        assert cond["evidence_of_closure"]
        assert cond["fail_closed_action"]  # this is the "executable, fail-closed" requirement

    # Contract value exceeds the CEO-approval threshold from the controlling overlay
    assert dec["requires_ceo_approval"] is True
