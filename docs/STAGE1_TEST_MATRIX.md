# Stage 1 independent acceptance matrix

## Scope
Tests below are acceptance requirements, not passed results. Test data synthetic and private; none represents a real factory or OEM instruction. API and browser gates must run against disposable PostgreSQL/temp uploads, local captured SMTP and approved local scanner.

| Boundary | Positive behavior | Negative/control |
|---|---|---|
| Auth | Signup → captured real mail → one-use verification → login | Wrong password, replay/expired token, no verification, rate limit, malicious next URL |
| MFA | Password reauth → enrollment → code accepted → recovery once | Bad code, replay recovery, re-enrollment without reauth, missing owner/admin MFA |
| Session | Auth me, logout, reset revocation | Old session after logout/reset rejected; cookie HttpOnly and production Secure/SameSite |
| Tenant | Two factories use same machine code | Foreign location/asset/assignee/job/manual IDs denied; client role/tenant fields rejected |
| Registry | Optional-sensor general machine add/edit/search/archival | Stale revision, required fields, nonexistent location, archive preserves history |
| Jobs | Assign/start/block/resume/submit/approve history | Technician cannot approve/cancel other's job; missing checklist/notes, invalid transition |
| Replay | Same key same payload returns prior result | Same key changed payload conflict, concurrent duplicate creates one record |
| Manuals | Valid synthetic PDF → real scan → parse → exact page → download | EICAR, bad signature, oversized/corrupt/encrypted/active PDF, scan unavailable, foreign/deleted document |
| Worker | Committed job claim/retry/lease recovery | Crash after SMTP delivery documented at-least-once; no fabricated ready, revoked doc can't publish |
| UX | Phone/keyboard/desktop focus/real counters | Blank factory zero counts/no chart, service failure explicit retry, no dummy timer/empty button |
| Legacy | New API private | Old /auth/setup-admin, /api/ingest, /api/history, /api/request-maintenance etc disabled |
| Data | New schema via explicit migration | Original instance DB fingerprints unchanged; no app-start seed/create_all |

Record actual commands/exit codes/counts/screenshots in TASK_CHECKLIST.md. Browser preview tools provide runtime inspection; tests are not replaced by screenshot-only proof. PostgreSQL transactions required for tenant constraints/idempotency. No live email recipients or model spend during tests.
