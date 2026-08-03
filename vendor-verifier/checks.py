"""
Pure, reason-coded evidence checks for the PeopleFlow vendor verification pipeline.

Every function returns a (status, code) tuple.
status is one of: "pass", "fail", "insufficient", "malformed"
code is a short machine-readable reason code.

These functions define the *interface* the published and hidden fixtures test.
They must never special-case a record_id, case_id, or any assigned-case value.
"""
from datetime import datetime


def _parse_tls(v: str) -> tuple:
    # "TLSv1.2" or "1.2" -> (1, 2)
    v = v.replace("TLSv", "").replace("TLS", "")
    parts = v.split(".")
    return (int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)


def check_tls_minimum(minimum: str, observed: str):
    if _parse_tls(observed) < _parse_tls(minimum):
        return "fail", "TLS_BELOW_MINIMUM"
    return "pass", "TLS_OK"


def check_access_mfa(mfa: bool, privileged: bool):
    if privileged and not mfa:
        return "fail", "PRIVILEGED_MFA_MISSING"
    return "pass", "MFA_OK"


def check_access_hash_chain(expected_previous_hash: str, previous_hash: str):
    if previous_hash != expected_previous_hash:
        return "fail", "HASH_CHAIN_BROKEN"
    return "pass", "HASH_CHAIN_OK"


def check_access_duplicate(event_ids: list):
    if len(event_ids) != len(set(event_ids)):
        return "malformed", "DUPLICATE_EVENT_ID"
    return "pass", "NO_DUPLICATES"


def _to_dt(s):
    if s is None:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def check_deletion_order(reported_at: str, completed_at: str):
    completed = _to_dt(completed_at)
    reported = _to_dt(reported_at)
    if completed is None:
        return "insufficient", "DELETION_COMPLETION_MISSING"
    if reported < completed:
        return "fail", "SUCCESS_BEFORE_COMPLETION"
    return "pass", "DELETION_ORDER_OK"


def check_deletion_backup(status: str, backup_purge_at):
    if status == "success" and backup_purge_at is None:
        return "insufficient", "BACKUP_PURGE_UNPROVEN"
    return "pass", "BACKUP_PURGE_OK"


def check_location_claim(claimed: str, observed: str):
    if observed != claimed:
        return "fail", "REGION_CLAIM_CONTRADICTED"
    return "pass", "REGION_CLAIM_OK"


# Assurance types treated as meeting an independent-assurance bar for subprocessors
# handling regulated / high-sensitivity data classes. A missing value, or a value that
# is present but self-attested with no independent testing, is treated the same way:
# the customer has no verifiable basis for reliance. This interpretation is recorded
# in evidence-index.csv (confidence, alternative considered) rather than hidden here.
_INSUFFICIENT_ASSURANCE_VALUES = {None, "", "self-assessment"}


def check_subprocessor_assurance(assurance, subprocessor: str):
    if assurance in _INSUFFICIENT_ASSURANCE_VALUES:
        return "insufficient", "ASSURANCE_MISSING"
    return "pass", "ASSURANCE_OK"


def check_notification_clock(clock_basis: str, customer_awareness_dependency: bool):
    if clock_basis == "vendor_confirmation" and customer_awareness_dependency:
        return "fail", "CUSTOMER_CLOCK_DELAYED"
    return "pass", "CLOCK_OK"


def check_graph_orphan(node: str, parent: str, known_nodes: set):
    if parent not in known_nodes:
        return "malformed", "ORPHAN_NODE"
    return "pass", "GRAPH_EDGE_OK"


# --- Deterministic extension: undisclosed subprocessor edge ---
# Chosen from the published extension pool: "Detect a subprocessor edge missing from
# the declared graph." A subprocessor observed operating on data (telemetry) but never
# disclosed on the customer-facing/contractual subprocessor list is a distinct failure
# from a structurally orphaned graph node: the graph is internally consistent, but it
# was never shown to the customer, which breaches the 10-day change-notice clause.
def check_subprocessor_disclosed(subprocessor_name: str, disclosed_names: set):
    if subprocessor_name not in disclosed_names:
        return "fail", "UNDISCLOSED_SUBPROCESSOR"
    return "pass", "SUBPROCESSOR_DISCLOSED"


CHECK_DISPATCH = {
    "tls.minimum": lambda i: check_tls_minimum(i["minimum"], i["observed"]),
    "access.mfa": lambda i: check_access_mfa(i["mfa"], i["privileged"]),
    "access.hash_chain": lambda i: check_access_hash_chain(i["expected_previous_hash"], i["previous_hash"]),
    "access.duplicate": lambda i: check_access_duplicate(i["event_ids"]),
    "deletion.order": lambda i: check_deletion_order(i["reported_at"], i["completed_at"]),
    "deletion.backup": lambda i: check_deletion_backup(i["status"], i["backup_purge_at"]),
    "location.claim": lambda i: check_location_claim(i["claimed"], i["observed"]),
    "subprocessor.assurance": lambda i: check_subprocessor_assurance(i["assurance"], i["subprocessor"]),
    "notification.clock": lambda i: check_notification_clock(i["clock_basis"], i["customer_awareness_dependency"]),
    "graph.orphan": lambda i: check_graph_orphan(i["node"], i["parent"], set(i.get("known_nodes", []))),
}
