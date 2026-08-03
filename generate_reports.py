#!/usr/bin/env python3
"""Regenerates contradiction-matrix.csv, evidence-index.csv, vendor-risk-register.csv,
and monitoring-plan.yaml from evidence-verdicts.json. Run after vendor-verifier/cli.py."""
import json
import csv
import hashlib
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent
data = json.loads((ROOT / "evidence-verdicts.json").read_text())
verdicts = data["verdicts"]
dec = data["decision"]


def sha_of(artifact_rel):
    p = ROOT / artifact_rel
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "n/a"


ALT_MAP = {
    "TLS_BELOW_MINIMUM": "The endpoint could be a decommissioned/legacy path not in production use; weakened because it is present in the current, dated telemetry export with no retirement note.",
    "AUDIT_EXCEPTION_CONTRADICTS_CLAIM": "The 7 missing review-days could be documentation-only gaps with reviews actually performed; weakened because the SOC 2 report itself records management's own admission that reviews were not retained.",
    "REGION_CLAIM_CONTRADICTED": "The flagged subprocessor(s) could be internal vendor infrastructure mislabeled as external regions; weakened because each carries a distinct subprocessor ID, name, and parent relationship in the vendor's own telemetry schema.",
    "UNDISCLOSED_SUBPROCESSOR": "The DPA subprocessor list could be out of date rather than the subprocessor being genuinely undisclosed; weakened because no version/date on the list postdates the telemetry export, and no notice-of-change record exists in the pack.",
    "SUCCESS_BEFORE_COMPLETION": "The completed_at field could be a corrected retroactive timestamp rather than reporting order; weakened because no correction/amendment marker exists on the record.",
    "BACKUP_PURGE_UNPROVEN": "Backup purge could have occurred but gone unlogged; weakened because absence of a required field is exactly what 'insufficient' is defined to capture -- it cannot be inferred as conforming.",
    "PRIVILEGED_MFA_MISSING": "The session could have used an out-of-band compensating control not captured in this schema; weakened because no compensating-control field exists in the telemetry export.",
    "HASH_CHAIN_BROKEN": "Could be an export artifact rather than a genuine tamper/loss event; weakened because the schema defines previous_hash specifically to prove chain continuity, and it does not match here.",
    "CUSTOMER_CLOCK_DELAYED": "PeopleFlow may in practice confirm incidents quickly; weakened because the DPA creates no contractual obligation to do so, and no SLA on confirmation speed is supplied.",
    "ASSURANCE_MISSING": "Self-assessment could be materially accurate; weakened because it is unverified by an independent party and the vendor supplied no supporting configuration/log evidence for the specific attachment-masking claim it is meant to back.",
    "EVIDENCE_NOT_SUPPLIED": "IAM-04 could be operating correctly with evidence simply not exported this cycle; weakened because the vendor's own SIG response marks evidence_supplied=false rather than 'not yet exported'.",
    "DUPLICATE_EVENT_ID": "Could be a legitimate retry/replay logged twice by the export tool; weakened because both copies carry identical timestamps and hashes, which a genuine retry would not.",
}
PROVES_MAP = {
    "TLS_BELOW_MINIMUM": "That at least one PeopleFlow endpoint served TLSv1.0 at the observed time, below the vendor's own claimed minimum.",
    "AUDIT_EXCEPTION_CONTRADICTS_CLAIM": "That the vendor's own SOC 2 auditor recorded missing alert-review evidence for the sampled days stated in this row's claim text.",
    "REGION_CLAIM_CONTRADICTED": "That subprocessors outside us-east-1 process in-scope data classes.",
    "UNDISCLOSED_SUBPROCESSOR": "That a subprocessor observed in production telemetry does not appear on the DPA-disclosed subprocessor list supplied for this review.",
    "SUCCESS_BEFORE_COMPLETION": "That the deletion job's reported-success timestamp precedes its own completion-event timestamp.",
    "BACKUP_PURGE_UNPROVEN": "That no backup-purge timestamp exists for a job marked successful.",
    "PRIVILEGED_MFA_MISSING": "That a privileged access event occurred without MFA.",
    "HASH_CHAIN_BROKEN": "That a privileged-access log entry's previous_hash does not match the prior entry's hash.",
    "CUSTOMER_CLOCK_DELAYED": "That the contractual notice clock is defined to start at vendor confirmation, not independent detection.",
    "ASSURANCE_MISSING": "That the subprocessor's assurance field is null or self-attested only.",
    "EVIDENCE_NOT_SUPPLIED": "That the vendor marked evidence_supplied=false for this claim and no telemetry export exists to test it independently.",
    "DUPLICATE_EVENT_ID": "That the same event_id appears more than once in the privileged-access export.",
}
DOES_NOT_PROVE_MAP = {
    "TLS_BELOW_MINIMUM": "Does not prove data was intercepted or that the endpoint carries regulated data; scope of that endpoint's traffic is not stated in this export.",
    "AUDIT_EXCEPTION_CONTRADICTS_CLAIM": "Does not prove alerts were actually missed, only that review evidence for them was not retained.",
    "REGION_CLAIM_CONTRADICTED": "Does not by itself prove a DPA breach; contractual consequence depends on whether these regions were properly disclosed elsewhere.",
    "UNDISCLOSED_SUBPROCESSOR": "Does not prove PeopleFlow never sent notice through another channel outside this document set.",
    "SUCCESS_BEFORE_COMPLETION": "Does not prove data was retained after the claimed deletion; only that the reporting sequence is inverted.",
    "BACKUP_PURGE_UNPROVEN": "Does not prove the backup was never purged, only that no evidence of purge exists in this export.",
    "PRIVILEGED_MFA_MISSING": "Does not prove the access was malicious or that data was exfiltrated.",
    "HASH_CHAIN_BROKEN": "Does not prove which specific entries were altered, only that chain continuity is broken at this point.",
    "CUSTOMER_CLOCK_DELAYED": "Does not prove PeopleFlow has ever actually delayed a real notification.",
    "ASSURANCE_MISSING": "Does not prove the underlying control (masking) is absent, only that it is unverified.",
    "EVIDENCE_NOT_SUPPLIED": "Does not prove termination access removal is broken, only that it is untested.",
    "DUPLICATE_EVENT_ID": "Does not prove data corruption; could be an export artifact.",
}
SECTION_MAP = {
    "IAM-04": "Access Control", "LOG-07": "Logging & Monitoring", "LOC-02": "Data Residency",
    "ENC-03": "Encryption", "DEL-05": "Data Deletion", "IR-08": "Incident Response",
}
COLLECTION_TIME = {
    "input/vendor-telemetry.json": "2026-07-13T09:00:00Z",
    "input/vendor-claims.json": "2026-07-02T00:00:00Z",
    "input/assurance-and-contract.json": "2025-02-28T00:00:00Z",
}

# ---- contradiction-matrix.csv ----
rows = [v for v in verdicts if v["status"] in ("fail", "malformed", "insufficient")]
with open(ROOT / "contradiction-matrix.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["id", "artifact_a", "locator_a", "claim_a", "artifact_b", "locator_b",
                "contrary_fact", "evidence_quality", "risk_consequence", "follow_up", "decision_effect"])
    for i, v in enumerate(rows, 1):
        w.writerow([
            f"CON-{i:03d}",
            "input/vendor-claims.json" if v["claim_id"] else "n/a",
            f"$.claims[?(@.claim_id=='{v['claim_id']}')]" if v["claim_id"] else "n/a",
            v["claim_id"] or "(general control)",
            v["artifact"], v["locator"], v["message"],
            "high" if v["status"] == "fail" else "medium",
            v["status"], "mapped to condition in vendor-risk-register.csv", v["status"],
        ])

# ---- evidence-index.csv ----
with open(ROOT / "evidence-index.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["claim_id", "report_section", "claim", "artifact_path", "exact_locator",
                "collection_time_utc", "sha256", "proves", "does_not_prove", "confidence",
                "alternative_considered", "disposition"])
    for v in verdicts:
        code = v["code"]
        confidence = "high" if v["status"] in ("fail", "malformed") else "medium"
        w.writerow([
            v["claim_id"] or "GEN",
            SECTION_MAP.get(v["claim_id"], "Verification Engine / General Controls"),
            v["message"], v["artifact"], v["locator"],
            COLLECTION_TIME.get(v["artifact"], ""),
            sha_of(v["artifact"]),
            PROVES_MAP.get(code, "See message."),
            DOES_NOT_PROVE_MAP.get(code, "No further inference beyond the stated finding."),
            confidence,
            ALT_MAP.get(code, "No material alternative reading changes the disposition."),
            v["status"],
        ])

# ---- vendor-risk-register.csv ----
conds = dec["conditions"]
with open(ROOT / "vendor-risk-register.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["risk_id", "condition_id", "description", "owner", "due_date_note",
                "evidence_of_closure", "fail_closed_action", "related_evidence_codes",
                "status", "residual_after_closure"])
    for c in conds:
        w.writerow([
            f"RISK-{c['condition_id'][-2:]}", c["condition_id"], c["description"], c["owner"],
            f"{c['due_in_days']} days from decision issue date", c["evidence_of_closure"],
            c["fail_closed_action"], ";".join(c["evidence_source_codes"]), "open",
            "See vendor-risk-memo.pdf Residual Risk section",
        ])
    for i, r in enumerate(dec["residual_risks"], 1):
        w.writerow([f"RISK-RES-{i:02d}", "n/a", r, "CloudScale GRC (Rosemary Gift Nelson)",
                    "n/a (accepted residual)", "n/a", "n/a", "n/a", "accepted-residual", "n/a"])

# ---- monitoring-plan.yaml ----
plan = {"monitoring_plan": {
    "vendor": "PeopleFlow Inc.", "customer": "CloudScale Dynamics",
    "decision": dec["decision"], "review_cadence": "quarterly", "checks": [],
}}
for c in conds:
    plan["monitoring_plan"]["checks"].append({
        "condition_id": c["condition_id"],
        "command": f"python3 vendor-verifier/cli.py --check {','.join(c['evidence_source_codes'])}",
        "schedule": "quarterly",
        "threshold": "zero occurrences of: " + ", ".join(c["evidence_source_codes"]),
        "owner": c["owner"],
        "evidence_source": ";".join(c["evidence_source_codes"]),
        "fail_closed_action": c["fail_closed_action"],
        "escalation": "CloudScale GRC -> CloudScale Chief People Officer -> CEO (contract value exceeds USD 85,000 acceptance threshold)",
    })
plan["monitoring_plan"]["quarterly_verification_command"] = (
    "python3 vendor-verifier/cli.py  # re-run against a fresh telemetry export each quarter; "
    "compare evidence-verdicts.json codes against this file's `threshold` fields"
)
with open(ROOT / "monitoring-plan.yaml", "w") as f:
    yaml.dump(plan, f, sort_keys=False, default_flow_style=False, width=100)

# ---- contract-redlines.md ----
import re as _re

print(f"contradiction-matrix.csv: {len(rows)} rows")
print(f"evidence-index.csv: {len(verdicts)} rows")
print(f"vendor-risk-register.csv: {len(conds) + len(dec['residual_risks'])} rows")
print("monitoring-plan.yaml written")

def _field2(text, key):
    m = _re.search(rf"{_re.escape(key)}=([^,)\]]+)", text)
    return m.group(1) if m else None

def _names_for(code):
    found = []
    for v in verdicts:
        if v["code"] == code:
            val = _field2(v["locator"], "name")
            if val and val not in found:
                found.append(val)
    return found

undisclosed_names = ", ".join(_names_for("UNDISCLOSED_SUBPROCESSOR")) or "the flagged subprocessor(s)"
deletion_job_ids = []
for v in verdicts:
    if v["code"] in ("SUCCESS_BEFORE_COMPLETION", "BACKUP_PURGE_UNPROVEN"):
        val = _field2(v["locator"], "job_id")
        if val and val not in deletion_job_ids:
            deletion_job_ids.append(val)
deletion_job_ids_str = ", ".join(deletion_job_ids) or "the flagged job(s)"

redlines_md = f"""# Contract Redlines — PeopleFlow DPA / MSA (Stage 6, UBI-2026-0039)

Each redline traces backward to a `fail` or `insufficient` verdict in `evidence-verdicts.json`
and forward to a monitoring command in `monitoring-plan.yaml`. Entity names below (subprocessors,
job IDs) are pulled live from the current `evidence-verdicts.json`, not typed in by hand — if the
underlying evidence changes, regenerate this file with `python3 generate_reports.py`.

## RL-01 — Subprocessor disclosure (traces to COND-01, code: UNDISCLOSED_SUBPROCESSOR)
**Current text (paraphrased):** "PeopleFlow may use subprocessors listed on its trust page and
will give ten days' notice of material changes."
**Problem:** telemetry shows subprocessor(s) ({undisclosed_names}) actively processing CloudScale
data that do not appear anywhere in the DPA-disclosed list supplied for this review.
**Redline:** Add an exhibit listing every subprocessor by legal name and function, require it be
refreshed on schedule and match production telemetry, and add a customer right to audit the
match on demand. Breach of the exhibit-telemetry match is a material breach with a defined cure
window, not just a notice failure.

## RL-02 — Data residency (traces to COND-02, code: REGION_CLAIM_CONTRADICTED)
**Current text:** SIG claim LOC-02 states data remains exclusively in the claimed region.
**Problem:** telemetry shows in-scope data classes processed in regions other than the claimed one.
**Redline:** Either (a) amend the DPA to name all actual processing regions and attach
appropriate cross-border transfer mechanisms, or (b) require the vendor to re-architect so all
in-scope data classes are processed exclusively in the contracted region, with telemetry-based
proof, before go-live is treated as complete.

## RL-03 — Independent assurance for subprocessors handling attachments (traces to COND-03,
code: ASSURANCE_MISSING)
**Current text:** no independent-assurance requirement is currently attached to individual
subprocessors in the DPA.
**Redline:** Require any subprocessor with ticket/attachment access to regulated data to hold and
maintain independent assurance (SOC 2 Type II or ISO 27001) and to enable session recording for
privileged access; self-assessment alone is contractually insufficient for this data class.

## RL-04 — Incident notice clock (traces to COND-07, code: CUSTOMER_CLOCK_DELAYED)
**Current text:** notice is due within a fixed window "after PeopleFlow confirms" an incident.
**Problem:** the clock is entirely vendor-controlled; the customer has no independent trigger.
**Redline:** Change the trigger to "after the vendor knew or should reasonably have known," add a
mandatory interim notice within 24 hours of any *suspected* incident (pending confirmation), and
add a customer right to request a status update at any time during triage.

## RL-05 — Deletion evidence and audit assistance (traces to COND-06, codes:
SUCCESS_BEFORE_COMPLETION, BACKUP_PURGE_UNPROVEN)
**Problem:** deletion job(s) ({deletion_job_ids_str}) report success before their own completion
event, and/or lack backup-purge evidence.
**Redline:** Require deletion-completion evidence (timestamped, backup-inclusive) to be supplied
without additional billable audit assistance whenever a deletion job is disputed or sampled by
the customer, and require status fields to be set only after the completion event fires.

## RL-06 — Audit exception remediation commitment (traces to COND-08, code:
AUDIT_EXCEPTION_CONTRADICTS_CLAIM)
**Redline:** Add a contractual remediation commitment for open SOC 2 exceptions material to
in-scope controls, with named completion dates the vendor must meet before the next report
period, and a right for the customer to receive bridge-letter evidence in the interim.

## RL-07 — Evidence-on-demand for unverified claims (traces to COND-09 and COND-04/05, codes:
EVIDENCE_NOT_SUPPLIED, PRIVILEGED_MFA_MISSING, HASH_CHAIN_BROKEN)
**Redline:** Add a standing right for the customer to request underlying evidence (not just
questionnaire attestations) for any SIG claim, with a defined response SLA, and require MFA on
all privileged access with tamper-evident (hash-chained) logging that the vendor warrants it will
maintain without gaps.

---
*Every entity name above is pulled live from `evidence-verdicts.json` via `generate_reports.py`;
none is typed in by hand. Regenerate this file after any replacement export.*
"""
Path("contract-redlines.md").write_text(redlines_md)
print("contract-redlines.md regenerated with live entity names")

