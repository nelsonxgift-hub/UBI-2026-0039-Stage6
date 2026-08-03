# Verify the Vendor, Then Decide — UBI-2026-0039, Advanced Stage, Project 2

**Intern:** UBI-2026-0039 · **Track:** GRC · **Private assignment set:** D5
**Evidence marker:** `UBI-A6-A643A704516C`
**Vendor case:** PeopleFlow Inc. (HR platform) for CloudScale Dynamics

## Environment

- OS: Parrot OS 6.4 MATE Security Edition (VirtualBox VM on Windows host)
- Python: 3.12
- Key packages (see `.venv` after provisioning): `jsonschema==4.26.0`, `pytest==9.1.1`,
  `pyyaml`, `reportlab`

## Archive verification (resolved)

`grc-stage-6-shared-b1.tar.gz` was downloaded and hash-checked: SHA-256
`3e5e6e8f39975da3e07d1b72a54181910e97db74c0d09b43c8553381e6866973` matches the private overlay
exactly, as does the byte size (11,269 bytes). Its `evidence/brief/*.json` files were compared
structurally (`json.load` equality) against `input/*.json`: `vendor-claims.json`,
`vendor-telemetry.json`, `assurance-and-contract.json`, and `public-fixtures.json` are all
identical in content (only whitespace/indentation differs, which is not JSON-semantic). No
pipeline output changed. An early file-handling discrepancy affecting five input files was identified and resolved before analysis began.

The archive also supplied one artifact not previously seen: `evidence/common/decision-log-template.md`,
completed here as `decision-log.md` at the submission root (see brief.md: "Update the decision log
and state whether it changes the ruling, a condition, or neither" during the artifact check).

## Reproduction order

```bash
# 1. Provision
cd UBI-grc-stage6
python3 -m venv .venv && source .venv/bin/activate
pip install jsonschema pytest pyyaml reportlab

# 2. Verify raw input integrity (SHA-256 of each raw export, printed to stdout)
shasum -a 256 input/*.json

# 3. Run the full test suite (public fixtures + own fixtures + schema + pipeline +
#    graph + decision + replacement-export rehearsal)
PYTHONPATH=vendor-verifier pytest -q

# 4. Run the pipeline: writes evidence-verdicts.json and data-flow.graphml to the
#    submission root from the raw input/ exports
python3 vendor-verifier/cli.py

# 5. Regenerate the derived report artifacts from evidence-verdicts.json
python3 generate_memo.py                    # vendor-risk-memo.pdf
python3 generate_reports.py                 # contradiction-matrix.csv, evidence-index.csv,
                                              # vendor-risk-register.csv, monitoring-plan.yaml

# 6. Quarterly monitoring command (fail-closed; exit 1 if any watched code recurs)
python3 vendor-verifier/cli.py --check UNDISCLOSED_SUBPROCESSOR,REGION_CLAIM_CONTRADICTED,\
BACKUP_PURGE_UNPROVEN,CUSTOMER_CLOCK_DELAYED

# 7. Regenerate the manifest (from the submission root, excludes itself)
find . -type f ! -name manifest.sha256 -print0 | sort -z | xargs -0 shasum -a 256 > manifest.sha256
```

## What each step checks

| Step | Checkpoint |
|---|---|
| 3 | 20/20 public fixtures produce exact status+code; schema rejects broken/malformed/wrong-scope inputs; `insufficient` never promoted to `pass`; pipeline is deterministic across repeated runs |
| 4 | Every verdict carries an exact artifact + locator; graph accounts for every declared and telemetry-observed subprocessor edge with 0 cycle/orphan findings |
| 6 | Demonstrates the "executable quarterly verification command" required by the decision rubric — this is a real subprocess exit code, not prose |

## Directory map

```
vendor-verifier/   checks.py, loaders.py, pipeline.py, graph_builder.py, decision.py, cli.py
schemas/           JSON Schema for each of the 3 raw export types + the verdict shape
tests/             public-fixture conformance, own edge-case fixtures, schema tests,
                   pipeline/graph/decision integration tests, replacement-export rehearsal
input/             raw, read-only (chmod 444) copies of the 3 assigned exports + public fixtures
evidence-verdicts.json / data-flow.graphml   generated — do not hand-edit
vendor-risk-memo.pdf, vendor-risk-register.csv, contradiction-matrix.csv,
contract-redlines.md, monitoring-plan.yaml, evidence-index.csv   generated from evidence-verdicts.json
```

## Known limitations

- `subprocessor.assurance` treats a present-but-self-attested value ("self-assessment") the same
  as a missing one. This is a documented interpretive judgment (see `evidence-index.csv`
  "alternative_considered" column for HELP-SPHERE), not a schema-level fact.
- The undisclosed-subprocessor check joins telemetry to the DPA list on name/id only; no other
  join key (e.g. IP range, contract exhibit number) was supplied in the pack.
