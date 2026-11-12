# Isolated PM runbook — locally verified, not production

## Boundaries

Never start original pilot_dev/wsgi against original0001 DB while current code targets0003. No commits/deployment/customer mail/provider keys. New harness refuses originals, forces local storage, OS-only config and fresh temporary keys; isolated mailbox and blob roots. Existing scanner read-only reused; rootful parser containment proves local behavior only. Other session's5051 API stays untouched.

Existing tested prerequisites: CPython3.13 local uv environment/49compatible packages; Node26.7.0 and compatible frontend engine declaration; already available pinned parser/Mailpit images; loopback PostgreSQL55432/scanner13310. Missing prerequisites stop rather than install/pull. API5053/web5174/SMTP11027/inbox8027 checked free and fixed; no silent auto-port movement.

## Prepared run and safe restart

Private `.pilot/pm-run.json` owns namespace `machivital_pm_159682ffc75a`, app/`_test`/`_restore` DBs, keys and separate blobs/mail. Do not print/stage it. `pm_runtime.py info` prints nonsensitive identity/ports. Prepare once only; existing/partial manifests and nonempty restore targets are preserved, not overwritten.

All owned API/web/worker/Mailpit processes were stopped at handover; scratch artifacts retained. To rehearse again, start only manifest-owned Mailpit (no pull/recreate), then preview configurations `machivital-pm-api` and `machivital-pm-web`, then `.venv/Scripts/python.exe -I scripts/pilot/pm_runtime.py worker --seconds 900`. Stop only those owned processes. Do not use original launch or another session's5051. Migration/check explicit on manifest-owned app DB, not startup side effects.

## Native verification

- `.venv/Scripts/python.exe -I scripts/pilot/run_pm_checks.py backend tests/backend -q`: final106passed428.50s exit0; exclusive new `_test` fixture lock and real pinned parser, no skips.
- `.venv/Scripts/python.exe -m pytest --noconftest tests/runtime tests/calendar -q`:36passed exit0, runtime/calendar/restore guards.
- Frontend manifest typecheck/lint/test--run/build:61tests16.39s exit0. `run_pm_checks.py e2e`: installed Edge5tests3.6m exit0; helpers use isolated origin/mailbox/fixture.
- `verify_pm_journey.py`:10realHTTP assertions with local SMTP/scanner/parser, exit0. `verify_pm_clock.py`:in-process TESTING clock only, actual due/overdue SMTP and one unfinished order; no HTTP clock hook.

## Restore and failure semantics

Stop owned worker/any upload before snapshot. `pm_restore.py backup` uses exported DB snapshot and known-hex PDF inventory; then restore only into owned new empty*_restore and empty restored-documents. Current prepared run already contains completed snapshot/restore; do not rerun preparation/restore over these artifacts. Matching temporary encryption/session keys stay separately in manifest, not dump/blob archive; never copy original/provider keys.

`verify_pm_restore.py` passed restored MFA/recovery sign-in, PMcursor/work history, private PDF checksum and safe worker resume with TESTING mail capture. Corrupt/missing blob, wrongkey and stale schema rejected. Source snapshot/restore fields restored after negative controls. This is local synthetic app recovery, not production offsite policy, SLA or customer exit approval.

## Observed defects fixed

Duplicate new-schema composite-FK names; Alembic self-lock from open application transaction (migration now refuses open transaction,5s other lock timeout, tests close session); rescheduled local due-date mismatch; Edge path discovery and accessible test selector issues. Failures/traces retained privately. Final raw proofs/checklist/screenshots: `PM_VERIFICATION.md`, `TASK_CHECKLIST.md`, `tests/screenshots/personas/pm-*.png`.

Original24tables/9protectedfiles/3legacyDBs and frozen0001/0002 unchanged; HEAD6539ad2, nothing staged/committed. Public legacy demo unchanged. Release gates remain `RELEASE_GATES.md`; original connected/predictive vision remains `ORIGINAL_VISION_CROSSCHECK_2026-11-12.md`.
