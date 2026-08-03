"""
Rehearses the mandatory artifact check: replace one export in input/ through the
published interface (same schema, different values) and confirm the pipeline picks it
up and produces different, still-locator-complete verdicts -- with zero edits to
checks.py, pipeline.py, or graph_builder.py. This test uses a temp copy of input/ and
monkeypatches loaders.INPUT_DIR; it never edits the assigned files in place.
"""
import copy
import json
import os
import shutil
from pathlib import Path

import loaders
import pipeline

ROOT = Path(__file__).resolve().parent.parent


def test_replacement_telemetry_export_flows_through_without_validator_edits(tmp_path, monkeypatch):
    # Copy the real input/ into a scratch dir
    scratch = tmp_path / "input"
    shutil.copytree(ROOT / "input", scratch)
    # copytree preserves the source's file mode; real evidence is locked (chmod 444), so
    # the scratch copy needs to be made writable before this drill can edit it
    for root, dirs, files in os.walk(scratch):
        for name in files:
            os.chmod(os.path.join(root, name), 0o644)

    telemetry = json.loads((scratch / "vendor-telemetry.json").read_text())
    replaced = copy.deepcopy(telemetry)
    # Same schema, different identifiers/values/ordering/edge condition:
    # fix the hash chain break, but introduce a NEW below-minimum TLS endpoint instead.
    for ev in replaced["privileged_access"]:
        if ev["event_id"] == "PA-003":
            ev["previous_hash"] = "98abc"  # now correctly chains
    replaced["tls"]["observations"].append(
        {"endpoint": "admin.peopleflow.invalid", "port": 443, "protocol": "TLSv1.1",
         "observed_at": "2026-07-14T09:00:00Z"}
    )
    (scratch / "vendor-telemetry.json").write_text(json.dumps(replaced, indent=2))
    # keep the file read-only-in-spirit for the rest of this test: no further writes
    (scratch / "vendor-telemetry.json").chmod(0o444)

    monkeypatch.setattr(loaders, "INPUT_DIR", scratch)

    result = pipeline.run_pipeline()
    hash_findings = [v for v in result["verdicts"] if v["check_id"] == "access.hash_chain"]
    assert all(v["status"] == "pass" for v in hash_findings), "replacement export should have fixed the chain"

    tls_findings = [v for v in result["verdicts"] if v["check_id"] == "tls.minimum"]
    assert any(
        v["code"] == "TLS_BELOW_MINIMUM" and "admin.peopleflow.invalid" in v["locator"]
        for v in tls_findings
    ), "new below-minimum endpoint in the replacement export must be caught"

    # Every verdict still carries a complete, exact locator -- no validator-source edit needed
    for v in result["verdicts"]:
        assert v["locator"]
