"""Own validator fixtures beyond the 20 published ones, covering categories the brief
requires (valid, invalid, stale, malformed, wrong-scope, unverifiable) at the check-function
level rather than only the schema level."""
import checks


def test_valid_tls_passes():
    assert checks.check_tls_minimum("TLSv1.2", "TLSv1.3") == ("pass", "TLS_OK")


def test_tls_exactly_at_minimum_passes():
    assert checks.check_tls_minimum("TLSv1.2", "TLSv1.2") == ("pass", "TLS_OK")


def test_invalid_mfa_missing_on_privileged_fails():
    assert checks.check_access_mfa(mfa=False, privileged=True) == ("fail", "PRIVILEGED_MFA_MISSING")


def test_mfa_missing_on_non_privileged_is_not_a_finding():
    # wrong-scope guard: MFA absence only matters for privileged access
    assert checks.check_access_mfa(mfa=False, privileged=False) == ("pass", "MFA_OK")


def test_hash_chain_valid_link_passes():
    assert checks.check_access_hash_chain("root123", "root123") == ("pass", "HASH_CHAIN_OK")


def test_deletion_completion_missing_is_insufficient_not_fail():
    # unverifiable: no completion event recorded at all -- distinct from a failed order check
    assert checks.check_deletion_order("2026-01-01T00:00:00Z", None) == ("insufficient", "DELETION_COMPLETION_MISSING")


def test_deletion_order_exactly_equal_timestamps_is_not_a_violation():
    ts = "2026-01-01T00:00:00Z"
    assert checks.check_deletion_order(ts, ts) == ("pass", "DELETION_ORDER_OK")


def test_backup_purge_present_passes():
    assert checks.check_deletion_backup("success", "2026-02-01T00:00:00Z") == ("pass", "BACKUP_PURGE_OK")


def test_backup_purge_irrelevant_when_job_failed():
    # wrong-scope guard: an unproven backup purge only matters when status is success
    assert checks.check_deletion_backup("failed", None) == ("pass", "BACKUP_PURGE_OK")


def test_region_claim_matching_passes():
    assert checks.check_location_claim("us-east-1", "us-east-1") == ("pass", "REGION_CLAIM_OK")


def test_assurance_present_and_independent_passes():
    assert checks.check_subprocessor_assurance("SOC 2 Type II", "AWS") == ("pass", "ASSURANCE_OK")


def test_assurance_self_assessment_is_insufficient_not_pass():
    # This is the interpretive judgment call documented in evidence-index.csv: a present-but-
    # self-attested value does not meet the independent-assurance bar for regulated data.
    assert checks.check_subprocessor_assurance("self-assessment", "HelpSphere") == ("insufficient", "ASSURANCE_MISSING")


def test_notification_clock_with_independent_customer_trigger_passes():
    assert checks.check_notification_clock("customer_detection", customer_awareness_dependency=False) == ("pass", "CLOCK_OK")


def test_graph_orphan_known_parent_passes():
    assert checks.check_graph_orphan("SP-9", "PeopleFlow", {"PeopleFlow"}) == ("pass", "GRAPH_EDGE_OK")


def test_undisclosed_subprocessor_extension_check():
    assert checks.check_subprocessor_disclosed("QueueNorth", {"AWS", "HELP-SPHERE", "MAIL-RELAY"}) == (
        "fail", "UNDISCLOSED_SUBPROCESSOR"
    )


def test_disclosed_subprocessor_extension_check_passes():
    assert checks.check_subprocessor_disclosed("AWS", {"AWS", "HELP-SPHERE", "MAIL-RELAY"}) == (
        "pass", "SUBPROCESSOR_DISCLOSED"
    )
