# 06: Evaluation and repair

**What to build:** Measured eval run proving safety, disposition quality, and evidence linkage, with remaining failures documented.

**Blocked by:** 05 replay-live-actions.

**Status:** ready-for-agent

## Comments

Implemented 2026-09-30 (ticket 06). New: deterministic `eval/generate.py`
(60 cases: 30/10/20, 17 ambiguous, families pinned to one split), `eval/run_eval.py`
(import → investigate → disposition → disposition/safety checks, JSON + markdown
report, exit 1 off-bar), 5 harness tests. Full run: 70 cases, accuracy 1.00,
held-out supported 11/11, safety clean — bar passes. case-01 gold revised to
need-information with note (no evidenced value exists to correct with).
No repairs needed; limitations logged in `eval/LIMITATIONS.md` (synthetic-family
optimism, live paths unproven). Full suite green; see commit.

- [ ] Ten-case starter set passes before expanding to 60 (30/10/20, >=12 ambiguous, paraphrases in one split)
- [ ] All safety/spend cases pass; >=90% dispositions correct on supported held-out; every correction links evidence; no secret in stored input or export
- [ ] Unsupported claims, unsafe retry suggestions, leakage, wrong state interpretation, non-idempotent webhook handling fixed or logged as known failures
- [ ] Ambiguous scoring reported as disagreement with gold revision before any rate claim
