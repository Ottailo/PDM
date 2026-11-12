# Machivital: original vision cross-check — 2026-11-12

## Verdict

**The original vision is not fulfilled. The new locally verified product is a maintenance workspace, not yet a connected-machine monitoring, predictive-maintenance, or released commercial platform.** The public site is still the legacy demo. A narrow Stage1 is a foundation, not permission to silently replace the founder's original goal or call all of it done.

This document audits the user's original request against the current code, prior-turn fresh execution, this-turn public HTTP/browser inspection, and specific remaining acceptance gates. It is a proposed release sequence, not authorization to deploy, contact factories, connect equipment, spend on providers, change keys or promise safety/accuracy. Existing files/databases remain preserved.

## Product and architecture contracts

Deliverable: requirements traceability, gap audit and proposed roadmap, not feature implementation. User-reported problem: the existing fake-data demo does not provide credible machinery understanding, maintenance or monitoring that a factory can pay for. Target: factory maintenance leads, technicians, stores staff and OT/reliability engineers in Nigeria; actual customer fit/purchase intent remains unvalidated. Product ambition: real equipment monitoring and evidence-based maintenance, with manuals/parts/team workflows and suitable web/mobile/desktop/cloud access.

Success for this audit: every named capability receives an explicit active/dormant/absent/unverified status and evidence gate; no test count is used to imply physical integration or validated predictions; local, public and sale-ready states are separated. Fact ledger: `docs/facts.md`. Out of scope this turn: implementation, deployment, mutation of public/customer systems, actual invitations, hardware polling or AI inference.

Keep the existing modular Flask API + PostgreSQL + React client + separate durable workers. Future telemetry must enter an authenticated tenant/device boundary through a commissioned read-only edge connector, not through re-enabled public legacy routes. Measurement freshness/quality and human maintenance state are separate; predicted condition is a third evidence-gated layer. No second business backend, native app fleet, unrestricted MCP or Kubernetes just to satisfy feature wording.

## Evidence boundaries

1. **Public legacy deployment**: fresh unauthenticated GET checks, exit0, `https://machivital.vercel.app/` returned200 with title `Mechavital — Autonomous Machinery Vitality & Telemetry`; HTML contains `admin [admin]`, old asset/protocol/GRU training controls, a default machine marker and a static35-minute advisor repair window. Some inspected text is inside hidden dialogs: HTML presence is not proof it is visible, working or predicting anything. `/api/latest-states` returns200 JSON with `predictions`, `kpis`, `event_log` and operational fields. `/signup`, `/api/v1/auth/me`, `/api/v1/csrf`, `/readyz` each404. New local secure runtime is **not** deployed there. No public mutation or AI request made. Private raw evidence: `.pilot/vision-audit-20261112/`.
2. **Local Stage1 software**: prior turn freshly passed88backend tests364.74s,31frontend tests plus typecheck/lint/build,4serialEdge journeys2.8m,22realAPI assertions, pinned-container parser containment. Exact commands, preserved initial failures and release limits: `docs/SECURITY_REMEDIATION_VERIFICATION_2026-11-12.md`. This turn is a cross-check, not a second claimed full test rerun.
3. **Original data preservation**: this turn checker exit0 confirms24originalPostgreSQLtables/9protectedfiles unchanged; HEAD6539ad2 on `feat/machivital-private-pilot`. Original pilot stays`pilot_0001`; restored verification copy alone is`pilot_0002`. Do not run original API against new code/schema mismatch. No provider keys changed.
4. **Customer/hardware truth**: synthesized personas/fixtures are not customers. Last recorded fact is no equipment/representative data access; availability must be reconfirmed before commissioning. No actual monitored factory, accuracy, avoided failure, downtime savings, payment, funding, customer acceptance or native-store install is established.

## Public truth and current design cross-check

The deployed `/static/js/dashboard.js?v=4.0` was fetched with GET200, not executed. `fetchHistory` falls back to `generateRealisticHistory` on missing/error history; that function generates sensor history from `Math.random` and a sine trend (private captured source lines1070–1105). This is direct deployed-source evidence of fabricated history, not merely the user's aesthetic opinion. The deployed connector helper still falls back to `dev-api-key`; no ingest/action was called. There is no approval here to patch the live deployment.

This-turn local GET `/api/v1/assets/1` returned200 with `telemetry_status=not_connected`, machine metadata only. At1280px the machine registry has44px action buttons and no page overflow; it is a searchable table, not spatial layout/drag configuration or live monitoring. At375px the team table has internal horizontal overflow: initially name/email are visible while role/access actions require sideways scrolling. That is usable as a technical table but weaker than a phone-first technician/team experience. Screenshot `tests/screenshots/vision-audit/team-mobile-20261112.jpg`; design acceptance needs task-based phone review, not just page-width assertions or full-desktop screenshots. No UI restyling was performed.

`DESIGN.md` still calls autonomous surveillance, GRU RUL and exact root-cause prediction 'Product Truth'; its dark control-room spec is historical, not the current warm Barlow/Source Sans workbench or verified product. README's historical sections still say 'Feature-complete', precise failure minutes, sub50ms inference and zero unplanned stoppages. Their disclaimer prevents some confusion but does not make these claims valid; future release docs should isolate history rather than let buyers/agents read it as present capability. The Stage1 PRD says a later approved roadmap exists, but no full original-vision roadmap has been found in current docs; this report must make deferred requirements explicit instead of letting them disappear.

## Traceability matrix

Read-only independent source scan completed and important claims spot-checked directly. It ran no tests, legacy scripts, hardware or providers. `app/__init__.py` delegates to the pilot factory; factory registers only auth, registry, maintenance and documents. Existing PRD explicitly excludes connectors, predictions, recurring PM, stock, AI/MCP, saved layouts and native distribution (`docs/PRD.md:29–33`). Exclusion from Stage1 is not fulfillment of the original request.

| Original requirement | Current status | Evidence / exact gap |
|---|---|---|
| Credible software to sell to factories | Local foundation; commercial release held | Current source+fresh local tests exist, but production package, clean environment/staging, supervision, recovery, data/support agreement and buyer acceptance missing. Local untracked additions do not constitute a released artifact. `docs/RELEASE_GATES.md:7–20`. |
| Good signup, private company/team access | Implemented and locally exercised | `app/pilot/auth.py:104–135`, `frontend/src/Auth.tsx:89–156`, security membership checks; verification/MFA/recovery/tenant/invite/offboard tests. Live site's signup404 and no new auth endpoints; production deliverability/onboarding unproved. |
| Good machine arrangement | Metadata/search/location organization implemented; layout incomplete | `app/pilot/registry.py:11–20,51–68,97–139`; `frontend/src/Machines.tsx:35–62,167–186`. Site/Area/Line, code/name/model/serial/criticality/archive, no connector or saved spatial arrangement. |
| Drag/drop components and arrangements | Absent | `frontend/src/Maintenance.tsx:452–481` is links grouped by job status, not drag transitions or saved layout. Legacy CSV file-drop is not component rearrangement. No layout schema/API/persistence/keyboard alternative. |
| Easy different-machine connectors | Dormant prototypes; absent active ingress; hardware unverified | Legacy `app/api/ingest.py:202–303`; Modbus/MQTT scripts target disabled old endpoint. `registry.py:20` always emits not_connected. No active onboarding/revocable tenant-device identity/channel commissioning. No implemented OPC-UA connector found despite old UI listing it. |
| Real monitoring/history | Not delivered in active runtime | No active measurement ingest/trend/history; retained sensor schemas are not exposed APIs. Registered machine GET this turn returns metadata/not_connected. Deployed history fallback generates random data instead of unknown/error. |
| Predict failure/RUL/root cause | Dormant prototypes; validity not established | Legacy trainer generates synthetic degradation or missing-target defaults (`app/services/trainer.py:45–123`); predictor picks random fault when rules fail (`app/services/predictor.py:407–447`). No representative measured-failure holdout/uncertainty/site validation; artifacts/speed cannot close gate. |
| Download/read manuals | Implemented private text-PDF scope | `documents.py:31–94,117–137`, current sandbox worker and `frontend/src/Manuals.tsx:274–337`; actual scanner/parser/download tests. No manual discovery, OCR/image/diagram interpretation or non-PDF support. |
| Understand machine/manual and give AI failure advice | Absent/disabled | `app/services/llm_advisor.py:1–7` refuses old advisor; no active private retrieval, page-cited answers, consent/safety evaluation. PDF extraction alone is not machine understanding. |
| Maintenance alerts and time-organized logs | Real one-off due work/history; recurring/delivered alerts missing | `maintenance.py:15–27,105–123,159–230`, registry overdue counts. Due dates/checklist/notes/labor/review/events/export exist. No PM recurrence/meter plan, reminder/escalation, delivery/ack audit. Worker schedules mail/doc processing, not preventive maintenance. |
| Parts inventory | Absent | WorkOrder `app/pilot/models.py:53–79` has no stock transaction/consumption model. Legacy parts menu and parts_replaced JSON are not receipts/reservations/issues/returns/reorders. Stores persona tests viewing authorization only. |
| Helpful mascot/reminders | Absent | Branding/icons/toasts are not assistant behavior. No contextual due-work reminder logic/test; must not become fake safety status. |
| Companies connect AI through MCP | Absent | Web tenant auth is not product MCP; no transport/tools/client scopes/company consent/revocation/audit. Editor MCP does not count. |
| Web, phone, desktop, cloud, everything | Web/responsive browser local; broad distribution incomplete | Mobile-width browser tests do not prove native phone/PWA/offline. Desktop browser is not installer. No active service worker/offline queue/native build/signing/update/store pipeline. S3 adapter/WSGI entrypoint do not prove cloud deployment or clean package. |
| Nigerian factory adoption, promotion and funding | Ambition; no validated outcome | No named partner/customer acceptance/payment/retention/commissioned field outcome in facts ledger. Need discovery, approved pilot and measured evidence rather than invented adoption/funding claims. |

## Legacy source that must not be promoted as working capability

Verified directly: `scripts/edge/pdm_edge_agent.py:171–205` random-generates samples but logs 'live telemetry'; `:225–262` accepts stdin choice yet always invokes simulation. `app/api/machine_management.py:351–373` writes fixed96.8%accuracy/97.5%training accuracy/2.6hMAE as supposedly calibrated benchmark without measuring them. `app/services/predictor.py:443–447` randomly selects a fault. `app/services/trainer.py:54–66` replaces missing labels with normal/constant RUL; `:118–136` fits scalers and makes overlapping windows before validation separation. These are dormant local prototype paths, **not defects in the active secure pilot**, but cannot be transplanted to restore the original vision or cited as prediction proof. No model/joblib was deserialized or training run.

`PRODUCT.md:7–13` and `PILOT_DEPLOYMENT_PLAYBOOK.md:153–168` still state predictive/connector/advisor facilities as present/verified. Their old handcrafted telemetry tests are not physical commissioning. Record these as documentation drift; do not erase prior files or silently treat their statements as actual evidence.

## Preview attribution and audit limits

The API port5051 was already held by another local preview session. This turn's requested isolated API launch was assigned5052 but the fixed Python launcher still attempted5051; that new launch never became ready and was stopped. The web preview's existing5051 API served the read-only machine/team inspection; do not misattribute it as a freshly booted API or current-turn integration suite. Preview inventory identified the other session's running5051 service; it was left untouched. This turn's web/API launch attempts were stopped, mobile emulation reset. Original data fingerprint checks remained unchanged throughout. This is another reason to keep fixed-port/runtime assumptions out of release claims.

Only audit documents and a saved screenshot were changed in this turn. Build/test results cited are the preceding turn's freshly executed software gates, not new executions in this cross-check. This turn executed public GET/source checks, read-only source/DOM inspection, preserved-state checks and diff whitespace checks. No implementation, package installs, model inference, real equipment polling, deployment, commit/push or key change.

## Acceptance and priority checklist

- [x] Original requested capabilities traced to active/dormant/absent/unverified with source paths, no percentage-complete guess.
- [x] Public site read-only HTTP/source checked; old deployment separated from new local secure runtime, fake-history fallback confirmed.
- [x] Local machine GET and desktop/375px team flow inspected; weak phone ergonomics recorded with screenshot and computed dimensions (710px table in336px wrapper, offscreen40px role/access controls).
- [x] Existing88/31/4/22 local proof interpreted only within scope; original24tables/9protectedfiles preserved, no new test/inference/hardware claim.
- [ ] Original complete product delivered or ready to sell: **not passed**. Proposed sequence below needs a scoped implementation plan, release gates and real partner/OT commissioning evidence.

## Proposed release sequence: preserve the ambition, gate the claims

This is a recommendation, not an accepted implementation plan. Do not wait for prediction before providing genuine maintenance value, and do not spend months on optional inventory/native packaging while leaving the primary connected-machine promise without a commissioning path.

### 1. A truthful, supportable maintenance pilot

Close reproducible API/frontend/worker packaging, same-origin HTTPS/cookies/CSRF, real sender deliverability, scanner/parser least privilege, app-level DB+blob+key restore, customer export/retention/purge, incident ownership and buyer-approved scope. Add the missing recurring preventive-maintenance workflow: task plan, calendar interval, due dates/timezone, occurrence identity, assigned responsibility, notification delivery attempts and overdue escalation; scheduled work is never auto-completed. Add phone-first task views and keyboard alternatives before desktop-only rearrangement. Prepare, but do not send, a design-partner interview/onboarding brief. No fixed price, SLA, ROI or compliance badge without evidence.

Gate: clean isolated package boot; real mail to an explicitly authorized test mailbox; restore/sign-in/MFA/manual/history working; repeat schedule/restart/duplicate/missed occurrence/timezone tests; technicians complete a phone journey; a named partner agrees scope and support. May be offered as maintenance coordination only once these gates close, not failure prediction.

### 2. Prove real connection and useful monitoring on one authorized machine

Select actual OEM/model/PLC/sensor/access method with a consenting factory and competent OT engineer. One protocol and read-only adapter first; source-to-signal map specifies addresses/node IDs, types/units/scaling/endianness, safe polling load, timestamps and quality. Device identity bound to tenant/machine, revocable credentials, TLS, bounded store-and-forward/dedup, stale/no-data/invalid-clock and reconnect behavior. Collect trends and deterministic engineer-approved alarms with hysteresis/debounce, acknowledgment/clear state and maintenance link. No machine commands, arbitrary RPC, auto-reset or operating setpoints.

Gate: hardware-in-loop rehearsal then witnessed on-site commissioning for the named model; power/network disconnect/reconnect and invalid-data tests; measured sampling/latency/storage; explicit OT approval and no adverse equipment load. A simulator demonstrates protocol code only, not this gate. List exact supported models/configurations, never 'all machines'.

### 3. Improve the technician workflow: manuals, parts and saved workspace

Extend manual ingestion with version/OEM-model association, user-authorized upload/catalog, metadata and page provenance; add OCR only with confidence/quality controls. AI retrieval is optional and consented, tenant-private, page-cited, refuses missing/contradictory instructions, and labels advisory answers; retrieval is not permission to instruct unsafe machine work. Parts need receipt/reservation/issue/return/adjustment ledger and job linkage before reorder advice. Save per-user/per-role layout changes with schema versions/reset and keyboard reorder, not cosmetic drag-only animation. These are separate scoped changes, not a general ERP rebuild.

Gate: original manual checksum/version+page citation tests; foreign-document and injection negative controls; partial/missing OCR warnings; stock conservation and concurrent reservation/return tests; saved layout survives reload and organization switch without leakage; functional phone alternatives. A manual list/parts array is not an inventory ledger or AI understanding.

### 4. Validate prediction before selling prediction

Collect representative operating/failure/maintenance labels for a specified machine/fault. Compare persistence/rule/domain baselines before choosing a model. Split by time and equipment/site; prevent overlap/leakage; include normal conditions, maintenance interventions, missing channels and uncertainty. Evaluate event-level precision/recall, false alarms per operating period, detection lead time, calibration/coverage and missed failure costs. Agree acceptance limits with the OT/customer team before validation. Use shadow mode and review; unsupported machine/model states show 'prediction unavailable', not exact failure minutes.

Gate: held-out representative data and external/site validation, reproducible provenance/model versions, operational shadow evidence and documented limits approved for that specific claim. GRU files, public benchmark performance, training script exit0 or inference speed do not prove industrial accuracy or avoided downtime.

### 5. Distribution, company AI/MCP and growth after a working wedge

One responsive web product and shared backend first; controlled PWA/offline queue only after encrypted local-data lifecycle, replay/conflicts, logout/offboarding and synchronization tests. Desktop/native wrappers later if device/peripheral/offline requirements justify the cost; installers, signing, updates, mobile-store policies and backend support are real gates. Cloud/isolated on-prem are deployment choices, not five independent domain backends.

MCP initially read-only for a consenting organization, scopes bound to tenant/user/tool, client authorization, audit, token expiry/revocation, output minimization and untrusted-manual injection tests. Human confirmation and separate privilege for any future mutation; never expose machine-control commands to generic AI. Mascot earns its place through dismissible genuine due-work reminders, not safety assurances or fake operational status. Funding/promotion follows documented customer problem, usage/retention, authorized case study, willingness to pay and measured outcomes; no invented factory logos or ROI.

Gate: independent client/device/installer/offline/MCP-boundary tests and organizational approval; a real customer-value record. Broad Nigerian factory penetration and funding are outcomes to pursue, not checked software features.

## Grounding sources

- [ERPNext Asset Maintenance](https://docs.frappe.io/erpnext/asset-maintenance) and [Maintenance Log](https://docs.frappe.io/erpnext/asset-maintenance-log): separate recurring plan/occurrence from actual dated completion. [Stock Ledger](https://docs.frappe.io/erpnext/stock-ledger): auditable transaction movements, not a static parts list.
- [ThingsBoard IoT Gateway](https://thingsboard.io/docs/iot-gateway/), [Modbus](https://thingsboard.io/docs/iot-gateway/config/modbus/), [OPC-UA](https://thingsboard.io/docs/iot-gateway/config/opc-ua/) and [Alarms](https://thingsboard.io/docs/user-guide/alarms/): protocol mappings and per-device configuration, explicit read/write separation, deterministic condition-driven alarm lifecycle. Reference components need license/security/fit review before adoption; no download/clone/inference executed this turn. Gateway state/replay needs must be designed, not copied from a summary's 'stateless' suggestion.
- [NIST SP800-82 Rev3](https://csrc.nist.gov/pubs/sp/800/82/r3/final), September2023: OT has distinct safety, reliability and performance requirements. The retrieved landing page does not prove section-level control compliance; no certification implied.

All linked reference pages fetched successfully in this session. Their existence grounds proposed patterns, not Machivital compatibility or commercial outcomes.
