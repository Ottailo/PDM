# Local Stage 1 pilot

Development only; no customer deployment or hardware commissioning.

Local isolated containers:
- PostgreSQL `machivital-pilot-db`, host `127.0.0.1:55432`, pilot DB `machivital_pilot`, test DB `machivital_test`.
- SMTP capture `machivital-pilot-mail`, SMTP port `11026`, inbox `http://127.0.0.1:8026`. This is a development inbox, never a production verification workaround.
- Malware scanner `machivital-pilot-scan`, clamd port `13310`. Verified with `python -I scripts/pilot/verify_scanner.py`: exit0, PONG, clean `stream: OK`, harmless EICAR `Eicar-Test-Signature FOUND`. This proves actual local scanning, not the not-yet-complete upload workflow.

`compose.pilot.yml` pins the three exact image digests inspected locally; containers bind localhost only. Existing unrelated containers were not modified.

Configuration is ignored `.env.pilot`; private documents in ignored `.pilot/documents`. Do not use original `instance/maintenance.db`, public credentials or production provider pools. Dependency reproducibility uses requirements-pilot.in/lock and isolated .venv. Frontend has its own package lock.

API localhost:5051, frontend localhost:5173. Both started via Browser preview configurations. Do not use old run.py or api/index.py for new customer runtime. Schema migrations are explicit, not app boot side effects. Worker processes queued mail and scan/extract PDFs. Migration: `.venv/Scripts/python.exe -m flask --app wsgi:app db upgrade --directory migrations_pilot`. One bounded job batch: `.venv/Scripts/python.exe -m app.pilot.worker --max-jobs 10`. Development-only continuously polling verification worker: `.venv/Scripts/python.exe pilot_worker_dev.py --seconds 900`; it stops after the stated duration. It is not a production scheduler.

Tests: set `PDM_TEST_DATABASE_URL` to the disposable machivital_test URI and run `.venv/Scripts/python.exe -m pytest tests/backend -q`. Never point this test fixture at the pilot/customer DB; it truncates only an explicitly named `_test` DB. Frontend: `npm --prefix frontend run typecheck`, lint, `test -- --run`, build. Browser: `PDM_BROWSER_CHANNEL=msedge npm --prefix frontend run test:e2e` uses installed Edge when pinned Chromium is unavailable; record browser used. Use `localhost:5173` to match the configured CSRF origin. Screenshot proof is saved under root `tests/screenshots/personas/`.

Nothing here certifies security, commercial readiness or factory connectivity. Current proof and failures are in TASK_CHECKLIST.md and docs/STATE.md. Remote email, hosting, paid AI and production changes still require separate approval.
