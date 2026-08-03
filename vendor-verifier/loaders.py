"""Load and JSON-Schema-validate the three raw vendor exports."""
import json
import hashlib
from pathlib import Path

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None

ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "input"
SCHEMA_DIR = ROOT / "schemas"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate(instance: dict, schema_path: Path):
    schema = load_json(schema_path)
    if jsonschema is None:
        raise RuntimeError("jsonschema package is required: pip install jsonschema --break-system-packages")
    jsonschema.validate(instance=instance, schema=schema)


def load_sig_claims():
    p = INPUT_DIR / "vendor-claims.json"
    data = load_json(p)
    validate(data, SCHEMA_DIR / "sig-claims.schema.json")
    return data, sha256_of(p), str(p)


def load_telemetry():
    p = INPUT_DIR / "vendor-telemetry.json"
    data = load_json(p)
    validate(data, SCHEMA_DIR / "telemetry.schema.json")
    return data, sha256_of(p), str(p)


def load_assurance_contract():
    p = INPUT_DIR / "assurance-and-contract.json"
    data = load_json(p)
    validate(data, SCHEMA_DIR / "assurance-contract.schema.json")
    return data, sha256_of(p), str(p)


def load_public_fixtures():
    p = INPUT_DIR / "public-fixtures.json"
    return load_json(p), sha256_of(p), str(p)
