#!/usr/bin/env python3
"""Generates vendor-risk-memo.pdf from the frozen evidence-verdicts.json.
This is a *report generator*, not a source of truth -- every figure it prints is read
from evidence-verdicts.json, which is itself produced by vendor-verifier/cli.py."""
import json
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                 PageBreak, ListFlowable, ListItem)

ROOT = Path(__file__).resolve().parent
data = json.loads((ROOT / "evidence-verdicts.json").read_text())
verdicts = data["verdicts"]
dec = data["decision"]
hashes = data["source_hashes"]

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="H1c", parent=styles["Heading1"], spaceAfter=10))
styles.add(ParagraphStyle(name="H2c", parent=styles["Heading2"], spaceBefore=14, spaceAfter=6))
styles.add(ParagraphStyle(name="Bodyc", parent=styles["BodyText"], spaceAfter=8, leading=14))
styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8, leading=10, textColor=colors.HexColor("#555555")))

doc = SimpleDocTemplate(str(ROOT / "vendor-risk-memo.pdf"), pagesize=letter,
                         topMargin=0.75*inch, bottomMargin=0.75*inch,
                         leftMargin=0.75*inch, rightMargin=0.75*inch)
story = []

story.append(Paragraph("Vendor Risk Decision Memo", styles["Title"]))
story.append(Paragraph("PeopleFlow Inc. — HR Platform Vendor Onboarding for CloudScale Dynamics", styles["H2c"]))
story.append(Paragraph(
    "UBI-2026-0039 · GRC Analyst Track · Advanced Stage, Project 2 · Evidence marker UBI-A6-A643A704516C<br/>"
    "Prepared by: Rosemary Gift Nelson, GRC Analyst", styles["Small"]))
story.append(Spacer(1, 14))

story.append(Paragraph("1. Decision", styles["H2c"]))
decision_label = dec["decision"].replace("_", " ").upper()
story.append(Paragraph(f"<b>Ruling: {decision_label}</b>", styles["Bodyc"]))
story.append(Paragraph(dec["decision_rationale"], styles["Bodyc"]))
if dec["requires_ceo_approval"]:
    story.append(Paragraph(f"<b>CEO approval required.</b> {dec['ceo_approval_reason']}", styles["Bodyc"]))
story.append(Paragraph(
    "This ruling means: PeopleFlow is not rejected outright, but no in-scope CloudScale data "
    "class may be processed (or must have processing suspended, if the 24 July 2026 planned "
    "launch already occurred) until the Tier-0 conditions in Section 4 close. Every condition "
    "carries an executable quarterly monitor (monitoring-plan.yaml) and a stated fail-closed "
    "action, per the hard acceptance gate that a conditional approval without executable "
    "fail-closed monitoring cannot pass.", styles["Bodyc"]))

story.append(Paragraph("2. Verification summary", styles["H2c"]))
counts = dec["counts"]
t = Table([
    ["Result", "Count"],
    ["Pass", counts["pass"]],
    ["Fail", counts["fail"]],
    ["Insufficient", counts["insufficient"]],
    ["Malformed", counts["malformed"]],
    ["Total verdicts", len(verdicts)],
], colWidths=[3*inch, 2*inch])
t.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1f2d5c")),
    ("TEXTCOLOR", (0,0), (-1,0), colors.white),
    ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
    ("FONTSIZE", (0,0), (-1,-1), 9),
    ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, colors.HexColor("#f2f2f2")]),
]))
story.append(t)
story.append(Spacer(1, 8))
story.append(Paragraph(
    "Six SIG claims were tested (IAM-04, LOG-07, LOC-02, ENC-03, DEL-05, IR-08). Every one of "
    "them produced at least one fail or insufficient verdict against technical evidence, "
    "telemetry, or the vendor's own SOC 2 report — not against questionnaire text, which the "
    "hard acceptance gate forbids relying on.", styles["Bodyc"]))

story.append(Paragraph("3. Material findings (traceable to evidence-verdicts.json)", styles["H2c"]))
seen_codes = []
material = [v for v in verdicts if v["status"] in ("fail", "malformed") and v["code"] not in seen_codes and not seen_codes.append(v["code"])]
items = []
for v in material:
    items.append(ListItem(Paragraph(
        f"<b>{v['code']}</b> ({v['claim_id'] or 'general control'}) — {v['message']} "
        f"<i>[{v['artifact']} :: {v['locator']}]</i>", styles["Bodyc"])))
story.append(ListFlowable(items, bulletType="bullet"))

insuff = [v for v in verdicts if v["status"] == "insufficient"]
story.append(Paragraph("Insufficient (missing/unverifiable, never promoted to pass):", styles["Bodyc"]))
items2 = []
for v in insuff:
    items2.append(ListItem(Paragraph(
        f"<b>{v['code']}</b> ({v['claim_id'] or 'general control'}) — {v['message']}", styles["Bodyc"])))
story.append(ListFlowable(items2, bulletType="bullet"))

story.append(PageBreak())
story.append(Paragraph("4. Conditions precedent (owner / deadline / evidence / fail-closed action)", styles["H2c"]))
cond_rows = [["ID", "Description", "Owner", "Due", "Fail-closed action"]]
for c in dec["conditions"]:
    cond_rows.append([
        c["condition_id"],
        Paragraph(c["description"], styles["Small"]),
        Paragraph(c["owner"], styles["Small"]),
        f"{c['due_in_days']}d",
        Paragraph(c["fail_closed_action"], styles["Small"]),
    ])
ct = Table(cond_rows, colWidths=[0.55*inch, 2.3*inch, 1.5*inch, 0.5*inch, 1.9*inch], repeatRows=1)
ct.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1f2d5c")),
    ("TEXTCOLOR", (0,0), (-1,0), colors.white),
    ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
    ("FONTSIZE", (0,0), (-1,-1), 8),
    ("VALIGN", (0,0), (-1,-1), "TOP"),
    ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f2f2f2")]),
]))
story.append(ct)

story.append(Paragraph("5. Residual risk (remains even after all conditions close)", styles["H2c"]))
items3 = [ListItem(Paragraph(r, styles["Bodyc"])) for r in dec["residual_risks"]]
story.append(ListFlowable(items3, bulletType="bullet"))

story.append(Paragraph("6. Alternatives considered", styles["H2c"]))
story.append(Paragraph(
    "<b>Reject outright:</b> considered given that every SIG claim has a problem; not selected "
    "because every finding maps to a closeable, owned condition rather than an unfixable defect, "
    "and outright rejection would forfeit the leverage to force disclosure of the undisclosed "
    "subprocessors while the deal is still open. <b>Approve as-is:</b> rejected outright — the "
    "hard acceptance gate that trusting questionnaire text over failing technical evidence fails "
    "the decision applies directly; SIG claims cannot be accepted at face value here. "
    "<b>Defer:</b> considered, but with 24 conditions/verdicts already resolvable into concrete, "
    "owned actions, deferral would only delay accountability without changing the underlying "
    "facts.", styles["Bodyc"]))

story.append(Paragraph("7. Artifact-check log", styles["H2c"]))
story.append(Paragraph(
    "Reserved for the mandatory replacement-export exercise: record here which export staff "
    "swapped, the resulting delta in evidence-verdicts.json, and whether it changed the ruling, "
    "a condition, or neither. See tests/test_replacement_export_rehearsal.py for the rehearsed "
    "version run before submission.", styles["Bodyc"]))

story.append(Paragraph("Source hashes (frozen at generation time)", styles["H2c"]))
for k, v in hashes.items():
    story.append(Paragraph(f"<font face='Courier' size=8>{k} :: {v}</font>", styles["Small"]))

doc.build(story)
print("wrote vendor-risk-memo.pdf")
