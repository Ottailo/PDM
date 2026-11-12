# Local PM runtime / recovery contract

Operation: local implementation/rehearsal only, not DEPLOY. Native Flask/React/PostgreSQL/foreground outbox on explicitly isolated run. App health/ready/worker diagnostics not production certification. No providers/hardware/real recipients/install/pull/commit/push. STOP on failed guard/preservation/unexplained migration/test failure.

## Runtime preflight

Existing `.venv/Scripts/python.exe` CPython3.13 and49compatible pinned packages; Node26.7.0. Node declaration aligned to jsdom31 requirements `^22.22.2 || ^24.15.0 || >=26.0.0`; no install. API5053 / web5174 / SMTP11027 / inbox8027 checked free before preparation. Other session's5051 retained. Loopback existing DB55432 and scanner13310. Existing parser image sha256:94eb11fac2a171ce59582f4f74aa039f496531b5621861786323cabb45fe9316, mail image sha256:aef2aacc11f075ec0fb6874275ee4a421e688e11a96ebb296134d1735c7761ce; inspect-only, no pulls/build requirements now.

Private `.pilot/pm-run.json` owns namespace machivital_pm_159682ffc75a and app/_test/_restore databases, tempkeys, separate blob/restored root and persistent Mailpit. Process environment explicit OS allowlist plus local app values; no S3/AWS/provider/env credentials copied. `LOAD_PILOT_ENV=False` required so factory cannot reload original ignored config. Missing prerequisites/fixed port collision hard fail; partial provision manifest preserved (no automatically deleting unknown DB/container). All mail is captured locally, never claims of human receipt.

## Recovery and identity

Backup source only namespace-matched app DB; new empty restore DB and empty restored blob root enforced, checksummed known-hex PDF keys and dump. Exports repeatable-read snapshot; owned worker stopped/no uploads so blob consistency not assumed under arbitrary writes. Matching generated MFA key remains separately in local manifest, not dump. No source customer/private keys in delivery. DB dump+checksum files alone insufficient; verify restored MFA/recovery, authorized manual bytes/history, PMstate and safe worker resume. Corruptdump/blob/unownedtarget blocked before tool calls. Missing/wrong key, stale schema, lost blob fail authorization/ready/integrity rather than pretend restored success.

## Final local empirical gate

Runtime negative controls16passed0.95s exit0: original/remote/mutable/shared/unsafeport targets denied; original provider/SMTP/AWS/DockerHost omitted; partial preparation refused; corrupt/unowned restore rejected before DB/tool IO. Source/restore scripts compile. Original24tables/9files unchanged, frozen0001/0002 hash match. Actual PMAPI10assertions, targeted15tests122.05s and migration/reminderfix19tests112.10s, finalEdge5tests3.6m, frontend61tests16.39s/type/lint/build, controlled-clockSMTP and full app/blob/testkey restore proof exit0. Final complete backend106passed428.50s exit0/no skips after migration relationlock correction. Local PM milestone verified; no production completion inferred. Finalcalendar/runtime/recovery36passed exit0.

Foreground worker runs explicit bounded service after backend ready, stopped before restore/end. API/web launch via preview tools only; autoPortfalse, actual launcher/proxy use same manifest ports. Original pilot0001 never migrated/launched as0003. Build SHA remains6539ad2 uncommitted local edits, no production canary or release assertion. Public demo untouched.
