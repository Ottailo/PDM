# Public pilot publishing boundary

The public Vercel deployment is an informational page, not the private maintenance service. The user approved this boundary on 2026-11-12.

## What ships

`frontend/package.json` → `vercel-build` → standalone `frontend/pilot/index.html` and `src/pilot-main.tsx` → `dist-pilot`. The public entry imports the shared brand and informational page only, never the private workbench, identity queries, or API client. Fonts and mark are local build assets. Interactive disclosures and in-page navigation explain the maintenance workflow without fabricated records or telemetry.

The explicit single `@vercel/static-build` target in `vercel.json` prevents accidental Python entrypoint selection. `.vercelignore` permits only public frontend build source; original Python, environment, document, database, screenshot and runtime artifacts are excluded from the deployment upload. Source remains in Git for continued local pilot work. Private persona screenshots and prior private-workbench captures remain machine-local and ignored, even when they use synthetic identities. Only reviewed informational public-page screenshots are included in Git. No credentials or customer documents belong in Git.

API paths must return non-cacheable JSON with HTTP 503 and code `private_pilot_unavailable`, not successful HTML. Private/auth/old demo URL visits show the same public explanation. Missing generated asset URLs return 404 rather than HTML. Build output is ignored by Git.

## Local verification

Run `npm --prefix frontend run vercel-build` followed by `npm --prefix frontend run test:public-build`. Start `machivital-public-preview` using preview tools, then run `npm --prefix frontend run test:public-e2e`. The local preview middleware mirrors the API-unavailable contract; the Vercel routing result must also be verified on the actual deployment, since local middleware is not proof of CDN behavior.

Ordinary `npm --prefix frontend run build` still builds the real private workbench. Its existing isolated PostgreSQL/SMTP/scanner/worker rehearsal remains separate. Original pilot schema/data are not automatically upgraded or connected to Vercel.

## Git versus production

Pushing `feat/machivital-private-pilot` requests a branch preview through the existing Vercel Git integration. It does not merge `main` or promote the production alias `https://pdm-chi.vercel.app`. Record the exact commit and Vercel status/URL after the push; do not claim a ready preview solely because Git accepted the push.

Customer deployment and production backend release remain HOLD. See `RELEASE_GATES.md` for private hosting, production operations, email, storage, parser trust, recovery, data lifecycle and customer acceptance gates.

## Grounding

- Vercel route schema: https://vercel.com/docs/build-output-api/configuration
- Explicit build configuration: https://vercel.com/docs/project-configuration/vercel-json

Fresh run results are recorded in `VERIFICATION.md` and `STATE.md` after execution. `node scripts/pilot/verify_public_source.cjs` also rehearses the public build with only deployment-allowed source files and installed dependencies, with no private modules or inherited service environment. Public and private Playwright suites have separate output directories to avoid trace-file collisions.

The disposable loopback PM runtime has an explicit 500-attempt rehearsal allowance so repeated five-persona tests do not exhaust one shared IP's ten-minute login budget. This applies only to the namespace-validated local helper; `app/pilot/factory.py` retains its normal 30-attempt default. Abuse-limit denial remains covered by backend tests.
