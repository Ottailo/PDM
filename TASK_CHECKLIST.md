# Machivital Stage 1 verification checklist

Current status: local implementation on `feat/machivital-private-pilot`; not deployed or approved for customer use. The older checklist below is a historical demo record, NOT current release proof. The 2026-11-11 source audit disproved its blanket real-hardware, reliable-prediction, secure-auth and real-work-order claims. Prior screenshots/printed script success do not close these gates.

## Public publishing and visual polish — 2026-11-12

Approved scope: public pilot information on the feature-branch preview; private service remains local. No main merge, production alias promotion, private DB migration or provider changes.

- [x] PUBLISH-UI: `frontend/src/{styles,Auth,Brand,App,pilot,PilotPage}` warm mineral/sage polish, actual handlers retained, phone Jobs label/44px controls/reduced-motion, Source Sans3/Barlow verified via preview inspect.
- [x] PUBLISH-BOUNDARY: standalone `pilot-main.tsx`/HTML/config, single static Vercel target, private modules excluded; 4artifact negative-control tests and source-only build exit0; public Edge2tests8.4s zero forms/API queries, GET/POST unavailable JSON/503.
- [x] PUBLISH-VERIFY: final type/lint/frontend64tests20.65s/private+publicbuild/4artifact tests exit0; backend/calendar/runtime143tests291.51s exit0; private Edge5journeys2.5m exit0 after all fixes. Original24tables/9files/3legacyDBs unchanged/check exit0. Frozen0001 whitespace exception documented, not modified.
- [x] PUBLISH-PROOF: reviewed public `tests/screenshots/public-pilot/{desktop,mobile-320,mobile-390}.png`; private synthetic persona captures are ignored/machine-local. Contrast7.30/6.53/7.21:1, public console clean, source credential-pattern scan0hits. Detailed failures preserved in VERIFICATION.md.
- [x] PUBLISH-GIT: staged174files private-path/credential scan0hits; attributed commit `08b62ce55b6ecbe79c455fdde9e98e9e04358235` pushed to `origin/feat/machivital-private-pilot`. Vercel Git status success/Deployment has completed: `https://vercel.com/ottailo-projects/pdm/3P5gZ7neWbfemufQASxcc2KNkhTh`. Preview `https://pdm-git-feat-machivital-private-pilot-ottailo-projects.vercel.app` is SSO-protected; actual CDN/UI behavior remains unverified without accepted Vercel auth. `main` remains6539ad2; no production alias promotion/private backend release.

## Preventive maintenance milestone — locally verified 2026-11-12

Contract `docs/PREVENTIVE_MAINTENANCE_API.md`, state `docs/PREVENTIVE_MAINTENANCE_STATE.md`; approved local-only, not production/customer prediction.

- [x] PM-CONTRACT: requirements/API/ownership frozen; source snapshot30files preserved; original24tables/9files unchanged; HEAD6539ad2.
- [x] PM-SCHEMA: scratch0003 migrate/check exit0; explicit names correct observed duplicate-FK failure; targeted15PM/reminder tests122.05s exit0 include forward/constraints/provenance. Frozen0001/0002 hash match, original DB unchanged. Final full106test suite and full-component restore passed exit0.
- [x] PM-CALENDAR: purecalendar17tests and fullbackend106passed428.50s exit0 cover anchored day/week/month/DST/leap, bounded coalesce/oneunfinished/edit/pause/resume/reopen. Browser actual server preview and generated work passed full5Edge suite.
- [x] PM-DELIVERY: PM15targeted backend tests122.05s +19operations/migration/reminderfix tests112.10s exit0; real HTTP10assertions/Mailpit due +controlledclock due/overdue1unfinished exit0. Lease/provenance/refusal/ack/offboard/fairness tested. Rescheduled mail currentUTC/plant time negativecontrol red→green; acceptance not receipt.
- [x] PM-PHONE: actual PM Edge form/mandatorypreview/role/technician/planner/viewer/stores journey passed; final complete5Edge tests3.6m exit0. Team actions measured44px/visible at320/375/390, reauth dialog checked; screenshots pm-owner-mobile-visible-team-actions/pm-technician-mobile-submitted/pm-planner-reviewed-history/pm-stores-read-only-plan/pm-viewer-read-only-plan.png. Finalfrontend61tests/type/lint/build exit0.
- [x] PM-RESTORE: isolated manifest17runtimeguard tests; actual DB+1privatePDF+separate temporary MFAkey restore checks exit0; recoverylogin/history/PMcursor/checksum/safeworker plus corrupt/missingblob/wrongkey/stale-schema negatives. Original24tables/9files unchanged, no originals migrated.
- [x] PM-FINAL: final106backend428.50s/no skips;36calendar/runtime/recovery;61frontend16.39s/type/lint/build;5Edge3.6m;10realPMAPI;controlledclockSMTP/fullDBblobseparatekeyrestore all exit0.42Pythonmodules compiled,49packages compatible, npm runtime audit0, source review adjudicated, original fingerprints/migrations/HEAD unchanged. Raw proof PM_VERIFICATION.md/private logs; ownedservices stopped. Production release remains HOLD.

## Security remediation acceptance — 2026-11-12

Historical Stage1 checks below are retained. Current evidence: `docs/SECURITY_REMEDIATION_VERIFICATION_2026-11-12.md`.

- [x] Preserve existing files/databases/config: read-only checker24originaltables/9protectedfiles unchanged, legacy3DBhashes unchanged, HEAD6539ad2 unchanged, no staged files, exit0. Negative control rejects deliberately mismatched private fingerprint. Original pilot remains `pilot_0001`.
- [x] Team/identity/concurrency: final serial `.venv/Scripts/python.exe -m pytest tests/backend -q` with verified disposable `_test` DB and `PDM_PARSER_SANDBOX_IMAGE` pinned ID: **88passed,364.74s,exit0**. Edge `team-security.spec.ts` offboards current-tenant session, preserves other tenant, last-owner409 and cancelled-link400; included final4passed2.8m exit0. Screenshots `tests/screenshots/personas/security-owner-offboarding.png`, `security-cancelled-invitation.png`.
- [x] Quotas/reservations/fairness/recovery: `test_quota_scheduler.py` included88passed. New idle-worker full-quota-refund/blob-cleanup test red then green1passed9.04s exit0; run_once invokes bounded persisted staging reconciliation. Live-upload nonblocking fence, concurrent boundary admission, offboard during blob I/O, tenant fairness and stale worker fences pass. No original blobs removed.
- [x] Parser/migration containment: default Docker executable regression red→green; removed pypdf fixture API fixed. `verify_parser_sandbox.py --image <verified immutable local ID>` exit0: nonroot/seccomp/readonly/noegress/nohostmounts/noprivateenv, unsafe/encrypted/malformed rejection, timeout workload absent, production rootful rejected. Restored scratch copy alone upgraded `pilot_0001`→`pilot_0002`; check exit0/no operations, frozen0001 hash unchanged. Full backend run includes actual Docker opt-in, no skipped probe.
- [x] Integrated quality proof: typecheck/lint/31frontendtests/build exit0, Edge4tests2.8m exit0, final real Mailpit/ClamAV/pinned-parser API22assertions exit0; uv49packages compatible and37Python files compiled exit0, npm runtime audit0vulnerabilities, diff check exit0 with CRLF advisory warnings. Failed initial84pass/2fixturefail run preserved. Independent source review adjudicated, not independent certification. Screenshots/copy read for truthful synthetic fixtures.

Release HOLD persists for production packaging/runtime/launcher trust, full database/blob/key recovery, retention/legal/support and explicit deployment approval. No commit/push/deploy/provider-key changes. Bounded verification worker stopped; verification scratch DB/private evidence retained.

## Historical Stage1 acceptance gates
- [x] ID-01/02: PostgreSQL backend suite `PDM_TEST_DATABASE_URL=<isolated _test DB> .venv/Scripts/python.exe -m pytest tests/backend -q` — final serial exit0,24 passed in87.04s; real API SMTP verification/invitation/MFA/replay/logout proof22 assertions exit0 (`scripts/pilot/verify_api_journey.py`). Browser signup/verification/MFA/recovery-login core journey2passed exit0.
- [x] TEN-01: `tests/backend/test_domain.py` and `test_identity.py` exercise two tenants, composite FK denial, role denial, session/recovery revocation and concurrent one-use tokens; included in24passed final suite.
- [x] REG-01: core Edge browser journey records arbitrary equipment without sensors; API reload preserves make/model/serial. Async option regression fixed with controlled selectors (`frontend/tests/async-selection.test.tsx`,2passed); screenshots `tests/screenshots/personas/owner-empty-workbench.png` and `owner-mobile-workbench.png`.
- [x] JOB-01/02: real API assigned technician start/block/resume/submit/manager-review/history/export + mismatched/duplicate idempotency and foreign denial22 assertions exit0. Edge core journey2passed with actual approval event/Reopen assertions; `tests/screenshots/personas/owner-completed-job.png`.
- [x] DOC-01/02: actual local ClamAV PONG, clean OK and harmless EICAR FOUND (`scripts/pilot/verify_scanner.py` exit0); real API upload→quarantine→scan→bounded parse→TEST-ONLY-42 page→private download/foreign denial exit0. Backend negative delete/failed/malicious tests included final24passed. Browser private reader inspected at375px with no horizontal overflow; full persona suite final switch rerun passed1test58.7s; final combined3browsertests passed. Screenshots `technician-authenticated-manual-marker.png`, `foreign-owner-private-manual-denied.png` and `organization-switch-clears-private-manuals.png` in root tests/screenshots/personas.
- [x] UX-01: final `npm --prefix frontend run typecheck`, lint, `test -- --run`, build exit0;27passed. Core Edge spec2passed and actual manual/team spec1passed58.7s after confirmed defects fixed. Browser screenshots/readable375px reader and phone navigation; semantic modal focus/unit keyboard tests. No night mode or native/PWA packaging claimed. Final consolidated Edge run3passed,exit0; `frontend/tests/e2e/{workbench,manual-team}.spec.ts`.
- [x] OPS-01: empty `machivital_pilot` migrated to `pilot_0001`; `flask db check --directory migrations_pilot` exit0/no new operations; no runtime seed tests, worker lease/concurrent-claim/SMTP failure and migration roundtrip included24passed. Snapshot-safe `scripts/pilot/verify_backup_restore.py` exit0:24 table/counts restored into new scratch DB; production/private-blob restoration still a release prerequisite.
- [x] SAFE-01: legacy API/setup-admin/ingest blocked410 in tests and real API journey. `scripts/pilot/legacy_fingerprint.py --check` exit0:3 original DB files unchanged. New factory imports no predictors/simulator/provider. Optional entrypoint hides boot errors; SMTP explicitly validates TLS certificates; regressions included24passed.
- [x] Stage 1 self-audit: source/test review found and corrected password trimming, async context selections, invitation-success precedence, SMTP TLS verification and entrypoint traceback exposure; fresh negative controls and final suites pass. New runtime source search has no TODO/FIXME/phantom metrics/random fallback/provider calls. `docs/STAGE1_REVIEW.md` records findings. Independent security audit NOT completed; separate release gate remains open.
- [ ] Release review: hosting/backup restore/email/data/support/credential-rotation decisions approved before customer use.

## Historical prototype checklist (superseded; not release acceptance)

This historical checklist records earlier demo work. Claims require fresh validation and must not be marketed as real factory proof.

## Phase 1: Core Wire Bugs & Predictor Robustness
- [x] Fix `MODEL_BASE_DIR` in `app/__init__.py` to anchor dynamically to absolute path based on project root. (Verified: `app/__init__.py` line 34, models resolve regardless of execution cwd)
- [x] Align maintenance endpoints: support `/api/request-maintenance` and `/api/perform-maintenance` in `app/api/routes.py` with full payload handling (`parts`, `estimated_duration`, `technician_notes`). (Verified: `verify_full_system.py` TEST 3 returned 200 with "Maintenance scheduled for FILLING_001")
- [x] Update `DataSimulator.request_maintenance` in `app/services/simulator.py` to enter `Maintenance` state with realistic countdown duration and recovery transition instead of instant reset. (Verified: `app/services/simulator.py` transitions state to `Maintenance` with `event_steps_left`)
- [x] Ensure `"machine_id": machine_id` is included in all prediction objects returned by `PredictiveService`. (Verified: `app/services/predictor.py` line 639 & line 830, tested in `verify_full_system.py` TEST 2)
- [x] Verify unit & service tests for predictor and simulator pass exit code 0. (Verified: `verify_full_system.py` exit code 0)

## Phase 2: Unified V2 Schema Migration
- [x] Refactor `app/api/machine_management.py` to perform CRUD on `Asset`, `AssetTemplate`, `AssetSensor`, and `Location` (V2 Schema). (Verified: `verify_full_system.py` TEST 1, 11 physical assets loaded from V2 schema)
- [x] Update `app/static/js/machine_management.js` so machine registration registers physical `Asset` instances visible on the main dashboard. (Verified: payload maps to V2 schema with `Asset` and `MachineState` creation)
- [x] Align `app/api/ingest.py` to validate sensor channels against `AssetSensor` database records dynamically rather than hardcoded static files. (Verified: `app/api/ingest.py` queries `AssetSensor.channel_id`)
- [x] Maintain backward compatibility for any existing seed templates and associations. (Verified: legacy sensor templates and configurations intact)

## Phase 3: Database Retention & Bloat Remediation
- [x] Create a pruning routine in `app/services/maintenance_db.py` to keep high-frequency sensor readings within a rolling window (e.g. 48 hours). (Verified: `fast_prune_and_vacuum(keep_recent_count=150000)` and `prune_older_than(hours=48)` implemented)
- [x] Prune stale historical records from the 5.2GB `instance/maintenance.db`. (Verified: Pruned 28,053,245 stale rows, cutting DB size from 5,223 MB down to 30.96 MB)
- [x] Execute `VACUUM` on SQLite database to reclaim disk space. (Verified: Reclaimed >5.19 GB of unfragmented disk space)
- [x] Hook the pruning routine into the simulator or periodic background maintenance loop so the database stays lean (<100MB). (Verified: `app/services/simulator.py` triggers retention prune every 600 cycles)

## Phase 4: Real Model Training & Ingestion Pipeline
- [x] Implement `POST /api/machine-mgmt/upload-training-csv` endpoint to receive, validate, and store real run-to-failure telemetry CSVs. (Verified: `verify_full_system.py` TEST 7 uploaded `test_telemetry.csv` and validated 8 channels)
- [x] Implement `POST /api/machine-mgmt/train-model` endpoint to trigger background model training. (Verified: Dual-Head GRU in `verify_gru_training.py` exit code 0 and OmniRoute Reasoner in `verify_full_system.py` TEST 5 exit code 0)
- [x] Update `_MODEL_CACHE` dynamically upon training completion so newly trained weights are immediately active. (Verified: `trainer.py` re-populates `PredictiveService._MODEL_CACHE` with hot-loaded Keras model and scalers)
- [x] Wire `machine_management.js` to call real upload and training endpoints with live progress and genuine status feedback. (Verified: UI controls wired with `#training-indicator`, `#training-text`, `#training-epochs`, and `#start-training-btn`)
- [x] Populate model validation analytics with authentic metrics from training history rather than static mock arrays. (Verified: `verify_full_system.py` TEST 4 retrieved authentic evaluation metrics for 4 asset classes)

## Phase 5: OmniRoute LLM Diagnostic Advisory Integration
- [x] Implement `app/services/llm_advisor.py` connecting to OmniRoute (`http://127.0.0.1:20129/v1`) using `auto/best-fast`, `agy/gemini-2.5-flash`, and heuristic fallback. (Historical test credential redacted; validity and any required rotation remain unverified. Not a production integration approval.)
- [x] Create endpoint `POST /api/ai-diagnostics` returning structured physical root-cause analysis, severity classification, and component inspection checklist based on real sensor anomalies. (Verified: `verify_full_system.py` TEST 6 returned full mechatronic diagnostic payload)
- [x] Add an interactive "AI DIAGNOSTIC ADVISOR" modal and triggers in `app/templates/components/modals.html` and `app/static/js/dashboard.js`. (Verified: `#ai-advisor-modal-overlay` interactive with action checklist, severity badges, and auto-dispatch pre-selection)
- [x] Verify AI diagnostics endpoint with live telemetry data. (Verified on `FILLING_001` with exit code 0)

## Phase 6: System Verification & Post-Build Self-Audit
- [x] Verify Python syntax and import integrity across all modified files. (Verified: All modules compile and import with zero errors)
- [x] Run automated API endpoint tests (`scripts/verify_full_system.py`, `scripts/verify_gru_training.py`). (Verified: 100% passed with exit code 0)
- [x] Verify full application boot and dashboard payload via `curl`. (Verified: `/api/latest-states` returns 11 online assets)
- [x] Complete self-audit pass ensuring zero empty handlers and zero mock stubs. (Verified: No dead ends, authentic two-way dispatch and training pipelines active)
- [x] Update persistent memory in `.agents/memory/pdm.md`. (Verified: Documented architecture, pruning service, and OmniRoute reasoning pipeline)

## Phase 7: Real-World Pilot & Edge Connectivity Facilities
- [x] Implement Universal Edge Daemon (`scripts/edge/pdm_edge_agent.py`) with SQLite Store-and-Forward FIFO buffering. (Verified: `verify_edge_and_pilot.py` TEST 7)
- [x] Implement PLC Modbus TCP Gateway Bridge (`scripts/edge/pdm_modbus_bridge.py`) for Siemens, Schneider, and Allen-Bradley PLCs. (Verified on port 502 holding register unpacking)
- [x] Implement MQTT Industrial Subscriber Bridge (`scripts/edge/pdm_mqtt_subscriber.py`) for smart wireless IoT sensors. (Verified)
- [x] Add Ingestion Handshake & Connection Profile APIs (`/api/ingest/ping` & `/api/ingest/connection-info`). (Verified: `verify_edge_and_pilot.py` TEST 1 & 2)
- [x] Implement Live Hardware Mode with Simulator Bypass (`app/services/simulator.py` line 135 & `/api/ingest/toggle-mode`). (Verified: `verify_edge_and_pilot.py` TEST 4)
- [x] Build Automated Statistical Baseline Calibration Engine (`app/services/calibrator.py` & `/api/machine-mgmt/calibrate-asset`). (Verified: `verify_edge_and_pilot.py` TEST 5 across all 3 channels)
- [x] Build Industrial Incident Webhook & Telegram Alert Dispatcher (`app/services/alert_dispatcher.py`). (Verified: `verify_edge_and_pilot.py` TEST 6)
- [x] Build Interactive Device Connection Wizard Modal (`#device-connection-modal` & `app/static/js/device_connection.js`) with one-click code generation and live ping testing. (Verified)
- [x] Author Comprehensive Industrial Pilot Deployment Playbook (`PILOT_DEPLOYMENT_PLAYBOOK.md`). (Verified)

## Phase 8: Real-World Factory Operations & Mobile Surveillance Remote
- [x] Retire synthetic simulation default across the platform: `ENABLE_SIMULATOR` defaults strictly to `False` in `app/__init__.py` and `run.py`. (Verified: `verify_real_world_factory.py` TEST 1 exit code 0)
- [x] Implement Edge Heartbeat Watchdog in `app/services/predictor.py`: assets with zero readings report `Awaiting Telemetry` with edge setup instructions instead of being skipped or showing fake status. (Verified: `verify_real_world_factory.py` TEST 2)
- [x] Implement Signal Dropped Detection in `app/services/predictor.py`: telemetry timeout (>45s) flags `Signal Dropped` with physical cabling and edge service RCA steps instead of falsely reporting "Normal". (Verified: `verify_real_world_factory.py` TEST 3)
- [x] Implement Live Auto-Recovery in `app/services/predictor.py`: active edge stream (<45s) immediately promotes asset to `Live` and `Normal`. (Verified: `verify_real_world_factory.py` TEST 4)
- [x] Align Ingest API (`app/api/ingest.py`) to accept both `sensors` and `readings` payloads with automatic timestamp normalization. (Verified: `verify_real_world_factory.py` TEST 5)
- [x] Fix SQLite `sensor_data` primary key auto-increment schema to eliminate SQLAlchemy identity map null errors. (Verified: schema migrated with `INTEGER PRIMARY KEY AUTOINCREMENT`)
- [x] Anchor SQLite database URI dynamically in `app/__init__.py` to project root (`instance/maintenance.db`). (Verified: deterministic database access from any execution working directory)
- [x] Build Dedicated Mobile Remote Surveillance Web App (`/mobile`, `app/templates/mobile_dashboard.html`, and `app/static/js/mobile_dashboard.js`):
  - Viewport-fit cover, touch ergonomics, and PWA manifest (`app/static/manifest.json`). (Verified: `verify_real_world_factory.py` TEST 6)
  - 2-second real-time telemetry polling with live heartbeat LED indicator. (Verified: `fetchFleetState()`)
  - Multi-zone RUL gauge bar and real-time metric pills for Speed, Temp, Pressure. (Verified)
  - Haptic alarm vibration triggers on critical state changes (`navigator.vibrate([200, 100, 200])`). (Verified: `triggerAlarmVibration()`)
  - Mechatronic Root-Cause Diagnostic Drawer powered by OmniRoute LLM with interactive technician floor checklist. (Verified: `openDiagnosticDrawer()`)
  - 1-Tap Field Service Work Order Dispatch modal and handler (`POST /api/request-maintenance`). (Verified: `verify_real_world_factory.py` TEST 7)
  - Mobile Edge Ingest Tester sending live test bursts. (Verified: `sendMobileIngestTest()`)
- [x] Add Desktop Header `MOBILE REMOTE` launch button (`header.html`) and QR Code Modal (`modals.html` & `dashboard.js`) enabling workstation engineers to scan and open `/mobile` on smartphones. (Verified)
- [x] Build Multi-Asset Industrial Floor Edge Feeder Script (`scripts/edge/factory_floor_feeder.py`) simulating independent external PLCs (Line 1 Bottling, Line 2 Packaging, Capping) transmitting genuine HTTP edge bursts with disconnect and degradation simulations. (Verified)
- [x] Run full system test suite (`verify_full_system.py`, `verify_edge_and_pilot.py`, `verify_real_world_factory.py`) with 100% exit code 0. (Verified)

## Phase 9: Vercel Serverless Production Deployment & Cloud Readiness
- [x] Streamline dependencies: Separate massive ML binaries (`scipy`, `scikit-learn`, `tensorflow`) into `requirements-ml.txt`, reducing `requirements.txt` to <80MB (clearing Vercel's 250MB uncompressed limit). (Verified)
- [x] Eliminate `os.dup2` file descriptor redirection in `app/services/predictor.py` to prevent AWS Lambda CloudWatch supervisor pipe corruption and `FUNCTION_INVOCATION_FAILED`. (Verified)
- [x] Guard top-level Keras/TensorFlow imports to optimize serverless cold start from 12.8s down to 3.6s, eliminating invocation timeouts. (Verified)
- [x] Configure dual zero-config entrypoints (`index.py` at root and `api/index.py`) exposing WSGI `app` and `application`. (Verified)
- [x] Implement dynamic route restoration in `api/index.py` via `__pdm_path__` rewrite query capture (`/(.*) -> /api/index?__pdm_path__=$1`) ensuring exact path matching for `/`, `/mobile`, `/manifest.json`, and `/api/*`. (Verified: all routes return 200 OK)
- [x] Enable serverless ephemeral SQLite operation in `/tmp/maintenance.db` with automated cold-start fleet seeding and disabled WAL mode. (Verified: live edge telemetry packet ingested returning 200 OK and transitioning fleet to Live)
