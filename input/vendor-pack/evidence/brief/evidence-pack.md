# PeopleFlow Vendor Due-Diligence Pack

## Proposed service

PeopleFlow will process employee names, addresses, bank details, tax IDs,
performance notes, and support attachments for CloudScale Dynamics. Planned
launch: 20 July 2026. Contract value: USD 180,000 annually. Business owner:
Chief People Officer.

## Procurement message, 13 July 2026 08:20 WAT

"The launch announcement is approved. Please sign security off today. PeopleFlow
has SOC 2 and encryption; reopening terms will cost the quarter. If there is a
small issue, put it in the risk register after launch."

## Security message, 13 July 2026 09:05 WAT

"The audit period appears stale, the deletion answer has no evidence, and the
support subprocessor can access tickets outside the stated region. We need a
decision, not a checklist marked green because a report exists."

## SOC 2 Type II excerpt

Service organisation: PeopleFlow Inc.  
Period: 1 January 2024 to 31 December 2024  
Report issued: 28 February 2025  
Scope: production HR platform operated in AWS us-east-1  
Carve-out: subservice organisations use the carve-out method.

Exceptions:

1. CC6.2 sample: 4 of 25 terminated workforce accounts remained enabled from
   6 to 19 days after termination. Management cites manual ticket delays.
2. CC7.2 sample: alert-review evidence was absent for 7 of 40 sampled days.
   Management states reviews occurred in chat but were not retained.
3. CC8.1 sample: 3 of 20 emergency changes lacked retrospective approval within
   the required five business days.

The auditor did not qualify the opinion but states exceptions must be evaluated
by user entities in light of their use and complementary controls.

## SIG response, signed 2 July 2026

| ID | Vendor answer |
|---|---|
| IAM-04 | Access is removed within 24 hours of termination. |
| LOG-07 | Security alerts are reviewed daily and evidence retained for one year. |
| LOC-02 | Customer data remains exclusively in AWS us-east-1. |
| ENC-03 | Data is encrypted in transit and at rest using provider-managed keys. |
| DEL-05 | Customer data is deleted promptly after termination. |
| IR-08 | Customers are notified within 72 hours of confirming a breach. |

No attachments were supplied for IAM-04, LOG-07, DEL-05, or IR-08.

## DPA excerpts

- Customer data will be hosted in the United States.
- PeopleFlow may use subprocessors listed on its trust page and will give ten
  days' notice of material changes.
- On termination, PeopleFlow will delete customer data within 180 days unless
  law requires retention. Backup deletion may take an additional 90 days.
- PeopleFlow will notify the customer without undue delay and no later than 72
  hours after PeopleFlow confirms a security incident affects customer data.
- Audit assistance beyond one annual questionnaire is billable.

## Subprocessor list, updated 30 June 2026

| Provider | Location | Function | Assurance |
|---|---|---|---|
| Amazon Web Services | United States | Hosting | SOC 2 Type II |
| HelpSphere Services Ltd | Philippines | Tier-1 support with ticket attachment access | Self-assessment only |
| MailRelay BV | Netherlands | Transactional email | ISO 27001 certificate expires 30 September 2026 |

## Vendor clarification already on file

Support staff in the Philippines use a browser interface. PeopleFlow says
attachments are masked "where practical" but supplied no configuration export,
sample, or access log. Privileged support sessions are not currently recorded.
