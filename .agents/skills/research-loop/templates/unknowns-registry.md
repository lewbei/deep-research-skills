# Unknowns Registry

A persistent record of every open question, unknown, and thing-to-investigate that surfaces during the research loop. This file grows across iterations — new unknowns are added when discovered, resolved unknowns are marked with their answer + source.

The research loop reads this file at the start of each research round to decide what to investigate next.

## How to use

1. **When an unknown is discovered** (during research, execution, or planning), add it as a new entry below.
2. **At the start of each research round**, scan the open entries, pick the highest-priority one that blocks a decision, and research it.
3. **When an unknown is resolved**, update its status to the correct terminal state (`verified`, `empirically-validated`, or `eliminated`), record the answer + sources, and note which decision it unblocks.
4. **When an unknown is deferred**, mark it `deferred` with a trigger condition for when to revisit.

## Priority levels

- **P0 — blocking:** this unknown must be resolved before the next execution step. No workaround exists.
- **P1 — decision-critical:** this unknown changes which approach to take or how to configure it. Resolve before committing to an approach.
- **P2 — informative:** this unknown would improve the plan but is not blocking. Resolve when research budget allows.
- **P3 — curiosity:** interesting but not decision-relevant. Only resolve if it's cheap.

## Entry format

```
### U<id>: <question>
- **Status:** open | provisional | provisional-high-risk | verified | empirically-validated | deferred | eliminated
- **Priority:** P0 | P1 | P2 | P3
- **Context:** why this question exists (what triggered it)
- **Decision blocked:** what decision or step this unknown blocks
- **Hypothesis:** tentative answer (if any)
- **Answer:** (filled when resolved)
- **Sources:** (filled when resolved — list of URLs/passages that corroborate; include exact passages)
- **Verifier verdict:** (filled for P0/P1 — aligned / minor-drift / major-drift / inconclusive)
- **Search attempts:** (filled for `provisional`/`provisional-high-risk` — list up to 3 distinct attempts with channel, query, and result)
- **Probe script:** (filled if applicable — path + what it tests + result)
- **Resolved date:** (filled when resolved)
- **Deferred trigger:** (filled if deferred — what condition should trigger revisiting)
```

## Triangulation requirement

A P0 or P1 unknown must **not** be marked as `verified` based on a single source. To resolve a high-priority unknown:

- **Verified (`verified`):** ≥2 independent primary sources corroborate the answer, OR 1 highly authoritative source + 1 successful empirical micro-validation. For P0/P1 unknowns, the verifier must return `aligned` or `minor-drift` before marking `verified`.
- **Provisional (`provisional`):** only 1 source found after the first search round. The unknown is marked `provisional` and a Phase 8 execution step is injected to empirically test the claim before committing. Record the single source. For P0/P1 unknowns, invoke the verifier before marking `provisional`.
- **Provisional high-risk (`provisional-high-risk`):** after 3 distinct search attempts across different channels (e.g., Kaggle + arXiv + GitHub, or paper + code + docs), no second source was found. The unknown is marked `provisional-high-risk` and a Phase 8 **probe script** is mandatory to validate the claim before any dependent branch is committed. Also trigger a human escalation warning: "Single-source claim blocks [decision]. Proceed only if no other path exists." Record the 3 attempts in `Search attempts`.
- **Empirically validated (`empirically-validated`):** the answer was confirmed by execution (e.g., running code, testing the simulator, or a passing probe script) rather than by reading a source.
- **Eliminated (`eliminated`):** the answer was proven false by execution or a contradiction, or the question became irrelevant.
- **Deferred (`deferred`):** intentionally postponed; record the trigger condition for revisiting.

P2/P3 unknowns may be marked `verified` with a single source if the source is authoritative (official docs, peer-reviewed paper, competition rules). For single-source P2/P3 claims, still record the source as `provisional` if the source is a forum, blog, or unverified repo.

## Triangulation bypass rule (anti-deadlock)

Do not search forever for a second source. A "distinct attempt" means a search in a different channel class with a materially different query. The three required attempts must cover at least 3 of these channel classes: competition platform (Kaggle, leaderboard), code repository (GitHub), academic/official source (arXiv, paper, official docs), discussion/forum (Reddit, Discord, Stack Overflow), general web (blog, documentation).

After 3 distinct attempts:

1. If no second source exists, mark the unknown `provisional-high-risk` and record the 3 attempts.
2. Define a probe script (small executable test) that can validate the claim directly.
3. Execute the probe in Phase 8.
4. If the probe passes → mark the unknown `empirically-validated`.
5. If the probe fails → mark the unknown `eliminated` (the claim was false), and prune any dependent branches.
6. Always inform the user when a P0/P1 unknown is resolved via bypass rather than triangulation.

*Source: MoAgent framework (ai4d3.github.io/2025/papers/20_MoAgent) — evidence triangulation achieves 4x F1 improvement over single-source ReAct agents. Triangulation bypass is our pragmatic fallback for bleeding-edge/niche hackathon contexts where no second source exists.*

---

## Open unknowns

<!-- Add new unknowns here. Keep P0/P1 at the top. -->

### U1: [placeholder — replace with first real unknown]
- **Status:** open
- **Priority:** P3
- **Context:** template entry
- **Decision blocked:** none
- **Hypothesis:** none
- **Answer:** none
- **Sources:** none
- **Search attempts:** none
- **Probe script:** none

---

## Answered unknowns

<!-- Move resolved entries here. Keep the answer + source visible. -->

---

## Deferred unknowns

<!-- Move deferred entries here with their trigger conditions. -->

---

## Eliminated unknowns

<!-- Move entries here if the question became irrelevant (approach was pruned, scope changed, etc.). -->
