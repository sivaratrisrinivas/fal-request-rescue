# 07: Deployment and demo

**What to build:** Deployed replay-default app with published notes and a three-minute walkthrough showing value and limits.

**Blocked by:** 06 evaluation-repair.

**Status:** ready-for-agent

## Comments

Implemented 2026-09-30 (ticket 07). Deploy: `backend/Dockerfile`,
`frontend/Dockerfile` + nginx proxy, `docker-compose.yml` (replay default, no
keys baked in) — verified live through the proxy (health, UI, create →
investigate → disposition=correction → replay). Two real bugs caught by that
verification: schemas missing from the image, then container path layout —
both fixed (`schemas` copied in, fallback-aware `SCHEMA_DIR`). Notes:
`docs/ARCHITECTURE.md`, `docs/DATA.md`, `docs/DEMO.md`, `docs/ROI.md`
(scenario-labeled, arithmetic checked). Full suite green; see commit.

- [ ] App deploys locally via Docker with replay default; live path stays opt-in and capped
- [ ] Architecture and data notes published; schemas and doc snapshots pinned in repo
- [ ] Walkthrough covers report to diff to bounded test to export to timing/eval/ROI in ~3 minutes, then an ambiguous case showing need-information abstention
- [ ] Eval results and editable ROI inputs shown as scenario (`eligible × min-saved/60 × hourly`); no cash-savings claim without fal volume and labor confirmation
