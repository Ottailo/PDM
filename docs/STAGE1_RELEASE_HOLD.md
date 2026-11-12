# Stage 1 commercial release hold

Current work is a local implementation, not released software. This report distinguishes blockers from roadmap features. Real PostgreSQL/API/SMTP/scanner and core browser gates have executed; exact final counts are in TASK_CHECKLIST.md. A subsequent independent read-only review completed on2026-11-11; it identified staff-offboarding,upload quota and auth lock-order blockers plus an unverified parser containment gate. Findings and closure criteria are in docs/RELEASE_GATES.md. No remediation or production security sign-off yet.

## Release requires evidence
- Fresh PostgreSQL migrations, authoritative tenant/role constraints and complete identity recovery/MFA/session tests.
- Real human work-order completion/history/export and authenticated private manuals.
- Fresh frontend compile/type/lint/unit and browser workflow proof on phone/keyboard.
- Worker crash recovery, actual private document scanning/parser failure controls, backup restoration.
- Startup/environment/secret audit plus owner-approved credential rotation if needed.

## External approvals still needed
Production hosting and data region/storage/email service costs; release/push/deployment; legal/privacy and support owner/scope; real customer onboarding; data retention/export/deletion and incident response. No sending invitations to actual people or production emails during tests.

## Not claimed by Stage 1
Hardware commissioning, predictive failure accuracy/RUL, AI advice, spare inventory, saved layouts/MCP/offline completion, native installers, regulatory certification or measured downtime savings. These cannot be marketed from the local test fixtures.

## Customer-safe language
Use 'maintenance workspace' and 'not connected' for registered assets without telemetry. State actual product scope, supported devices/protocols only after testing, and contractual support arrangements. No fake customer logos, endorsements, funding, benchmark, sensor history or 'system nominal' counters.
