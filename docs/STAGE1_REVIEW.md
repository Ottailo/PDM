# Stage 1 source/behavior review

Status: local acceptance review, not independent security certification or commercial release.

## Confirmed and corrected
- Password login/MFA reauthentication trimmed credentials although registration preserved them. Regression observed HTTP401, corrected non-trimming credential validator; full rerun passed22 before additional checks.
- Job/manual machine selects and machine location/job assignee edit selects lost context while asynchronous options loaded. Browser native validation exposed blank selection. Controlled selects preserve context; two async-option unit cases passed; actual machine→job browser journey passed.
- Invitation success was hidden by token preview error after consumption/refetch. Preserved failing persona test, changed success precedence; full persona test passed exit0,58.7s.
- SMTP STARTTLS default Python context did not verify certificates. Explicit ssl.create_default_context now supplied; regression checks certificate/hostname verification in final24passed backend suite.
- Optional legacy WSGI wrapper printed boot/request tracebacks. It now emits generic unavailable JSON without secret/error trace; regression verifies. Legacy run.py redirects secure factory with no simulator/training.
- Backup comparison originally used different snapshots during concurrent writes. Exported PostgreSQL repeatable-read snapshot now governs dump and inventory;24-table restore passed.
- Concurrent final backend suites conflicted through shared disposable fixture cleanup. Exclusive PostgreSQL advisory suite lock added; final serial run passed24tests exit0. No pilot/customer DB fixture cleanup allowed.

## Verified scope so far
Tenant API reads/relations, roles, exact workflow transitions, CSRF, idempotency, one-use tokens, recovery/session revocation, private manual quarantine/scanner/parser and entrypoints. Real local SMTP/ClamAV integration passed22 assertions. No personal provider calls, no invented metrics in new runtime. Old database fingerprints unchanged.

## Not verified / release hold
An independent reviewer agent did not return a usable report after attempts; do not call that review done. Production deployment, externally trusted email delivery/region/privacy settings, S3 and backup/purge policies, legal/data/support scope and secret rotation require explicit decisions. Database backup restore is local; private blob restore procedure still needs production rehearsal. Retained legacy templates/sensors are not customer-facing Stage1 functionality; no legacy-data import performed. Night mode, native installs, PWA offline, dragged layouts, stock, AI and MCP remain unimplemented/deferred.

## Evidence
Exact final commands/counts/screenshots live in TASK_CHECKLIST.md and docs/STATE.md. Failed test traces are retained privately under frontend/test-results; they are not published artifacts. Synthetic fixtures are labeled as tests, never real factories/manuals/engineering advice.
