# Security remediation checkpoint

## Fresh continuation — 2026-11-12

Existing patch verified before changes on `feat/machivital-private-pilot`, HEAD `6539ad2`. Original `machivital_pilot` remains `pilot_0001`; only restored scratch `machivital_security_20261112` upgraded to `pilot_0002`, migration check exit0. Original 24 table fingerprints and 9 protected config/migration/legacy/blob files unchanged; three legacy DB hashes unchanged. Existing edits retained; no commit/push/deploy/provider/key changes.

Observed/fixed: removed pypdf fixture API `add_js`; default literal Docker executable rejected by runner; idle worker did not invoke expired-staging cleanup. New executable and idle-cleanup tests observed red then green. Parser containment verifier exit0, actual seccomp/nonroot/readonly/network/mount/env/socket denials and timeout cleanup, unsafe/encrypted/malformed PDF rejection. Rootful production intentionally refused; production restricted launcher/kernel trust not closed.

Frontend typecheck/lint/31 unit tests/build exit0; npm runtime audit0. Final Edge suite **4passed,2.8minutes,exit0** including offboarding/last-owner/invite cancel and five-persona manual/team isolation. Final real API journey **22assertions,exit0** using scratch DB and separate private proof, real Mailpit/ClamAV/pinned parser. Python uv compatibility check49packages exit0;37scripts compiled exit0. Complete final backend rerun **88passed,364.74s,exit0**, including actual Docker opt-in and both new regressions; no skipped containment test.

Independent read-only reviewer reports required correction: other-tenant session survival and five-minute session reauth are explicit contracts; released rows already excluded from quota; document scheduling is tenant-fair. These were withdrawn. Final reviewer inaccurately repeated stale red outcomes; main direct execution is authoritative, not a certification. Details: `docs/SECURITY_REMEDIATION_VERIFICATION_2026-11-12.md`.

## Historical checkpoint — 2026-11-11

Approved: fix release security blockers locally, no production deployment/commit/push/credentialrotation/AI/hardware. Existing branch feat/machivital-private-pilot and old data preserved; frozenpilot0001 not modified.

Baseline before edits:24backendtests passed47.73s exit0,3legacyDBfingerprints unchanged. Main frontend team regression initially failed3/4 (controls missing), implementation now in progress; not called integrationproof.

Ownership: backendagent app/pilot auth/security/model/document/worker/factory + newmigration/tests; sandboxagent newrunner/parserimage/probes; main frontend/docs/explicitignoreddevconfig/integration. No overlapping file writers and no parallel suites using same disposabletestDB.

Current: authoritative member removal/roles/cancellation,reauth5min,shared/exclusive transactionguard,uploadreservation/quota/fairness and secureparserOSboundary implementation. Main Team UI uses exact contract docs/SECURITY_PATCH_API.md. Parserimage and backend tests pending.

Remaining: migrate separate localpilot/test lineage0002,real constrainedparser probes,currenttests plus offboard/quota/concurrency/browserflows,independentreview after finalchanges,report precise closures. Production restrictedlauncher/kerneltrust,packaging/fullrecovery/data/support remain independentreleasegates.
