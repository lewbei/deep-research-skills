# Proxy Log

A registry of every process reward proxy used to score hypothesis branches. A proxy is any cheap, measurable signal that stands in for the true goal. This file records why the proxy was chosen, whether it has been validated against the true outcome, and whether it is currently trusted.

## Proxy statuses

- `candidate` — proposed but not yet validated; may be used only for exploration, not for P0/P1 decisions
- `validated` — correlation with true outcome has been demonstrated; may be used for branch scoring
- `degraded` — correlation evidence has weakened or contradicted the proxy; must be recalibrated before reuse
- `rejected` — proxy is on the trivial-proxy ban list, or empirical correlation check failed; do not use
- `retired` — once valid but no longer relevant (e.g., goal changed); kept for audit

## Entry format

```
### PX<id>: <proxy name>
- **Status:** candidate | validated | degraded | rejected | retired
- **Branch:** B<id> or list of branches that use this proxy
- **True outcome:** the expensive/delayed goal this proxy stands in for (e.g., "final leaderboard Elo")
- **Proxy metric:** the cheap signal being measured (e.g., "mean search depth per move")
- **Causal chain:** 1-2 sentences explaining *why* this proxy is expected to cause or predict the true outcome
- **Domain / source:** paper, competition writeup, prior project, or agent hypothesis
- **Validation method:** how correlation was / will be checked
- **Validation evidence:** (filled after validation) data points showing proxy vs. true outcome
- **Correlation strength:** (filled after validation) PEARSON / SPEARMAN r value, or a qualitative label with justification
- **Gaming risk:** LOW / MEDIUM / HIGH — based on how many non-goal paths can produce a high proxy value
- **Known failure modes:** ways the proxy can improve without improving the true outcome
- **Ban-list check:** PASSED / FAILED — whether the proxy passes the trivial-proxy ban list
- **Decisions made with this proxy:** links to D<id> entries in `decision-log.md`
- **Retirement reason:** (filled if retired/degraded/rejected)
```

## Trivial-proxy ban list

The following proxies are not allowed for P0/P1 decisions:

| Category | Banned proxy | Why banned |
|----------|--------------|------------|
| Activity / effort | Lines of code written, files created, searches performed | Measures busyness, not outcome. |
| Self-consistency | Model agrees with itself across samples | Can be high while wrong. |
| Process compliance | Checklist items completed, phases reached | Gaming by checking boxes. |
| Training loss only | Validation loss decreases without leaderboard check | Overfitting proxy. |
| Uncoupled heuristic | Heuristic reward not tied to final metric | Optimizes wrong thing. |
| "It ran" | Script executed without error | Necessary but not sufficient. |
| Unbounded complexity | Number of parameters, ensemble size | Can grow without improving target. |
| Naive ensemble size | More models = better | Diminishing returns or overfit. |

## Active / candidate proxies

<!-- Add every new proxy here when it is first proposed. Do not move to validated without evidence. -->

### PX1: [placeholder — replace with first real proxy]
- **Status:** candidate
- **Branch:** B1
- **True outcome:** TBD
- **Proxy metric:** TBD
- **Causal chain:** TBD
- **Domain / source:** TBD
- **Validation method:** TBD
- **Validation evidence:** none
- **Correlation strength:** TBD
- **Gaming risk:** TBD
- **Known failure modes:** TBD
- **Ban-list check:** PENDING
- **Decisions made with this proxy:** none
- **Retirement reason:** none

---

## Validated proxies

<!-- Move proxies here after correlation evidence is recorded. Keep the evidence visible. -->

---

## Degraded / rejected / retired proxies

<!-- Move proxies here when the correlation breaks, the ban list rejects them, or they become irrelevant. Record the reason. -->
