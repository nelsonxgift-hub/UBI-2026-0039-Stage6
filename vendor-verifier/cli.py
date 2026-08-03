#!/usr/bin/env python3
"""
Entry point: python3 vendor-verifier/cli.py
Runs the full pipeline against input/, writes evidence-verdicts.json and
data-flow.graphml to the submission root, and prints a summary.
Never edited by the artifact-check replacement export; only input/ changes.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pipeline
import graph_builder
import decision as decision_mod
from loaders import load_assurance_contract, load_telemetry

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description="PeopleFlow evidence-verification pipeline")
    parser.add_argument(
        "--check", metavar="CODE1,CODE2",
        help="Quarterly monitoring mode: run the pipeline, then exit 1 (fail-closed) if any "
             "of the given comma-separated result codes are present among the fresh verdicts. "
             "Exits 0 only if none are present. Does not write evidence-verdicts.json in this mode.",
    )
    args = parser.parse_args()

    result = pipeline.run_pipeline()
    verdicts = result["verdicts"]

    if args.check:
        watch_codes = set(args.check.split(","))
        hits = [v for v in verdicts if v["code"] in watch_codes]
        if hits:
            print(f"MONITOR FAIL-CLOSED: {len(hits)} matching finding(s) for codes {sorted(watch_codes)}:")
            for h in hits:
                print(f"  - {h['check_id']} {h['code']} :: {h['locator']}")
            sys.exit(1)
        print(f"MONITOR OK: no occurrences of {sorted(watch_codes)} in current verdicts.")
        sys.exit(0)

    ac, _, _ = load_assurance_contract()
    tel, _, _ = load_telemetry()
    nodes, edges = graph_builder.build_graph(ac, tel)
    graph_findings = graph_builder.validate_graph(nodes, edges)
    graphml = graph_builder.to_graphml(nodes, edges)

    contract_value = 180000  # from due-diligence pack: "Contract value: USD 180,000 annually"
    dec = decision_mod.summarize(verdicts, graph_findings, contract_value)

    out = {
        "pipeline_version": "1.0",
        "source_hashes": result["source_hashes"],
        "verdicts": verdicts,
        "graph_findings": graph_findings,
        "decision": dec,
    }

    (ROOT / "evidence-verdicts.json").write_text(json.dumps(out, indent=2, sort_keys=False))
    (ROOT / "data-flow.graphml").write_text(graphml)

    print(f"Wrote {len(verdicts)} verdicts.")
    print(f"  pass={dec['counts']['pass']} fail={dec['counts']['fail']} "
          f"insufficient={dec['counts']['insufficient']} malformed={dec['counts']['malformed']}")
    print(f"Graph: {len(nodes)} nodes, {len(edges)} edges, {len(graph_findings)} findings")
    print(f"Decision: {dec['decision']} (CEO approval required: {dec['requires_ceo_approval']})")


if __name__ == "__main__":
    main()
