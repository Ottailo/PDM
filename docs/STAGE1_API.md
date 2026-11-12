# Stage 1 API contract

One Flask backend, same-origin React frontend; base `/api/v1`. JSON request/response; no alternate Node backend. Stage 1 customer paths never read demo data or call AI/predictors. Existing `Company` is tenant, `User` identity, `Asset` equipment. New memberships define roles owner/admin/planner/technician/stores/viewer. All foreign references tenant-scoped. `TESTING` never implies default data access.

## Envelope/security
Success payload is an object with named resource (`user`, `company`, `asset`, `work_order`, `document`) or list (`assets`, `locations`, `members`, `work_orders`, `documents`, `events`). IDs integers; public machine code is separate display data. Dates ISO UTC. Errors `{error: {code, message, fields?}, request_id}`. Client renders message without HTML.

`GET /csrf` returns `{csrf_token}` and cookie-backed anonymous session. All mutations including signup/login/send-reset require `X-CSRF-Token`. Client always sends credentials same-origin. Server headers private `no-store`. Authenticated session stores revocable session identity, active membership; use authoritative DB roles. TOTP is required for owner/admin commercial-sensitive actions; local registration can reach enrollment then must enroll before registry writes. Development mail capture is a real SMTP sink, not fake emailed tokens; test fixtures access a test adapter only. Never include verification/reset tokens in normal API responses.

## Identity
- `POST /auth/signup {name,email,password,company_name}` → 201 `{user,company,message}` pending verification. It does not login an unverified account. Rate-limit and reject weak password. Do not accept role/company_id.
- `POST /auth/verify-email {token}` → 200 `{message}`; one-use expiring token.
- `POST /auth/resend-verification {email}`, `/auth/forgot-password {email}` → generic 202 `{message}` regardless account existence. Queue mail in same DB transaction, do not claim delivered.
- `POST /auth/reset-password {token,password}` → 200; revoke all previous sessions.
- `POST /auth/login {email,password,totp_code?}` → 200 `{user,company,membership,mfa_required?,mfa_enrollment_required?}`. Verified only. Existing TOTP configured requires valid code. No persistent session for invalid code. Never keep user password for second step; return 401 code `mfa_required` if needed.
- `GET /auth/me` → `{user,company,membership,mfa_enrollment_required,capabilities}` or 401.
- `POST /auth/logout {}` → 200, revoke session, clear cookie.
- `POST /auth/mfa/setup {password}` → `{secret,otpauth_url}` provisional expiring enrollment; no setup without password reauth. `POST /auth/mfa/confirm {code}` → `{recovery_codes}` shown once; save hashed recovery codes; one-use recovery at login allowed. `/auth/mfa` status GET.
- `GET /companies` → `{companies:[{id,name,role}]}`; `POST /companies/switch {company_id}` validates membership. Switching returns `/auth/me` envelope, resets active tenant client state.
- `GET /members` → `{members:[{id,user_id,name,email,role}]}`.
- `POST /invitations {email,role}` → 201 `{message}` queue expiring invite; owner/admin only, cannot invite owner. `POST /invitations/accept {token,name,password}` → `{message}`; existing identities authenticate to accept, no password overwrite. GET `/invitations/preview?token=` safe basic company/email metadata for valid token.

## Registry
- `GET /locations` → `{locations:[{id,name,type,parent_id}]}`.
- `POST /locations {name,type,parent_id?}` → 201 `{location}`; Site/Area/Line; valid tree and same tenant.
- `GET /assets?q=&location_id=&include_archived=false` → `{assets:[{id,code,name,manufacturer,model,serial_number,criticality,location_id,location_name,status,description,revision,telemetry_status:'not_connected'}]}`. Optional category/template; no fake health/metrics.
- `POST /assets {code,name,manufacturer?,model?,serial_number?,criticality?,location_id?,description?}` → 201 `{asset}`. code unique within company only; id independent. owner/admin/planner.
- `GET /assets/<id>` → `{asset}` tenant-scoped.
- `PATCH /assets/<id> {revision,...fields}` → `{asset}`, stale revision 409. `DELETE /assets/<id>` archive only, preserve job/manual history.
- `GET /summary` → `{asset_count,open_work_order_count,awaiting_review_count,completed_work_order_count,overdue_work_order_count,document_count}` calculated from actual records. No current machines online or avoided downtime.

## Maintenance
- `GET /work-orders?asset_id=&status=&assigned_to_me=true` → `{work_orders:[WorkOrder]}`. Technician may view authorized tenant records but mutate only assigned jobs. Each WorkOrder has `id,number,title,description,asset_id,asset_name,priority,status,assignee_id,assignee_name,due_at,revision,created_at,completed_at,notes,completion_notes,checklist`. Number stable company scoped.
- `POST /work-orders {asset_id,title,description?,priority?,assignee_id?,due_at?,checklist?:[{text}]}` → 201 `{work_order}`; operator/technician can request, planner manages assignment. Reject foreign assignee and asset. Default status open; assigned if assignee supplied by planner.
- `GET /work-orders/<id>` → `{work_order,events:[{id,actor_name,action,from_status,to_status,notes,created_at}]}`.
- `PATCH /work-orders/<id> {revision,assignee_id?,due_at?,priority?}` → `{work_order}` planner only; no arbitrary status edits.
- `POST /work-orders/<id>/transition {revision,action,notes?,checklist?:[{text,completed}],labor_minutes?}` actions `start`, `block`, `resume`, `submit`, `approve`, `cancel`, `reopen`. Open/assigned→in_progress; in_progress→blocked with reason; blocked→in_progress; in_progress→awaiting_review requires all required checklist and nonempty notes; awaiting_review→completed planner approval; cancel/reopen manager with reason. No browser countdown. Append-only events. revision conflicts 409. Idempotency-Key all maintenance mutations; matching replay returns same result, mismatched payload 409. No health resets.
- `GET /work-orders/<id>/export` → safe CSV chronological record; server-authorized, prevent spreadsheet formula injection.

## Manuals
- `POST /documents` multipart `file,asset_id,title?` → 202 `{document}` with real status quarantined/queued. CSRF header. PDF only first slice (size/page limit, actual signature/MIME); worker scans via configured ClamAV and parses PDF in separate bounded process. Without scanner returns failed/blocked not ready. Require no remote AI.
- `GET /documents?asset_id=` → `{documents:[{id,title,filename,asset_id,asset_name,status,page_count,error?,created_at,checksum,revision}]}`.
- `GET /documents/<id>` → `{document}`; `GET /documents/<id>/download` authorized binary after ready; attachment safe filename. `GET /documents/<id>/pages/<n>` → `{page_number,text}` only ready, tenant-authorized. Files private, no static URL. Inline reader can use the authenticated PDF endpoint; sanitize dangerous PDF active content or return attachment plus extracted-text viewer as safest initial UI.
- `DELETE /documents/<id>` soft-delete metadata, revoke access and parser jobs; keep explicit retention policy.

## Operations/disabled legacy
`GET /healthz` dependency-free; `/readyz` DB/migration connection no sensitive config. Worker invoked explicitly, not spawned on page reads. Env required production SECRET_KEY/DATABASE_URL/private storage/SMTP/scanner. Local development env stored ignored only. Server app runtime never create_all/seed. Dedicated `flask db`/Alembic migration command or explicit CLI migration uses separate tested lineage; no blanket stamp legacy.

Customer runtime must not register legacy public blueprints at all; legacy `/api/latest-states`, `/api/history`, `/api/request-maintenance`, `/api/ingest`, `/auth/setup-admin`, `/admin`, `/mobile` blocked or redirect to workbench with no data exposure. Demo only explicit isolated app/database, no default fixed admin account in customer factory.

Frontend navigation Stage1: Today, Machines, Maintenance, Manuals, Team (settings). Parts/Connections/AI not rendered as dead controls. URLs `/login`, `/signup`, `/verify-email?token=`, `/reset-password?token=`, `/invite?token=`, `/mfa`, `/app`, `/app/machines`, `/app/machines/:id`, `/app/maintenance`, `/app/maintenance/:id`, `/app/manuals`, `/app/team`. No pretend live values, customers, response speeds, or savings.
