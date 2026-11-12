# Local security remediation verification — 2026-11-12

## Session and security contracts

Authorized scope: resume the existing local security patch in PDM on `feat/machivital-private-pilot`, HEAD `6539ad2`. Single existing working tree; preserve prior tracked/untracked edits, frozen `pilot_0001`, three legacy databases, original PostgreSQL pilot data, private blobs, and provider keys. No commit, push, deploy, hardware commissioning, provider inference, credential rotation, or real-user messages.

Surface: session-authenticated `/api/v1` team administration and manual uploads, durable workers, constrained PDF parsing. Trust boundaries: untrusted browser → same-origin Flask API → PostgreSQL; uploaded bytes → private blob storage → ClamAV → parser container; queued mail → loopback Mailpit only. Sensitive data: identities, private manuals, credential hashes, encrypted MFA/mail tokens and revocable session records. Local HTTP is development-only, not TLS deployment evidence.

STRIDE controls to verify: spoofing/session replay (password+MFA reauthentication and session revocation); tampering/elevation (authoritative tenant roles, last-owner guard, append-only audit); disclosure (cross-tenant denial, parser secret/mount isolation); availability (transactional reservations, quotas, scheduling, bounded parser and cleanup). No AI or money-moving path in scope; ATLAS/AI RMF/F3 do not apply.

Framework provenance: local security skill `references/framework-mappings.md`, reviewed 2026-11-12, pins ATT&CK v19.1, CSF 2.0 and D3FEND v1.4.0. Applicable mapped behaviors: T1078 Valid Accounts (Initial Access), T1190 Exploit Public-Facing Application (Initial Access). CSF: PR.AA, PR.PS, PR.IR, DE.CM, RC.RP. D3FEND: Application Hardening, Content Validation/File Content Analysis, Execution Isolation/Network Isolation, Process Termination/Restore Access. These are control mappings, not claims of a demonstrated exploit or certification.

Manifest commands: frontend `typecheck`, `lint`, `test -- --run`, `build`, `test:e2e` from frontend/package.json; backend `.venv/Scripts/python.exe -m pytest tests/backend -q` with an explicit verified loopback `_test` database. Fixtures truncate only the disposable test database and hold an exclusive advisory suite lock. Actual parser verifier takes an immutable local image ID. Preview launches use Browser tools only. Completion requires fresh tests, local API/browser negative controls, parser syscall/cleanup proof and preservation fingerprints; skipped/failed checks stay open.

Stop-the-line: unexpected failure, unsafe/nonlocal DB target, changed preserved fingerprint, unreconciled original edits, test collision, or external recipient/provider boundary. Preserve failure evidence; root-cause before feature work.

## Initial verified state

- Branch/HEAD match handoff; existing edits preserved. No staged changes observed.
- `legacy_fingerprint.py --check`: exit 0, three original DB files unchanged.
- `check_private_runtime.py`: exit 0, loopback PostgreSQL 55432, Mailpit 11026/8026 and ClamAV 13310 reachable.
- Read-only PostgreSQL inspection: original `machivital_pilot` is **pilot_0001**; existing disposable `machivital_test` is **pilot_0002**. Do not claim the original pilot was migrated.
- `.env.pilot` has no explicit `PDM_TEST_DATABASE_URL` or parser image/mode/executable. Initial preflight deliberately stopped with `AssertionError: Explicit test DB URL missing`; no fixtures ran. Existing `_test` DB independently verified, and its URL supplied only to the child test process; private env unchanged.
- Existing local `machivital-pdf-parser` image found; verify immutable identity and actual containment, not mutable tag trust.
- Fresh frontend typecheck/lint/unit/build: exit 0, **31 tests**, 5 files, 15.82 seconds; Vite build completed in 2.53 seconds.

## Current / remaining

First backend launch stopped before pytest: image lookup inferred `:latest`, but the existing parser image uses a different tag. Docker returned `No such image: machivital-pdf-parser:latest` (exit 1). Resolve the already observed image ID directly, without rebuilding/pulling or treating a mutable tag as trust. Fresh original-pilot snapshot/restore: exit 0, 24 tables/counts into `machivital_restore_check_20261111231727` (UTC filename). A second new database `machivital_security_20261112` received that snapshot, then upgraded `pilot_0001` → `pilot_0002`; `check` exit 0, no new upgrade operations. No existing database migrated/truncated except the explicitly disposable test database. Read-only fingerprint baseline covers 24 original tables and 9 protected config/migration/SQLite/blob files. New process-local runtime wrapper uses this copy, separate ignored blob directory, pinned parser image and loopback mail/scanner. `/healthz` and `/readyz` both returned 200. Preview initially resolved launch configurations from parent workspace, not newly granted PDM; added isolated launch there without changing original API launch. Initial Vite 502/ECONNREFUSED occurred before API started; reload and retest after API boot. Independent review initially proposed changes contradicting explicit other-tenant/session-window contract and quota-filter/scheduler source; those are not accepted findings. Asked reviewer for adversarial correction.

## Observed failures and targeted corrections

- Initial complete backend run: **84 passed, 2 failed, 321.07s, exit 1**. Both failures arose before active-PDF negative control generation: pypdf 7 removed `PdfWriter.add_js`. Existing pinned package source documents `add_open_action(JavaScript(...))`; updated only the verifier fixture. Focused parser fixture/default-resolution run now **2 passed, exit 0**.
- New Docker default regression observed red: factory passes literal `docker`, but `_docker_executable` interpreted it as an absolute-path override and rejected it. Literal `docker` now follows existing no-override PATH resolution, yielding a fixed absolute binary; arbitrary command strings/overrides remain rejected. No weakening of production rootless/seccomp/image gates.
- New idle-worker regression observed red: expired charged staging row remained unreleased after `run_once`. Added existing bounded nonblocking `reconcile_staging(app)` before job claim. Behavioral regression now **1 passed in 9.04s, exit 0**, asserting automatic blob removal and full bytes/files/pending quota refund. Live upload fences and only persisted known blob keys remain in use.
- Independent reviewer withdrew contract/source false positives. Their rootless-vs-rootful proposal is an existing intentional production gate, not a local defect; main verified the actual executable mismatch separately. No new production Docker socket/startup behavior authorized.

## Integrated evidence before final rerun

- Real Mailpit/ClamAV/pinned-container API journey: **22 assertions, exit 0**. Proof written under `.pilot/security-20261112/.pilot/api-proof.json`; original `.pilot/api-proof.json` preserved.
- Installed Edge serial browser run: **4 passed, 2.9 minutes, exit 0**. Five-persona manual/roles/organization isolation, offboarding/last-owner/invitation cancellation, public forms and signup/MFA/job lifecycle. New screenshots `tests/screenshots/personas/security-owner-offboarding.png` and `security-cancelled-invitation.png`.
- Initial preview errors were Vite 502/ECONNREFUSED before isolated API boot; subsequent reload rendered workbench and API logs show no server errors. Historical console entries are not represented as a fresh clean-console assertion.

Standalone actual Docker verifier **exit 0** after fixture correction: UID/GID65532, all capabilities zero, seccomp/no-new-privileges, denied network/root writes, absent private env/host files/socket; active/encrypted/malformed PDF rejection; timeout container absence; rootful production fail-closed. This is local containment observation, not kernel/daemon authorization certification. Reviewer final return incorrectly repeated pre-fix red results and called the opt-in image unset despite actual standalone green evidence; those statements are rejected. Source-review feedback is not independent executed verification or certification.

Python `-m pip check` unavailable (`No module named pip`); do not install into or alter the existing environment. Check existing uv-managed environment separately. Runtime npm audit **exit 0, 0 vulnerabilities**; new pilot source scan no TODO/FIXME/shell=True/eval/exec/unsafe pickle/provider calls.

## Final verdict and preservation — 2026-11-12

**PASS for this local verification scope; HOLD for production release/security sign-off.** Final serial backend: **88 passed in 364.74 seconds, exit 0**, including actual Docker opt-in (no skips) and new executable/idle-cleanup regressions. Final installed-Edge suite: **4 passed in 2.8 minutes, exit 0**. Final actual API journey: **22 assertions, exit 0**, private report `.pilot/security-20261112-final/.pilot/api-proof.json`, old proof untouched. Frontend typecheck/lint/31tests/build exit0; uv49installedpackages compatible exit0;37Python files compiled exit0; npm runtime advisory audit0vulnerabilities exit0. Backend compatibility is not a full dependency vulnerability audit, and no remote scanner upload ran.

Fresh preservation: **24 original PostgreSQL tables and 9 protected files unchanged**, three legacy DB fingerprints unchanged, frozen0001 unchanged, private env unchanged, no staged files, HEAD `6539ad2` unchanged. Deliberately modified private fingerprint rejected by checker negative control without modifying source data. New verification databases/backup and synthetic evidence retained. No original pilot schema/data/blob replaced; original pilot is still `pilot_0001`. Only disposable `machivital_test` fixture cleanup and new restored-copy DB writes performed. Actual preview GET auth/member/invitation endpoints200 after restart; health/ready200 on isolated runtime. Current API logs no server errors; old Vite startup502 and React aborted probe requests remain in historical network/console logs and are not hidden.

Dedicated source self-audit reviewed exact changes/negative controls; independent agent review was read-only and inaccurate findings were rejected/withdrawn rather than altering established security contracts. No independent certification or broad vulnerability-free claim. Screenshots read for actual labels, no customer/hardware outcomes represented; narrow preview's team table uses internal horizontal scrolling while Edge screenshots cover full desktop and manual-reader mobile journey.

Bounded verification workers stopped after checks; preview services stopped at handover. Private launch entries retain explicit isolated runtime for reproducibility; they do not alter the original pilot launch or provider keys. No commits, push, deployment, external inference, hardware commissioning, real-user invitations or key changes.

Remaining release gates: approved production package/supervision/TLS; production restricted parser launcher/daemon/kernel trust (rootful Desktop evidence is local only); complete DB/blob/key restore and retention/purge/export policy; legal/support/customer scope and explicit release authorization. Do not run the original pilot API against schema0001 and new code without a separately approved migration/config procedure. Original pilot schema/data and blobs remain untouched. Release held for production restricted-launcher/kernel trust, full DB/blob/key recovery, packaging/operations and retention/legal/support approvals.
