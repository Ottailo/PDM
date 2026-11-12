# Machivital Stage 1: maintenance without a sensor dependency

Status: Stage1 local foundation verified; PM extension implemented and locally verified (final106backend/61frontend/5Edge plus realPMAPI and whole-component restore proof). Current PM scope and proof: PREVENTIVE_MAINTENANCE_PRD.md, PM_VERIFICATION.md. Not released or factory-commissioned. Historical Stage1 criteria below remain preserved. The first customer is a general factory maintenance team in Nigeria. This is a proposed customer segment, not a validated market claim.

## Problem
Equipment details, manuals, assigned maintenance and completed service history need a shared dependable home. Staff should be able to do real work without connected sensors. The current demo's generated history and simulated work completion cannot provide this.

## First value journey
Owner creates a verified private account/organization, enables MFA, registers a site and machine, invites a technician, assigns a maintenance job, technician submits actual work evidence, planner reviews it, and the team retrieves the record and private manual after restart. The same asset name can exist safely at another factory.

## Acceptance criteria
| ID | The system SHALL | Proof required |
|---|---|---|
| ID-01 | Verify account ownership through expiring single-use email tokens; protect owner/admin with MFA | Auth integration and browser tests, expired/replayed token negative cases |
| ID-02 | Revoke sessions on logout/password reset, enforce CSRF and rate limits | Revocation/CSRF/retry tests |
| TEN-01 | Derive organization from current membership and prevent cross-organization references, reads and writes | Two organizations, duplicate names, foreign IDs and direct DB constraint tests |
| REG-01 | Persist optional machine model/serial/location and display name independent of ID; accept machines without sensors | Create/edit/reload browser proof |
| JOB-01 | Assign a real job, record start/block/resume/submission/review and immutable event history | API state-machine tests and technician journey |
| JOB-02 | Reject stale edits/invalid transitions and replay maintenance commands idempotently | Concurrency and conflicting idempotency tests |
| DOC-01 | Quarantine private PDFs, scan with a real configured malware scanner and parse in a bounded isolated process | Valid/corrupt/malicious/scan-unavailable fixtures, actual local scanner test |
| DOC-02 | Permit authorized manual download and page text reading only after processing; deny foreign/deleted documents | Private storage/download/browser tests |
| UX-01 | Render useful loading/error/empty states with no generated metrics, health, forecasts or diagnosis | Empty factory, service outage, mobile and keyboard screenshots |
| OPS-01 | Start without automatic tables/seeding or personal provider calls; migrate clean PostgreSQL, recover worker jobs | Empty-db/restart/recovery tests |
| SAFE-01 | Disable legacy public customer endpoints and retain old data untouched | Legacy endpoints rejected, source/data audit |

## Success targets (not achieved results)
One owner completes account-to-first-job rehearsal without developer intervention; technician submits work on a phone; evidence survives service restart; zero cross-tenant negative tests succeed. Timing and adoption targets will be agreed with a pilot sponsor rather than invented.

## Out of Stage 1
Spare-stock ledger, recurring PM, connected hardware, failure prediction, online learning, AI/manual Q&A, mascot, MCP, saved drag-layouts, offline writes, native application stores, billing, production deployment and outreach. Later roadmap is in the approved local plan; these are not shown as dead product controls.

## Release policy
Local software proof is not production approval. Before customer use: approved hosting, email delivery, backups and restoration, secrets rotation where necessary, data/support agreement, privacy/legal review, support owner and explicit release sign-off. Field monitoring requires equipment access and commissioning. Predictive claims require representative real data and held-out validation.
