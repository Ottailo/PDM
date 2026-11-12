# Security remediation integration contract

Scope is approved local remediation, not production release. Existing `/api/v1` and error envelope preserved.

## Team administration
- `POST /auth/reauth {password,totp_code}` → `{message}` proves exact password plus enrolled authenticator/recovery code and authorizes sensitive access changes for5minutes in the current revocable server session. No password persistence.
- `PATCH /members/<id> {role,reason}` → `{member}`; role choices owner/admin/planner/technician/stores/viewer. Owners manage privileged roles/promote existing teammate to owner; admins only non-owner/non-admin, grant no privileged role. Recent reauth required. Lastactive owner cannot be removed/demoted.
- `DELETE /members/<id> {reason}` → `{message}` softoffboard, recent reauth; only tenant membership sessions revoked, other-company identity preserved. Matching unused invitations cancelled. Current self removal signs out unless other active tenant selected separately.
- `GET /invitations` → `{invitations:[{id,email,role,expires_at}]}` owner/admin authorized pending entries only.
- `DELETE /invitations/<id> {reason}` → `{message}` same tenant, recent reauth, invalidates link and queuedmail.
- `GET /members` keeps existing list shape and may add active/revision.
- Access changes append audit in database; no tokens/secrets logged. No erasing existing work history or downloaded files.

## Upload admission
Keep10MiB perfile, proposed validated configurable tenant defaults500MiB retained bytes/100retained files/10pendingjobs/10uploadattempts per10minutes. Error `{error:{code,message,fields?}}` uses stable quota/rate codes and real limits. Retained/deleted originals stay charged; stagedstorage must not be runnable until success. New job provenance/capacity via pilot0002; frozen0001 unchanged.

## PDF boundary
Sandbox agent exports `app.pilot.sandbox_runner.parse_pdf(content)` reading PDF_PARSER_MODE (default docker), PDF_PARSER_IMAGE immutable sha256 image id, optional PDF_DOCKER_EXECUTABLE, existing PDF_MAX_BYTES/PAGES/TEXT/PARSE_TIMEOUT and APP_ENV. Secure production requires rootless/restrictedlauncher; rootfulDesktop local verification only. Developer subprocess explicit development mode allowed tests/dev, forbiddenproduction, no silentfallback. Worker reexports parse_pdf for compatibility and handles parser-rejected vs unavailable distinctly. Sandbox agent reports exceptions.

## Tests and change ownership
Backendagent owns auth/security/models/worker/documents/factory/migration/tests; sandboxagent owns newrunner,image/probes/test_parser_sandbox; mainfrontend/docs/privateenv. No concurrent edits to these files and no concurrent suites against same `_test` DB. Main runs full integrated tests last. No remote service/provider/credentialrotation/deployment/commit.
