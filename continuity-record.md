# Continuity Record — Stage 6 (Advanced Project 2)

## 1. Previous-stage commit and component reused

**Prior stage:** Advanced Stage, Project 1 — "Policy as Code Under Constraint" (UBI-2026-0039),
OPA/Rego control-outcome mapping for the CloudScale Dynamics case.

**Component reused:** the typed evidence-status vocabulary established in Project 1
(`pass` / `fail` / `insufficient` / `malformed`, each carrying an exact locator back to raw
input) is carried forward unchanged as the contract for every check in
`vendor-verifier/checks.py`. `insufficient` is preserved as a distinct, non-promotable status in
both stages — a policy that could not be evaluated for lack of evidence in Project 1 is the same
category as a SIG claim with no supplied evidence in this stage.

**Resolved before final submission.** Project 1's final submitted repository (`~/ubi-submission`,
commit message: "Final submission: 14 deliverables complete. 30/30 tests passing, 9 violations
verified against real data, manifest.sha256 generated last as required.") supplied the OPA policy
bundle at `policy-bundle/` (`identity.rego`, `storage.rego`, `endpoint.rego`) and its paired tests
under `tests/` (`identity_test.rego`, `storage_test.rego`). This Stage 6 pipeline's
pass/fail/insufficient/malformed status vocabulary carries forward the same non-promotable-`insufficient`
policy established there, as described above.

**Prior-stage commit:** `d1985eb52175b33ab5b9071ceab748f98b9b703e`

## 2. Interface consumed and backward-compatible extension

Project 1 emitted policy verdicts against a fixed rule set with no explicit distinction between
"the input violates the rule" and "the input lacks the field the rule needs." Stage 6 extends
this into a 4-way status (`pass`/`fail`/`insufficient`/`malformed`) because vendor evidence, unlike
policy-as-code input, routinely arrives incomplete rather than merely non-compliant. This is a
backward-compatible extension: any Project 1 consumer expecting `pass`/`fail` only can still
treat `insufficient` and `malformed` as not-pass.

## 3. Evidence that prior raw-to-result provenance remains intact

Every verdict in `evidence-verdicts.json` in this stage carries the same discipline enforced in
Project 1: an exact artifact path + locator (JSONPath-style pointer or record identifier), never
a summary without a pointer. `tests/test_pipeline.py::test_every_verdict_ties_to_an_exact_locator_and_no_two_are_identical_locators_for_same_check`
enforces this mechanically.

## 4. Migration record for incompatible changes

No incompatible change was required. The only structural addition is the `malformed` status
(used here for `DUPLICATE_EVENT_ID` and `ORPHAN_NODE`), which did not exist as a first-class
category in Project 1's binary pass/fail model; it is additive, not a breaking change to anything
Project 1 produced.

## 5. What this stage hands to Stage 7 (audit)

- `evidence-verdicts.json` — the full, locator-complete verdict set (24 verdicts, 6 SIG claims
  tested, all 6 with at least one non-pass finding).
- `data-flow.graphml` — the subprocessor/data-flow graph, including the 3 telemetry-observed
  subprocessors flagged `disclosed=false` (QueueNorth, AssistWorks, ArchiveLane).
- `vendor-risk-register.csv` — 9 open conditions with owner, due date, evidence-of-closure, and
  fail-closed action; 3 accepted residual risks.
- The `conditional_approve` decision itself, with the CEO-approval flag (contract value USD
  180,000 exceeds the USD 85,000 threshold in the private overlay), as the governance record
  Stage 7 should audit against for actual closure evidence.
- `monitoring-plan.yaml`'s quarterly `--check` commands, so Stage 7 can re-run the same pipeline
  against a fresh telemetry export rather than starting evidence collection from zero.
