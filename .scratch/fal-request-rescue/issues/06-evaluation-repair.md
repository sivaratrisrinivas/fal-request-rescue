# 06: Evaluation and repair

**What to build:** Measured eval run proving safety, disposition quality, and evidence linkage, with remaining failures documented.

**Blocked by:** 05 replay-live-actions.

**Status:** ready-for-agent

- [ ] Ten-case starter set passes before expanding to 60 (30/10/20, >=12 ambiguous, paraphrases in one split)
- [ ] All safety/spend cases pass; >=90% dispositions correct on supported held-out; every correction links evidence; no secret in stored input or export
- [ ] Unsupported claims, unsafe retry suggestions, leakage, wrong state interpretation, non-idempotent webhook handling fixed or logged as known failures
- [ ] Ambiguous scoring reported as disagreement with gold revision before any rate claim
