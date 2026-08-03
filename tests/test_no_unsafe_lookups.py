"""
Structural (static-analysis) safety net for the bug class this review caught twice:
a bare `next(generator)` with no default crashes with an unhandled StopIteration the
moment the thing it's searching for isn't present under that exact literal key --
which is exactly what happens when a replacement export renames or removes a record.

This test does not re-run the pipeline; it inspects the source of the modules that
process live evidence and fails if it finds a `next(...)` call with no `None`/`default=`
fallback. It exists so a THIRD instance of this same pattern, anywhere in
vendor-verifier/, is caught by CI before a reviewer has to find it by hand a third time.
"""
from __future__ import annotations
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCANNED_MODULES = [
    ROOT / "vendor-verifier" / "pipeline.py",
    ROOT / "vendor-verifier" / "decision.py",
    ROOT / "vendor-verifier" / "graph_builder.py",
    ROOT / "vendor-verifier" / "checks.py",
    ROOT / "vendor-verifier" / "loaders.py",
]


def _bare_next_calls(tree: ast.AST):
    """Yield (lineno, col) for every `next(x)` call with exactly one positional
    argument and no default -- the pattern that raises StopIteration if the
    generator/iterator is empty."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "next":
            if len(node.args) == 1 and not node.keywords:
                yield node.lineno, node.col_offset


def test_no_bare_next_calls_without_a_default():
    offenders = []
    for path in SCANNED_MODULES:
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(), filename=str(path))
        for lineno, col in _bare_next_calls(tree):
            offenders.append(f"{path.relative_to(ROOT)}:{lineno}:{col}")
    assert not offenders, (
        "Found next(...) call(s) with no default fallback -- these raise an unhandled "
        "StopIteration (crashing the whole pipeline) the moment a replacement export "
        "renames or removes the record being searched for. Use next(iter, None) (or "
        "equivalent) and handle the None case explicitly. Offending locations:\n  "
        + "\n  ".join(offenders)
    )


def test_no_literal_case_specific_identifiers_as_dict_lookup_keys_or_equality_targets():
    """
    A softer, advisory-strength check: flag literal strings that look like this
    case's specific data values (subprocessor names, job ids, event ids, a specific
    SOC 2 exception id) appearing as an equality-comparison target or dict-lookup key
    in the check/decision/pipeline modules. This does NOT flag stable interface
    vocabulary (claim ids like 'IAM-04', check ids like 'tls.minimum', status strings
    like 'pass') -- those are part of the fixed schema, not per-case observed facts.
    """
    suspicious_literals = {
        "QueueNorth", "AssistWorks", "ArchiveLane",  # subprocessor names
        "DEL-710", "PA-002",                          # specific record ids
        "EX-CC7.2", "EX-CC6.2", "EX-CC8.1",           # specific exception ids
    }
    offenders = []
    for path in SCANNED_MODULES:
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                for cmp_node in [node.left] + list(node.comparators):
                    if isinstance(cmp_node, ast.Constant) and cmp_node.value in suspicious_literals:
                        offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}: comparison against {cmp_node.value!r}")
    assert not offenders, (
        "Found case-specific observed values (not stable interface vocabulary) used as "
        "equality-comparison targets. These are assigned-case facts that can differ on a "
        "replacement export, not fixed schema identifiers, and must not drive control flow. "
        "Offending locations:\n  " + "\n  ".join(offenders)
    )
