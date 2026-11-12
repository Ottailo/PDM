# Preventive-maintenance verification — 2026-11-12

**Verdict: PASS for the approved LOCAL PM milestone; HOLD for public/customer release.** Calendar plans, real assigned work, reminder delivery records, phone workflows and synthetic full-component recovery were exercised. No equipment commissioning, prediction validation or security certification is implied.

## Final execution proof

| Gate | Fresh command / scope | Result |
|---|---|---|
| Complete backend | `.venv/Scripts/python.exe -I scripts/pilot/run_pm_checks.py backend tests/backend -q`; explicit new loopback `_test` DB, exclusive suite lock, actual pinned `PDM_PARSER_SANDBOX_IMAGE` | **106 passed in 428.50s, exit0; no skips** |
| Calendar/runtime/recovery negatives | `.venv/Scripts/python.exe -m pytest --noconftest tests/runtime tests/calendar -q` | **36 passed, exit0**; latest5.14s; includes restored-blob manifest consistency |
| Frontend | `npm --prefix frontend run typecheck`, `lint`, `test -- --run`, `build` | **61 tests/7files,16.39s, all exit0** |
| Installed Microsoft Edge | `.venv/Scripts/python.exe -I scripts/pilot/run_pm_checks.py e2e` | **5 passed in3.6minutes, exit0**; these are browser journeys, not equipment-edge commissioning |
| Real PM HTTP | `.venv/Scripts/python.exe -I scripts/pilot/verify_pm_journey.py` | **10 assertions, exit0**: real isolated Mailpit, ClamAV/pinned parser, private manual, plan/work/review/tenant boundaries |
| Due/overdue delivery | `.venv/Scripts/python.exe -I scripts/pilot/verify_pm_clock.py` | **exit0**: harness-only TEST_CLOCK, real isolated SMTP due+overdue, one unfinished order, cancel/pause |
| Full-component recovery | `pm_restore.py backup`, `restore`, then `verify_pm_restore.py` | **all exit0**: isolated DB+1privatePDF+separately supplied matching temporary key; MFA/recovery sign-in, PM cursor/history, checksum download, safe resume |
| Compatibility/static | `uv pip check --python .venv/Scripts/python.exe`;42currentPythonmodules compile; e2e/helper ESLint; `git diff --check`; npm runtime audit | **exit0**;49packages compatible;0runtime npm advisories; CRLF advisory warnings only |
| Preservation | `verify_preserved_state.py --baseline <private original baseline> --check`, `legacy_fingerprint.py --check`, frozen0001/0002 source hashes, git HEAD/staging | **exit0**:24originaltables/9files/3legacyDBs unchanged, HEAD6539ad2, nothing staged |

Backend106 includes existing security/domain/parser/worker/migration regressions plus new PM/reminder and migration-open-session controls. Calendar cases cover month-end/leap/DST/local-to-UTC, bounded catch-up, repeated/concurrent tick, one unfinished order including review, pause/resume/edit snapshots, reopening conflict, provenance/tenant constraints, retries/offboarding and queue fairness. Migration0003 applied/check passed only on scratch data; original pilot remains0001. Frozen0001/0002 unchanged.

## Actual browser and recovery evidence

PM browser journey creates a real plan through the form, requires current server calendar preview, waits for persisted occurrence and SMTP acceptance, submits technician checklist/labor, verifies manager approval and read-only stores/viewer denial. Team actions measured44px and in viewport at320/375/390px; reauthentication dialog remains required. Five persona screenshots in `tests/screenshots/personas/`: `pm-owner-plan-and-real-reminder.png`, `pm-owner-mobile-visible-team-actions.png`, `pm-technician-mobile-submitted.png`, `pm-planner-reviewed-history.png`, `pm-stores-read-only-plan.png`, `pm-viewer-read-only-plan.png`. Final screenshots wait actual Awaiting review/dialog closure rather than pending Saving state. Screenshots read for truthful synthetic labels; no factory/customer outcomes claimed.

Restore uses only the new empty `_restore` DB and `restored-documents`; original DB/blob paths cannot be targets. Matching test keys remain separate from dump/blob manifest. Corrupt/missing blob, wrong encryption key and stale schema were rejected; expected generic FileNotFoundError/InvalidToken server logs preserved. Revision/blob state restored after negative controls. Restored mail uses explicit TESTING capture, no unintended SMTP recipients. Snapshot dump/blob corruption, shared/remote targets, provider inheritance, unsafe paths and partial provisioning are also negative-tested.

## Observed failures, corrected and retained

- Initial0003 setup failed with duplicate auto-generated names for assignee/escalation composite membership FKs. Explicit `fk_plan_assignee`/`fk_plan_escalation` in new migration/models corrected it; scratch migration/check passed, frozen files untouched.
- Initial full backend stopped after22tests: an application transaction held pilot_jobs relation locks while separate Alembic connection waited on ALTER TABLE. Migration entry now refuses an open app transaction and bounds other lock waits at5s; migration tests explicitly close sessions. Targeted19tests112.10s exit0, then final106test suite exit0.
- Reminder email printed original local slot after work due-date edit while UTC showed revised due. NoDB and PostgreSQL regression observed red→green; email derives current due in captured occurrence timezone. Original slot remains immutable audit data.
- Browser environment omitted ProgramFiles discovery paths; installed Edge found at Program Files(x86), OS-only allowlist corrected without install. Exact label selectors missed required-star/hint accessible names; observed snapshots drove scoped selector corrections. Raw screenshots/traces retained privately. An interim whole-suite attempt was stopped for restore orchestration and is not passing proof.
- Independent read-only reviewer proposed a multiline-subject defect; direct source proved Subject uses only label+work.number, and reviewer withdrew it. No unnecessary title restrictions applied. Source review is not independent certification.

## Local environment and evidence ownership

Private namespace `machivital_pm_159682ffc75a`: separate application/`_test`/`_restore` databases, local blob roots, fresh temporary keys and own persistent Mailpit11027/8027. API5053/web5174 explicitly fixed; no auto-port misattribution. OS-only allowlisted runtime config forces local storage; original `.env.pilot`, provider/S3 credentials and mailbox are not inherited or changed. Existing local scanner13310 reused with no unrelated-container modification; pinned existing parser/mail images, no installs/pulls.

Raw failed and passing outputs, source snapshot and keys remain in ignored `.pilot/` and are not staged/published. Final backend log: `<run_dir>/logs/backend-final-green.txt`. Owned API/web/worker/mail processes stopped; another session's existing5051 API left untouched. Scratch DBs/blobs/evidence retained for inspection.

## Still held

Production WSGI/build packaging and supervision, approved hosting/TLS, real sender deliverability, offsite recovery/retention/RPO/RTO, purge/export/customer exit, privacy/legal/support and buyer acceptance, production restricted parser launcher/daemon/kernel trust, and explicit release authorization. Public legacy demo unchanged. Machine connectors/monitoring, predictive accuracy, inventory, saved drag layouts, AI/mascot/MCP and native/offline distribution remain later scoped milestones. No commit, push, deployment, key rotation, equipment access, real-user invitations or provider inference occurred.
