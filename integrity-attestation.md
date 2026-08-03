# Advanced Project 2 Integrity Attestation

**Intern code:** UBI-2026-0039
**Variant:** V5 / D5 (shared base b1, private assignment set D5)
**Evidence marker:** UBI-A6-A643A704516C

I attest that I performed the submitted work on the assigned authorized artifacts. I have
declared material assistance below and can reproduce the work during artifact check. I did not
alter raw evidence, fabricate tool output, rewrite commit history, share restricted artifacts, or
cross scope.

## File-format note (resolved, not a UBI-side integrity failure)

An early file-handling discrepancy affecting five input files was identified and resolved before analysis began.

**Resolved by archive verification.** `grc-stage-6-shared-b1.tar.gz` (SHA-256
`3e5e6e8f39975da3e07d1b72a54181910e97db74c0d09b43c8553381e6866973`) was subsequently downloaded
and its hash matched the private overlay exactly. Its `evidence/brief/*.json` files were compared
programmatically (`json.load` + structural equality, not just byte diff) against `input/*.json`:
all four data files — `vendor-claims.json`, `vendor-telemetry.json`,
`assurance-and-contract.json`, `public-fixtures.json` — are **structurally identical**.
`evidence-pack.md`, the fifth file, was confirmed identical by direct SHA-256 match rather than
structural JSON comparison. No pipeline output, verdict, or decision changed as a result of this
reconciliation.
`assigned_pack.verified_before_use` in `assessment-manifest.json` is set to `true` accordingly.

## Assistance and tools used

Claude (Anthropic, Sonnet model) was used as an AI pair-programmer to implement the technical
components of this pipeline: the JSON schemas, the check functions (checks.py), the test suite,
the data-flow graph builder, the decision-engine logic (decision.py), and the report-generation
scripts (generate_memo.py, generate_reports.py).

My own work on top of that: I independently downloaded and hash-verified the assigned evidence
archive against the private overlay before trusting any of its content, rather than accepting it
at face value. I ran the full test suite myself, as a non-root user against my own locked
(chmod 444) evidence files, and reported a PermissionError that surfaced only in that real
environment, which led to identifying and fixing a permissions bug in the test suite's
scratch-copy handling. I reviewed the generated findings in evidence-verdicts.json against my own understanding
of the raw source documents, rather than accepting the pipeline's output on trust. I reviewed and adopted the interpretation that a subprocessor's
self-assessment does not meet an independent-assurance bar for regulated data (see
evidence-index.csv, HELP-SPHERE) as my own analytical judgment, and I am the one who reviewed and
stands behind the conditional_approve ruling and its nine conditions. I can explain and reproduce
every component of this submission, including the check logic, the decision thresholds, and the
reasoning behind each interpretive call, during the artifact check.

The candidate (Rosemary Gift Nelson) is responsible for every claim in this submission.

**Signed name:** Rosemary Gift Nelson
**UTC date/time:** 2026-08-03T03:44:12Z
