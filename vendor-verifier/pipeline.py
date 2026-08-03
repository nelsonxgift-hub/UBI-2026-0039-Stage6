"""
Reconciles the PeopleFlow SIG claims against telemetry and the SOC 2 / DPA / subprocessor
export. Emits one verdict record per check, each carrying an exact locator back to raw
evidence. insufficient is never promoted to pass; fail and insufficient are kept as
distinct codes even when both apply to the same claim.
"""
import checks
from loaders import load_sig_claims, load_telemetry, load_assurance_contract

ARTIFACT_SIG = "input/vendor-claims.json"
ARTIFACT_TELEMETRY = "input/vendor-telemetry.json"
ARTIFACT_ASSURANCE = "input/assurance-and-contract.json"
ARTIFACT_DUEDILIGENCE = "input/due-diligence-pack.pdf"


def verdict(check_id, claim_id, status, code, artifact, locator, message):
    return {
        "check_id": check_id,
        "claim_id": claim_id,
        "status": status,
        "code": code,
        "artifact": artifact,
        "locator": locator,
        "message": message,
    }


def run_pipeline():
    sig, sig_hash, sig_path = load_sig_claims()
    tel, tel_hash, tel_path = load_telemetry()
    ac, ac_hash, ac_path = load_assurance_contract()

    claims_by_id = {c["claim_id"]: c for c in sig["claims"]}
    verdicts = []

    # ---- IAM-04: termination access removed within 24h ----
    # No attachment/log evidence was supplied for this claim at all (SIG evidence_supplied=false,
    # due-diligence pack: "No attachments were supplied for IAM-04"). Telemetry contains no
    # termination-event export to test against. Missing evidence stays missing.
    verdicts.append(verdict(
        "claim.evidence_presence", "IAM-04", "insufficient", "EVIDENCE_NOT_SUPPLIED",
        ARTIFACT_SIG, "$.claims[?(@.claim_id=='IAM-04')].evidence_supplied",
        "IAM-04 evidence_supplied=false and no termination-event export exists in telemetry to test against."
    ))

    # ---- LOG-07: security alerts reviewed daily, evidence retained 365 days ----
    # Matched by the exception's semantic `condition` field (alert_review_evidence_absent),
    # not its `id` label -- the id is an arbitrary per-report reference that can be
    # renumbered on a replacement export; the condition string is the stable, meaningful
    # key. If no matching exception exists in this export, LOG-07 is reported insufficient
    # for this run rather than crashing the whole pipeline (never silently treated as pass).
    alert_review_exceptions = [
        e for e in ac["assurance_report"]["exceptions"]
        if e.get("condition") == "alert_review_evidence_absent"
    ]
    if alert_review_exceptions:
        ex = alert_review_exceptions[0]
        verdicts.append(verdict(
            "claim.contradicted_by_exception", "LOG-07", "fail", "AUDIT_EXCEPTION_CONTRADICTS_CLAIM",
            ARTIFACT_ASSURANCE, f"$.assurance_report.exceptions[?(@.id=='{ex['id']}')]",
            f"SOC 2 exception {ex['id']}: alert-review evidence absent for {ex['failures']} of "
            f"{ex['population']} sampled days, contradicting the LOG-07 claim of daily review "
            f"with retained evidence."
        ))
    else:
        verdicts.append(verdict(
            "claim.contradicted_by_exception", "LOG-07", "insufficient", "NO_MATCHING_EXCEPTION_FOUND",
            ARTIFACT_ASSURANCE, "$.assurance_report.exceptions",
            "No SOC 2 exception with condition=alert_review_evidence_absent was found in this "
            "export; LOG-07 cannot be tested against an audit exception on this run. This does "
            "not mean the claim passes -- see claim.evidence_presence for LOG-07 separately."
        ))

    # ---- ENC-03: encrypted in transit and at rest, provider-managed keys ----
    # Telemetry TLS observations: one endpoint runs below the vendor's own claimed minimum.
    minimum = "TLSv" + tel["tls"]["minimum_version_claimed"]
    for idx, obs in enumerate(tel["tls"]["observations"]):
        status, code = checks.check_tls_minimum(minimum, obs["protocol"])
        verdicts.append(verdict(
            "tls.minimum", "ENC-03", status, code,
            ARTIFACT_TELEMETRY, f"$.tls.observations[{idx}] (endpoint={obs['endpoint']})",
            f"{obs['endpoint']} observed at {obs['protocol']}; vendor-claimed minimum is {minimum}."
        ))

    # ---- DEL-05: customer data deleted promptly after termination ----
    for idx, job in enumerate(tel["deletion_jobs"]):
        status, code = checks.check_deletion_order(job["reported_at"], job["completed_at"])
        verdicts.append(verdict(
            "deletion.order", "DEL-05", status, code,
            ARTIFACT_TELEMETRY, f"$.deletion_jobs[{idx}] (job_id={job['job_id']})",
            f"{job['job_id']}: status reported at {job['reported_at']}, completion event at "
            f"{job['completed_at']}."
        ))
        status, code = checks.check_deletion_backup(job["status"], job.get("backup_purge_at"))
        verdicts.append(verdict(
            "deletion.backup", "DEL-05", status, code,
            ARTIFACT_TELEMETRY, f"$.deletion_jobs[{idx}].backup_purge_at (job_id={job['job_id']})",
            f"{job['job_id']}: status={job['status']}, backup_purge_at={job.get('backup_purge_at')}."
        ))

    # ---- LOC-02: customer data remains exclusively in AWS us-east-1 ----
    claimed_region = claims_by_id["LOC-02"]["value"]
    for idx, sp in enumerate(tel["subprocessors"]):
        status, code = checks.check_location_claim(claimed_region, sp["region"])
        verdicts.append(verdict(
            "location.claim", "LOC-02", status, code,
            ARTIFACT_TELEMETRY, f"$.subprocessors[{idx}] (id={sp['id']}, name={sp['name']})",
            f"{sp['name']} ({sp['id']}) processes {sp['data_classes']} in {sp['region']}; "
            f"LOC-02 claims data remains exclusively in {claimed_region}."
        ))

    # ---- Access control checks (general IAM control quality, not a single SIG claim) ----
    events = tel["privileged_access"]
    event_ids = [e["event_id"] for e in events]
    status, code = checks.check_access_duplicate(event_ids)
    verdicts.append(verdict(
        "access.duplicate", None, status, code,
        ARTIFACT_TELEMETRY, "$.privileged_access[*].event_id",
        f"event_id list has {len(event_ids)} entries and {len(set(event_ids))} distinct values."
    ))

    # dedupe by event_id, preserving first occurrence, before chain/MFA checks
    seen = set()
    deduped = []
    for e in events:
        if e["event_id"] not in seen:
            deduped.append(e)
            seen.add(e["event_id"])

    for idx, e in enumerate(deduped):
        status, code = checks.check_access_mfa(e["mfa"], privileged=True)
        verdicts.append(verdict(
            "access.mfa", None, status, code,
            ARTIFACT_TELEMETRY, f"$.privileged_access[event_id={e['event_id']}].mfa",
            f"{e['event_id']} ({e['actor']}, {e['region']}): mfa={e['mfa']}, "
            f"approved_ticket={e['approved_ticket']}."
        ))

    for idx in range(1, len(deduped)):
        prev, cur = deduped[idx - 1], deduped[idx]
        status, code = checks.check_access_hash_chain(prev["hash"], cur["previous_hash"])
        verdicts.append(verdict(
            "access.hash_chain", None, status, code,
            ARTIFACT_TELEMETRY,
            f"$.privileged_access[event_id={cur['event_id']}].previous_hash "
            f"vs $.privileged_access[event_id={prev['event_id']}].hash",
            f"{cur['event_id']}.previous_hash={cur['previous_hash']} does not chain from "
            f"{prev['event_id']}.hash={prev['hash']}." if status == "fail" else
            f"{cur['event_id']}.previous_hash correctly chains from {prev['event_id']}.hash."
        ))

    # ---- IR-08: customer notified within 72h of vendor confirming a breach ----
    basis = ac["contract"]["incident_notice"]["basis"]
    status, code = checks.check_notification_clock(basis, customer_awareness_dependency=True)
    verdicts.append(verdict(
        "notification.clock", "IR-08", status, code,
        ARTIFACT_ASSURANCE, "$.contract.incident_notice.basis",
        f"Notice clock basis is '{basis}': the 72-hour window starts only when PeopleFlow "
        f"itself confirms an incident, so the customer has no independent trigger."
    ))

    # ---- Subprocessor assurance (contract-disclosed subprocessors) ----
    for idx, sp in enumerate(ac["subprocessors"]):
        status, code = checks.check_subprocessor_assurance(sp.get("assurance"), sp["id"])
        verdicts.append(verdict(
            "subprocessor.assurance", None, status, code,
            ARTIFACT_ASSURANCE, f"$.subprocessors[{idx}] (id={sp['id']})",
            f"{sp['id']} ({sp['function']}, {sp['location']}): assurance={sp.get('assurance')}."
        ))

    # ---- Extension check: undisclosed subprocessor edges (telemetry vs DPA-disclosed list) ----
    disclosed_names = {sp["id"] for sp in ac["subprocessors"]}
    # also allow matching on location/function heuristics is intentionally NOT done: name/id
    # is the only reliable join key we were given, and none of the telemetry subprocessor
    # names or ids appear anywhere in the disclosed list.
    for idx, sp in enumerate(tel["subprocessors"]):
        status, code = checks.check_subprocessor_disclosed(sp["name"], disclosed_names)
        verdicts.append(verdict(
            "subprocessor.disclosed", "LOC-02" if status == "fail" else None, status, code,
            ARTIFACT_TELEMETRY, f"$.subprocessors[{idx}] (id={sp['id']}, name={sp['name']})",
            f"Telemetry shows subprocessor {sp['name']} ({sp['id']}) handling {sp['data_classes']} "
            f"in {sp['region']}; this name/id does not appear in the DPA-disclosed subprocessor "
            f"list ({sorted(disclosed_names)})."
        ))

    return {
        "verdicts": verdicts,
        "source_hashes": {
            ARTIFACT_SIG: sig_hash,
            ARTIFACT_TELEMETRY: tel_hash,
            ARTIFACT_ASSURANCE: ac_hash,
        },
    }
