# GRC Advanced 2: Vendor Risk Decision

## Window and scoring

Monday 09:00 WAT to Friday 18:10 WAT. One revision. 100 points: contradiction detection 25, exception and
evidence judgment 20, risk analysis 20, decision/conditions 20, redlines and
communication 15.

## Required decision

Rule `approve`, `conditional approve`, `defer`, or `reject`. Procurement's date
is a pressure, not a control. Every condition must have an owner, due date,
evidence of closure, and consequence if unmet. Identify risks that remain even
after the conditions are met.

Cross-check the SIG against the SOC 2 excerpt, DPA, subprocessors, and current
date. Analyze audit exceptions for scope and impact. Separate facts from legal
assumptions. Do not treat a SOC 2 report as a certification or proof that every
control operated without exception.

The artifact check supplies one vendor response. Update the decision log and
state whether it changes the ruling, a condition, or neither.

## Verification-engine build

Build a typed ingestion and validation pipeline for the supplied SIG, SOC 2
exceptions, DPA, subprocessor graph, access logs, deletion telemetry, and
notification records. Publish the input/output JSON schemas. Preserve record
locators and classify each check as `pass`, `fail`, `insufficient`, or
`malformed`; `insufficient` must never be promoted to pass.

The exports contain stale records, duplicate events, one broken hash chain,
inconsistent region labels, and a deletion job that reports success before its
completion event. Validate graph cycles/orphans and every subprocessor/data-class
edge. `make test` must pass 20 public fixtures. Ten hidden fixtures must produce
the exact sealed result codes and locators. During the mandatory artifact check,
staff replace one export and require the pipeline, graph, conditions, and memo to
regenerate within 45 minutes without validator-source edits.

## Mission interface and handoff

- **You receive:** signed vendor claims, assurance/contract facts, telemetry, the evidence graph context, and candidate-specific decision constraints.
- **You build:** adapters and validators that consume the Stage 5 evidence model and emit contradictions, sufficiency codes, graph findings, conditions, and a decision memo.
- **You prove:** every claim disposition has contrary/supporting evidence locators and no missing evidence is silently treated as conforming.
- **You hand forward:** the verified evidence graph, open conditions, owners, deadlines, and evidence grades for Stage 7 audit.
