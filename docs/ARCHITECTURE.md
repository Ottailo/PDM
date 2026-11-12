# Stage 1 architecture

## Runtime boundary
One Flask domain API `/api/v1`, a React/TypeScript client, PostgreSQL business records and separate durable worker entrypoint. Development frontend proxy uses the API at localhost:5051. In a production package, a single HTTPS ingress may serve the built frontend and Flask. Vercel hosting is optional, not a second backend.

The old demonstration database/model files are not customer data. New pilot schema is installed by an explicit separate migration lineage. No create_all/seeding at application startup, no auto-login, no legacy public blueprints, no simulator/LLM/model training loaded for customer paths.

## Data model
Company remains organization/tenant; User remains identity with Membership per organization. Location and Asset are tenant-owned; optional machine templates/sensors. Stable IDs are not editable machine names. WorkOrder + append-only events represent actual human transitions; telemetry state is not a work order. Document metadata tracks private file, checksum/version and processing status. Sessions, expiring action tokens, recovery-code hashes and durable jobs share database persistence.

All links must be checked for same tenant, with composite relational constraints where possible. Authorization applies to each object access, export, download and worker operation. API input cannot select arbitrary tenant or grant a role. Mutations use CSRF and maintenance uses idempotency fingerprints/revision conflicts.

## Documents and mail
Email uses a real SMTP adapter and durable delivery intent; local Mailpit captures messages only in development. Tokens never appear in normal JSON responses. Delivery states do not pretend provider acceptance is human receipt.

Documents live outside static/repository paths in private storage. Development uses an ignored private local root; production storage configuration must be approved. PDFs enter quarantine, actual ClamAV scanning then bounded independent parser process. Missing scanner/failed validation means unavailable, not ready. Extracted pages retain page number. No remote AI/crawling or unsafe executable deserialization.

## Worker
Same application package, separate process. Atomic claims, leases, retries, abandoned-job recovery, visible permanent failures. No HTTP server started by worker, no sleeps used as business completion. Side effects are at-least-once; crash after delivery must not be advertised exactly-once. Document deletion/revocation and consent are rechecked before processing/access.

## Threat boundary
Untrusted browser parameters, IDs, uploaded bytes/filenames/PDF active content, email action tokens and credentials. Secure cookies with server revocation, CSRF, password reauth for MFA setup, encrypted MFA secret, one-use recovery hashes, rate limits. No predictable API keys or public hardware token disclosure. Legacy API returns disabled/not found in customer runtime. Error responses carry safe code/message/request ID, not traces/secrets.

## Verification
PostgreSQL tests are mandatory for actual constraints/concurrency, plus temporary file storage and captured mail. Browser tests cover signup/verification/MFA, machine CRUD, membership invite, job transitions and private manual reading. No old default-DB scripts are run. Current graph service has no PDM index; source+test tracing is authoritative until one exists.

## Deployment remains pending
No production services were changed. Local container passwords and mail identities are labeled development-only. Live factory telemetry, failure prediction, native apps and remote MCP remain out of Stage 1.
