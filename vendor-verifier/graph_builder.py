"""
Builds the subprocessor / data-flow graph from both the DPA-disclosed subprocessor list
and the telemetry-observed subprocessor list, and validates it for cycles, orphans, and
missing owners before it is trusted by the decision engine.
"""
import xml.etree.ElementTree as ET
import checks


def build_graph(assurance_contract: dict, telemetry: dict):
    nodes = {}   # id -> attrs
    edges = []   # (src, dst, attrs)

    nodes["PeopleFlow"] = {"kind": "vendor", "role": "processor", "region": "n/a", "disclosed": "true"}
    nodes["CloudScale-Dynamics"] = {"kind": "customer", "role": "controller", "region": "n/a", "disclosed": "true"}
    edges.append(("CloudScale-Dynamics", "PeopleFlow", {"relationship": "controller_to_processor"}))

    # DPA-disclosed subprocessors
    disclosed_ids = set()
    for sp in assurance_contract["subprocessors"]:
        nodes[sp["id"]] = {
            "kind": "subprocessor_disclosed",
            "role": sp["function"],
            "region": sp["location"],
            "assurance": str(sp.get("assurance")),
            "disclosed": "true",
        }
        edges.append(("PeopleFlow", sp["id"], {"relationship": "dpa_disclosed_subprocessor"}))
        disclosed_ids.add(sp["id"])
        for dc in sp["data_classes"]:
            dc_node = f"data:{dc}"
            nodes.setdefault(dc_node, {"kind": "data_class", "role": "n/a", "region": "n/a", "disclosed": "n/a"})
            edges.append((sp["id"], dc_node, {"relationship": "processes"}))

    # Telemetry-observed subprocessors (may or may not be disclosed)
    disclosed_names = {sp["id"] for sp in assurance_contract["subprocessors"]}
    telemetry_ids = {sp["id"]: sp for sp in telemetry["subprocessors"]}
    name_to_id = {sp["name"]: sp["id"] for sp in telemetry["subprocessors"]}

    for sp in telemetry["subprocessors"]:
        status, code = checks.check_subprocessor_disclosed(sp["name"], disclosed_names)
        nodes[sp["id"]] = {
            "kind": "subprocessor_observed",
            "role": "n/a",
            "region": sp["region"],
            "assurance": "unknown",
            "disclosed": "false" if status == "fail" else "true",
        }
        parent_id = "PeopleFlow" if sp["parent"] == "PeopleFlow" else name_to_id.get(sp["parent"], sp["parent"])
        edges.append((parent_id, sp["id"], {"relationship": "telemetry_observed_subprocessor"}))
        for dc in sp["data_classes"]:
            dc_node = f"data:{dc}"
            nodes.setdefault(dc_node, {"kind": "data_class", "role": "n/a", "region": "n/a", "disclosed": "n/a"})
            edges.append((sp["id"], dc_node, {"relationship": "processes"}))

    return nodes, edges


def validate_graph(nodes: dict, edges: list):
    """Returns a list of finding dicts: cycle, orphan (dangling edge endpoint), missing_owner."""
    findings = []
    node_ids = set(nodes.keys())

    # Orphan / dangling edges: either endpoint not a declared node
    for src, dst, attrs in edges:
        if src not in node_ids:
            findings.append({"type": "orphan", "detail": f"edge source '{src}' has no node"})
        if dst not in node_ids:
            findings.append({"type": "orphan", "detail": f"edge target '{dst}' has no node"})

    # Missing owner: every subprocessor node must be reachable from PeopleFlow
    adjacency = {}
    for src, dst, _ in edges:
        adjacency.setdefault(src, []).append(dst)
    reachable = set()
    stack = ["PeopleFlow"]
    while stack:
        cur = stack.pop()
        if cur in reachable:
            continue
        reachable.add(cur)
        stack.extend(adjacency.get(cur, []))
    for nid, attrs in nodes.items():
        if attrs["kind"].startswith("subprocessor") and nid not in reachable:
            findings.append({"type": "missing_owner", "detail": f"subprocessor '{nid}' unreachable from PeopleFlow"})

    # Cycle detection (DFS)
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in node_ids}

    def dfs(u, path):
        color[u] = GRAY
        path.append(u)
        for v in adjacency.get(u, []):
            if v not in color:
                continue
            if color[v] == GRAY:
                findings.append({"type": "cycle", "detail": " -> ".join(path + [v])})
            elif color[v] == WHITE:
                dfs(v, path)
        path.pop()
        color[u] = BLACK

    for n in list(node_ids):
        if color[n] == WHITE:
            dfs(n, [])

    return findings


def to_graphml(nodes: dict, edges: list) -> str:
    ns = "http://graphml.graphdrawing.org/xmlns"
    ET.register_namespace("", ns)
    graphml = ET.Element(f"{{{ns}}}graphml")

    keys = [
        ("d_kind", "node", "kind", "string"),
        ("d_role", "node", "role", "string"),
        ("d_region", "node", "region", "string"),
        ("d_disclosed", "node", "disclosed", "string"),
        ("d_rel", "edge", "relationship", "string"),
    ]
    for kid, target, name, ktype in keys:
        k = ET.SubElement(graphml, f"{{{ns}}}key", id=kid, **{"for": target, "attr.name": name, "attr.type": ktype})

    graph = ET.SubElement(graphml, f"{{{ns}}}graph", id="vendor-data-flow", edgedefault="directed")

    for nid, attrs in nodes.items():
        n = ET.SubElement(graph, f"{{{ns}}}node", id=nid)
        for kid, target, name, _ in keys:
            if target == "node" and name in attrs:
                d = ET.SubElement(n, f"{{{ns}}}data", key=kid)
                d.text = str(attrs[name])

    for i, (src, dst, attrs) in enumerate(edges):
        e = ET.SubElement(graph, f"{{{ns}}}edge", id=f"e{i}", source=src, target=dst)
        for kid, target, name, _ in keys:
            if target == "edge" and name in attrs:
                d = ET.SubElement(e, f"{{{ns}}}data", key=kid)
                d.text = str(attrs[name])

    return "<?xml version='1.0' encoding='UTF-8'?>\n" + ET.tostring(graphml, encoding="unicode")
