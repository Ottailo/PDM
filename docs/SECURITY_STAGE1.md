# Stage 1 security/release gate

Implementation and tests in progress. This is not a security certification.

## Scope
Browser identity and tenant API, uploaded manuals, worker/email and local service configurations. Physical control, AI, remote MCP and billing are absent. The old demo routes must not be mounted in the customer runtime.

## Controls to prove
Server-scoped membership/resource access; composite tenant references; owner/admin MFA; revocable sessions; single-use expiring action/recovery tokens; CSRF and rate limits; strong startup secrets and encrypted MFA data; no password/token leaks. Role hiding is not authorization. Verify foreign IDs on details, jobs, assignees, locations, manual pages/downloads and exports.

Uploads quarantined, size/MIME/signature/page validation, actual ClamAV scan, bounded subprocess parse, no unsafe deserialization, no PDF active-content delivery inline without sanitization. Text reader/download access authorized after ready. Scan failure means unavailable, not ready.

Durable jobs must claim atomically with leases, recover crashes and revalidate deletion/access. Notification delivery may be at-least-once; no claim of guaranteed human receipt or exactly-once email. Tests capture mail, not send to real people.

## Known external blockers
The old public deployment remains unchanged. Existing source/history contained a credential value: value removed from new reports/runtime, but validity and owner-approved rotation remain unverified. No provider/production secrets are printed. No customer security claim until independent review and actual deployment configuration, incident/support ownership and restoration evidence.

## Local infra proof
2026-11-11: isolated localhost PostgreSQL ready, test DB created; Mailpit inbox responds; ClamAV clean/EICAR negative control passed exit0. These do not prove tenant API/document pipeline until integration tests run.

## Release boundaries
No production commit/push/deploy, secret rotation, outreach or paid AI without explicit authorization. No compliance badges, invented model accuracy, fake live data, or claimed equipment safety. Lawful data handling, legal review and supported operations are release prerequisites.
