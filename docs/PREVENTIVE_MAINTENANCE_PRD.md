# PM milestone PRD — local pilot 2026-11-12

The first useful planned-maintenance journey: a manager creates an anchored calendar task for registered equipment, the durable scheduler creates one accountable job, the assignee sees due work and a real captured email, a technician records work/checklist/labor, a manager reviews completion, and history/recovery remain intact. This is scheduled maintenance, not measured equipment condition or validated prediction.

## SHALL acceptance

| ID | Requirement | Execution proof needed |
|---|---|---|
| PM-01 | Authoritative tenant/MFA/capability + idempotent revisioned plan CRUD/pause/resume | Foreign/role/unknown fields/stale/duplicate denial tests |
| PM-02 | IANA timezone fixed-anchor day/week/month + month-end/leap/DST preview | Pure clock tests and browser local-vs-UTC preview |
| PM-03 | One unfinished order incl review; missed-period coalesce/audit; atomic dedupe/cursor/jobs | Concurrent/restart/missed/pause/edit/closure/reopen/archived tests |
| PM-04 | Explicit system provenance only schedule creation; human submit/review unchanged | DB constraint/event/lifecycle regression |
| PM-05 | Provenance-checked maintenance_mail and genuine accepted/failed/retry/cancelled/ack states | Real isolated Mailpit + refusal/retry/leases/offboard/forged intent/fairness |
| PM-06 | Phone visible44px team/PM/job actions and tenant cache/replay isolation |320/375/390px computed viewport + keyboard/persona screenshots |
| PM-07 | Explicit isolated runtime/foreground worker/status/port consistency, no keys inherited | NewDB/blob/mail/tempkeys + original fingerprint; safety negatives |
| PM-08 | Whole synthetic app restore DB+blob+separate matching key and safe job resume | MFA/history/checksum/PMcursor + wrongkey/corruptblob/incompatible schema negatives |
| PM-09 | Fresh all regressions after final changes, no fake hardware/data claims | Full serial backend/pinnedparser, frontend/nativecommands, realAPI/Edge, source review |

Existing normal work-orders/manuals/session controls retained. Only local Mailpit recipients. No auto-complete, no downtime/accuracy/safety/compliance promises. No new production provider/supervisor/package purchase. Release data lifecycle/legal/support/real sender/production parser trust remain held. Original connected/predictive vision continues next one-machine read-only commissioned milestone, not abandoned.

API/state: PREVENTIVE_MAINTENANCE_API.md and PREVENTIVE_MAINTENANCE_STATE.md. No acceptance passed merely by writing this PRD.
