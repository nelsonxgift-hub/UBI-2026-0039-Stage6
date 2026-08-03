# Contract Redlines — PeopleFlow DPA / MSA (Stage 6, UBI-2026-0039)

Each redline traces backward to a `fail` or `insufficient` verdict in `evidence-verdicts.json`
and forward to a monitoring command in `monitoring-plan.yaml`. Entity names below (subprocessors,
job IDs) are pulled live from the current `evidence-verdicts.json`, not typed in by hand — if the
underlying evidence changes, regenerate this file with `python3 generate_reports.py`.

## RL-01 — Subprocessor disclosure (traces to COND-01, code: UNDISCLOSED_SUBPROCESSOR)
**Current text (paraphrased):** "PeopleFlow may use subprocessors listed on its trust page and
will give ten days' notice of material changes."
**Problem:** telemetry shows subprocessor(s) (QueueNorth, AssistWorks, ArchiveLane) actively processing CloudScale
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
**Problem:** deletion job(s) (DEL-710) report success before their own completion
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
