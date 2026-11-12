# Machivital execution proof

## Public publishing and visual polish — 2026-11-12

This turn publishes a static public pilot overview only. The real private maintenance service remains a local rehearsal, not a production/customer release.

- Frontend final coordinator post-navigation run: `npm --prefix frontend run typecheck`, `lint`, `test -- --run`, `build`, `vercel-build`, `test:public-build`: **exit 0**, **64 tests in 20.65s**, both Vite builds passed, **4 public build-contract tests** passed including a deliberate private-client negative control.
- Public browser: `npm --prefix frontend run test:public-e2e`: **2 passed in 8.4s, exit 0** using installed Microsoft Edge. Native disclosures, keyboard focus, 390/320px no-overflow, private/auth/legacy deep links, zero forms/API queries/page errors and unavailable API GET/POST JSON/503 are verified locally. Screenshots: `tests/screenshots/public-pilot/{desktop,mobile-320,mobile-390}.png`.
- Source-only rehearsal: `node scripts/pilot/verify_public_source.cjs`: **exit 0**, public TypeScript/Vite build passes with only deployment-allowed source and installed dependencies, no private modules/service environment. Actual `.vercelignore` evaluation excludes Python, private Auth/API/query modules, runtime/config/evidence, while including public entries/config/assets.
- Preview source inspection: main used snapshot/click/inspect/eval/screenshot; public console has no errors, native disclosure toggles, no API requests or account forms. Measured lead/kicker/action contrast **7.30:1 / 6.53:1 / 7.21:1**. Local private login inputs measured **44px**, Source Sans 3 body **16px**, intentional Barlow headings. Phone navigation now uses visible `Jobs` while retaining accessible `Maintenance`.
- Final private Edge suite: `.venv/Scripts/python.exe -I scripts/pilot/run_pm_checks.py e2e`: **5 passed in 2.5 minutes, exit 0**, after all source/navigation/harness fixes. Real SMTP verification/MFA/recovery login, machines/job completion/review, scanned private manuals/foreign denial, five personas, offboarding/last-owner/invitation cancellation and preventive-plan reminders all exercised. Phone Jobs label single-line assertion passed. Private screenshots remain ignored.
- Staged audit: **174 files**, zero forbidden private/config/memory/database/trace/screenshot paths, zero high-confidence credential-pattern hits. `git diff --cached --check` identified whitespace in frozen `pilot_0001`; preserved byte-for-byte as required. All other staged files pass formatting after a test EOF cleanup. This is a recorded formatting exception, not a hidden clean full-diff claim.
- Initial backend/calendar/runtime run: **142 passed in 212.55s, exit 0**. Final post-harness-change run: **143 passed in 291.51s, exit 0** including runtime allowance isolation and normal backend rate-limit denial. Python source/tests: **54 modules compile, exit 0**. Runtime npm audit **0 vulnerabilities**. Original read-only baseline and checks: **24 original tables, 9 protected files, 3 legacy databases unchanged**; isolated migration check **exit 0, no new operations**.

### Failures preserved and corrected

1. New public build test initially used CJS imports, violating the existing ESM lint rule. Converted to `.mjs`; final type/lint/unit/build chain exit 0. Dedicated `tsconfig.pilot.json` prevents the public build from requiring excluded private/test modules.
2. Simultaneous public/private Playwright runs shared default `test-results`, deleting an in-use private trace resource (ENOENT at security context close). Preserved raw artifacts under ignored `.pilot`; public config now uses `public-test-results`. Private security assertions passed on the next run.
3. Repeated five-persona suites exhausted the actual 30-login/ten-minute loopback IP limit; subsequent recovery-login received a truthful 429, not an MFA bug. The namespace-validated disposable PM helper now explicitly permits 500 rehearsal attempts; normal app factory default remains 30 and backend denial test remains active. No production security control disabled. Final clean run recorded below.
4. Visual critique caught mid-word phone `Maintenance` wrapping; visible tab changed to `Jobs` with accessible full label and E2E single-line check. Public screenshots refreshed without keyboard-test focus overlay.
5. Giving every nav link an aria-label made `getByLabel(/^Machine/)` match the Machines link as well as the form field. Explicit label now applies only to the shortened Maintenance/Jobs link. A bounded 900-second worker expired during repeated verification, leaving genuine email jobs queued; rearmed the isolated worker rather than pretending SMTP delivery or weakening tests. Failed runs remain private.

Only informational public screenshots are committed. Private persona screenshots, account evidence, mail, recovery keys, uploads, traces and local memory are excluded from Git/Vercel. Git push and actual CDN verification are recorded separately; local success is not proof of deployment.

## Historical Stage 1 local execution proof

## Fresh security continuation — 2026-11-12

Authoritative current evidence: `docs/SECURITY_REMEDIATION_VERIFICATION_2026-11-12.md`. Failed initial backend run84passed/2failed (removed pypdf fixture API) preserved; corrected fixture and new default-Docker/idle-cleanup regressions passed focused checks. Full final serial post-fix rerun **88passed in364.74s,exit0**, including actual Docker opt-in, no skips. `uv pip check --python .venv/Scripts/python.exe`:49packages compatible,exit0;37Python scripts compile exit0. Frontend typecheck/lint31tests/build exit0; Edge4tests2.8m exit0; final API22assertions exit0 using real Mailpit/ClamAV/pinned container, no original pilot writes. Original24tables/9protectedfiles/3legacyDBs unchanged. Scratch `pilot_0001`→`pilot_0002` upgrade/check exit0; production kernel/launcher and full DB/blob/key restoration still open. Historical results below do not replace current proof.

## Historical execution — 2026-11-11

This is software acceptance in a local isolated environment, not a field-equipment test, customer deployment or independent security certification.

## Backend
`PDM_TEST_DATABASE_URL=<isolated machivital_test URI> .venv/Scripts/python.exe -m pytest tests/backend -q`
Final serial run: **exit0,24 passed in87.04s**. Includes exact-password regression, TLS certificate/hostname verification, generic optional-entrypoint failure, token/session/MFA/tenant relations, assigned work/idempotency/concurrency, actual isolated PDF parsing and scanner-failure controls. Test suite requires `_test` DB and exclusive session advisory lock; never falls back to old data. Earlier overlapping cleanup failures and SMTP mock configuration failure are retained privately and not counted.

Migration command `.venv/Scripts/python.exe -m flask --app wsgi:app db upgrade --directory migrations_pilot`:exit0,clean new PostgreSQL. `db check`:exit0,No new upgrade operations detected. `/readyz` migration-aware, `/healthz` no inferred machine safety.

## Real external boundaries locally
`.venv/Scripts/python.exe -I scripts/pilot/verify_api_journey.py`:exit0,**22 assertions**. Actual Mailpit SMTP verification/invite, owner MFA, two tenants, arbitrary machine metadata, technician completion/planner review, replay conflict, real ClamAV+isolated PDF processing, exact TEST-ONLY-42 text/private download and foreign denial. Synthetic `.test` identities explicitly used; no real customers or OEM manuals claimed.

`verify_scanner.py`:exit0,PONG; clean stream OK; harmless EICAR detected FOUND. `check_private_runtime.py`:exit0,explicit config/PostgreSQL/SMTP/scanner reachable. `legacy_fingerprint.py --check`:exit0,**3 old DB files unchanged**.

`verify_backup_restore.py`:exit0,**24 tables/counts** match a new scratch restore using one exported repeatable-read snapshot. First attempt compared live counts across concurrent writes and failed; harness corrected rather than hiding the anomaly. Database restore does not yet prove production object-storage restore or customer retention policy.

## Frontend
Main ran `npm --prefix frontend run typecheck`, lint, `test -- --run`, build after the final organization selector correction:all exit0;27 unit tests passed in10.60s. The final serialized backend suite passed24 tests including SMTP TLS and safe entrypoint regressions. Runtime audit0vulnerabilities. Tests include no fabricated records/errors, CSRF, transport replay and async form selection.

## Browser
Servers started through preview tool:API5051,web5173. Playwright pinned Chromium was unavailable; install blocked by shared lock, not deleted. Tests executed in installed **Microsoft Edge** using `PDM_BROWSER_CHANNEL=msedge`; project name chromium denotes the engine family, not a pinned Chrome binary.

Core workbench spec: **2 passed,exit0** (latest18.2s): meaningful public routes, actual signup/captured-mail verification/MFA, empty factory, machine→job/start/checklist/submit/approve, exact completed event and mobile recovery login. Screenshot paths under `tests/screenshots/personas/`.

Manual/team spec: **1 passed,exit0,58.7s** after invitation success-state and organization selector fixes. It executes real invitation, technician workflow, actual scanned PDF/text/download, stores/viewer write403, foreign metadata/page/download denial and switching away from private data. Exact switch response and authoritative identity are checked; not inferred from a role label. Final consolidated Edge run: **all3 tests passed,exit0,1.3minutes**. Exact runtime recorded as installed Microsoft Edge via PDM_BROWSER_CHANNEL=msedge, not the missing pinned Chromium.

Built-in preview independently inspected actual maintenance history and manual reader, verified375px no horizontal overflow and CSS16px body/Barlow headings. Screenshots show explicitly synthetic records, not fake production dashboards.

## Review/release limits
No usable independent reviewer report returned; that gate remains open. Production host/TLS/email credentials, S3 behavior, blob restore/purge/retention, data/privacy/support/legal terms, owner-approved credential rotation and release sign-off pending. No commit,push,deployment,paid AI,outreach,hardware,MCP,inventory,native packaging or predictive claims authorized/performed.
