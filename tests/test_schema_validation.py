import copy
import json
from pathlib import Path

import jsonschema
import pytest
from loaders import load_json, SCHEMA_DIR, INPUT_DIR

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("input_file,schema_file", [
    ("vendor-claims.json", "sig-claims.schema.json"),
    ("vendor-telemetry.json", "telemetry.schema.json"),
    ("assurance-and-contract.json", "assurance-contract.schema.json"),
])
def test_supplied_exports_are_schema_valid(input_file, schema_file):
    instance = load_json(INPUT_DIR / input_file)
    schema = load_json(SCHEMA_DIR / schema_file)
    jsonschema.validate(instance=instance, schema=schema)  # raises on failure


def test_missing_required_field_is_rejected():
    instance = load_json(INPUT_DIR / "vendor-telemetry.json")
    schema = load_json(SCHEMA_DIR / "telemetry.schema.json")
    broken = copy.deepcopy(instance)
    del broken["deletion_jobs"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=broken, schema=schema)


def test_wrong_type_is_rejected():
    instance = load_json(INPUT_DIR / "vendor-claims.json")
    schema = load_json(SCHEMA_DIR / "sig-claims.schema.json")
    broken = copy.deepcopy(instance)
    broken["claims"][0]["evidence_supplied"] = "yes"  # should be boolean
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=broken, schema=schema)


def test_malformed_tls_protocol_string_is_rejected():
    instance = load_json(INPUT_DIR / "vendor-telemetry.json")
    schema = load_json(SCHEMA_DIR / "telemetry.schema.json")
    broken = copy.deepcopy(instance)
    broken["tls"]["observations"][0]["protocol"] = "not-a-version"  # wrong scope/format
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=broken, schema=schema)


def test_stale_date_still_schema_valid_but_flagged_by_business_logic():
    """A schema cannot detect staleness by itself -- that's a business-logic check, not a
    type check. This test documents the boundary: the SOC 2 export with an issued_at over
    a year old is schema-valid; staleness is asserted separately in test_pipeline.py via
    the AUDIT_EXCEPTION_CONTRADICTS_CLAIM / decision-engine path, consistent with the
    submission contract's evidence-standard requirement to separate 'what the artifact
    proves' from 'what it does not prove'."""
    instance = load_json(INPUT_DIR / "assurance-and-contract.json")
    schema = load_json(SCHEMA_DIR / "assurance-contract.schema.json")
    jsonschema.validate(instance=instance, schema=schema)
    assert instance["assurance_report"]["issued_at"] == "2025-02-28"
