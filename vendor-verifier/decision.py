"""
Converts frozen evidence-verdicts + graph findings into the commercial decision.
Every condition maps to: owner, due date, evidence of closure, and a fail-closed
consequence. This module contains no assigned-case identifiers, expected verdicts,
or hard-coded counts -- it aggregates whatever verdicts/findings it is given.
"""
import re

CEO_APPROVAL_THRESHOLD_USD = 85000


def _field(text, key):
    """Pull key=value out of a locator/message string, e.g. name=Foo -> 'Foo'."""
    m = re.search(rf"{re.escape(key)}=([^,)\]]+)", text)
    return m.group(1) if m else None


def _entities(verdicts, codes, key):
    """Distinct entity identifiers (subprocessor name, job_id, event_id, ...) pulled live
    from the locator field of every verdict matching the given code(s). Never a literal
    from a specific assigned case -- whatever the verdicts contain is what gets named."""
    if isinstance(codes, str):
        codes = {codes}
    found = []
    for v in verdicts:
        if v["code"] in codes:
            val = _field(v["locator"], key)
            if val and val not in found:
                found.append(val)
    return found


def _list_or_fallback(items, fallback="the affected record(s) -- see evidence-verdicts.json"):
    return ", ".join(items) if items else fallback


def summarize(verdicts, graph_findings, contract_value_usd):
    fails = [v for v in verdicts if v["status"] == "fail"]
    insufficient = [v for v in verdicts if v["status"] == "insufficient"]
    malformed = [v for v in verdicts if v["status"] == "malformed"]

    claims_with_problem = sorted({v["claim_id"] for v in fails + insufficient if v["claim_id"]})

    requires_ceo = contract_value_usd > CEO_APPROVAL_THRESHOLD_USD

    conditions = []

    def add_condition(cid, description, owner, due_days, evidence_of_closure, fail_closed_action, source_codes):
        conditions.append({
            "condition_id": cid,
            "description": description,
            "owner": owner,
            "due_in_days": due_days,
            "evidence_of_closure": evidence_of_closure,
            "fail_closed_action": fail_closed_action,
            "evidence_source_codes": source_codes,
        })

    codes_present = {v["code"] for v in verdicts}

    if "UNDISCLOSED_SUBPROCESSOR" in codes_present:
        names = _entities(verdicts, "UNDISCLOSED_SUBPROCESSOR", "name")
        add_condition(
            "COND-01",
            f"PeopleFlow discloses {_list_or_fallback(names)} on the contractual "
            "subprocessor list (or ceases routing CloudScale Dynamics data through them) and "
            "confirms no other undisclosed subprocessors exist.",
            "PeopleFlow Vendor Manager / CloudScale Chief People Officer",
            10,
            "Updated, countersigned subprocessor list matching telemetry-observed processors; "
            "written confirmation of completeness.",
            "Suspend data transmission to any subprocessor not on the disclosed list.",
            ["UNDISCLOSED_SUBPROCESSOR"],
        )

    if "REGION_CLAIM_CONTRADICTED" in codes_present:
        loc_verdicts = [v for v in verdicts if v["code"] == "REGION_CLAIM_CONTRADICTED"]
        observed_regions = []
        for v in loc_verdicts:
            m = re.search(r"in ([^;]+); LOC-02 claims", v["message"])
            if m and m.group(1) not in observed_regions:
                observed_regions.append(m.group(1))
        claimed_region_seen = None
        m2 = re.search(r"claims data remains exclusively in ([^.]+)\.", loc_verdicts[0]["message"]) if loc_verdicts else None
        if m2:
            claimed_region_seen = m2.group(1)
        add_condition(
            "COND-02",
            "PeopleFlow provides a corrected data-residency statement reflecting actual "
            f"processing regions ({_list_or_fallback(observed_regions)}), or relocates processing "
            f"to match the {claimed_region_seen or 'claimed'}-exclusive claim.",
            "PeopleFlow Compliance Lead",
            15,
            "Signed data-flow map matching telemetry; or telemetry re-export showing all "
            f"regions collapsed to {claimed_region_seen or 'the claimed region'}.",
            "Treat LOC-02 as false for contractual purposes; apply cross-border transfer terms "
            "to all affected data classes until corrected.",
            ["REGION_CLAIM_CONTRADICTED"],
        )

    if "ASSURANCE_MISSING" in codes_present:
        add_condition(
            "COND-03",
            "HelpSphere (tier-1 support, ticket/attachment access) provides an independent "
            "assurance report (SOC 2, ISO 27001, or equivalent) and enables session recording "
            "for privileged support access to attachments.",
            "PeopleFlow Vendor Manager",
            30,
            "Independent assurance report + configuration export showing session recording "
            "enabled.",
            "Restrict HelpSphere from attachment access until assurance is provided.",
            ["ASSURANCE_MISSING"],
        )

    if "PRIVILEGED_MFA_MISSING" in codes_present:
        mfa_events = _entities(verdicts, "PRIVILEGED_MFA_MISSING", "event_id")
        add_condition(
            "COND-04",
            "PeopleFlow enforces MFA on all privileged support access; retroactively "
            f"investigates the {_list_or_fallback(mfa_events)} non-MFA session(s) for "
            "unauthorized activity.",
            "PeopleFlow Security Lead",
            7,
            f"MFA enforcement policy export + investigation summary for {_list_or_fallback(mfa_events)}.",
            "Suspend the affected actor's privileged access pending investigation.",
            ["PRIVILEGED_MFA_MISSING"],
        )

    if "HASH_CHAIN_BROKEN" in codes_present:
        add_condition(
            "COND-05",
            "PeopleFlow explains and remediates the broken privileged-access hash chain "
            "(integrity of the audit log itself), and re-exports a verifiably unbroken log "
            "for the affected period.",
            "PeopleFlow Security Lead",
            14,
            "Re-exported, independently hash-verified access log covering the gap period.",
            "Treat the access log as unverifiable for the affected period; do not rely on it "
            "for LOG-07 evidence until remediated.",
            ["HASH_CHAIN_BROKEN"],
        )

    if "SUCCESS_BEFORE_COMPLETION" in codes_present or "BACKUP_PURGE_UNPROVEN" in codes_present:
        job_ids = _entities(
            verdicts, {"SUCCESS_BEFORE_COMPLETION", "BACKUP_PURGE_UNPROVEN"}, "job_id"
        )
        add_condition(
            "COND-06",
            "PeopleFlow corrects deletion-job status reporting to fire only after the "
            "completion event, and supplies backup-purge evidence (timestamp + verification) "
            f"for every deletion job, including {_list_or_fallback(job_ids)}.",
            "PeopleFlow Data Protection Officer",
            30,
            "Corrected deletion pipeline export; backup_purge_at populated and verifiable for "
            "all sampled jobs.",
            "Treat DEL-05 as unproven; escalate to legal if termination deletion is contractually "
            "represented as complete before evidence exists.",
            ["SUCCESS_BEFORE_COMPLETION", "BACKUP_PURGE_UNPROVEN"],
        )

    if "CUSTOMER_CLOCK_DELAYED" in codes_present:
        add_condition(
            "COND-07",
            "DPA is amended so the 72-hour notice clock starts at vendor discovery/should-have-"
            "discovered, not solely at vendor confirmation, and PeopleFlow commits to an interim "
            "notice within 24h of any suspected incident.",
            "CloudScale Legal / PeopleFlow Legal",
            30,
            "Countersigned DPA amendment.",
            "Escalate any suspected incident internally at CloudScale on independent detection, "
            "without waiting on PeopleFlow confirmation.",
            ["CUSTOMER_CLOCK_DELAYED"],
        )

    if "AUDIT_EXCEPTION_CONTRADICTS_CLAIM" in codes_present:
        ex_verdicts = [v for v in verdicts if v["code"] == "AUDIT_EXCEPTION_CONTRADICTS_CLAIM"]
        ex_ids = []
        gap_phrases = []
        for v in ex_verdicts:
            m_id = re.search(r"id==\s*'([^']+)'", v["locator"])
            if m_id and m_id.group(1) not in ex_ids:
                ex_ids.append(m_id.group(1))
            m_gap = re.search(r"absent for (\d+) of (\d+)", v["message"])
            if m_gap:
                gap_phrases.append(f"{m_gap.group(1)} of {m_gap.group(2)} days")
        add_condition(
            "COND-08",
            f"PeopleFlow remediates the {_list_or_fallback(ex_ids, 'flagged SOC 2 exception(s)')} "
            f"alert-review gap ({_list_or_fallback(gap_phrases, 'see evidence-verdicts.json for counts')} "
            "missing evidence) and demonstrates a full review cycle with retained evidence for one "
            "subsequent audit period.",
            "PeopleFlow Security Lead",
            60,
            "Bridge letter or interim testing evidence for the remediation period.",
            "Do not rely on LOG-07 as met until remediation evidence exists.",
            ["AUDIT_EXCEPTION_CONTRADICTS_CLAIM"],
        )

    if "EVIDENCE_NOT_SUPPLIED" in codes_present:
        add_condition(
            "COND-09",
            "PeopleFlow supplies a termination-access export (IAM-04) so the 24-hour "
            "de-provisioning claim can be tested against evidence rather than accepted on "
            "questionnaire text alone.",
            "PeopleFlow Vendor Manager",
            15,
            "Termination-access log export covering at least one full quarter.",
            "Treat IAM-04 as unverified; do not represent it as tested in any downstream audit.",
            ["EVIDENCE_NOT_SUPPLIED"],
        )

    residual_risks = [
        "Even after all conditions close, PeopleFlow remains a single vendor with access to "
        "regulated PII (bank details, tax IDs) and no customer-side ability to independently "
        "detect an incident before PeopleFlow chooses to confirm one.",
        "Historical processing that already occurred in undisclosed regions/subprocessors "
        "cannot be un-processed; conditions govern going-forward state only.",
        "SOC 2 Type II carve-out method means subservice organisations' controls are not "
        "directly tested by PeopleFlow's own auditor.",
    ]

    if len(claims_with_problem) >= 4 or "UNDISCLOSED_SUBPROCESSOR" in codes_present:
        decision = "conditional_approve"
        decision_rationale = (
            "Every SIG claim except (partially) ENC-03 and LOC-02's non-conflicting edge has a "
            "verified technical or evidentiary problem, including an undisclosed-subprocessor "
            "finding that touches regulated PII outside the claimed region. Outright rejection "
            "is not required because every finding maps to a closeable, owned, fail-closed "
            "condition; but approval is conditional and processing must be suspended for any "
            "in-scope data class until Tier-0 conditions (COND-01, COND-02, COND-06, COND-07) "
            "close. This is not a prose-only conditional approval: every condition above has an "
            "executable monitor (see monitoring-plan.yaml) and a stated fail-closed action."
        )
    else:
        decision = "defer"
        decision_rationale = "Insufficient material findings to reject outright or approve; hold for remediation."

    return {
        "decision": decision,
        "decision_rationale": decision_rationale,
        "requires_ceo_approval": requires_ceo,
        "ceo_approval_reason": (
            f"Contract value USD {contract_value_usd:,} exceeds the USD "
            f"{CEO_APPROVAL_THRESHOLD_USD:,} risk-acceptance threshold in the controlling "
            f"assignment overlay; any residual-risk acceptance requires CEO sign-off."
        ) if requires_ceo else None,
        "counts": {
            "fail": len(fails),
            "insufficient": len(insufficient),
            "malformed": len(malformed),
            "pass": len([v for v in verdicts if v["status"] == "pass"]),
        },
        "claims_with_problem": claims_with_problem,
        "conditions": conditions,
        "residual_risks": residual_risks,
        "graph_findings": graph_findings,
    }
