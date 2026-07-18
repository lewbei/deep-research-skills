# Context Archive

Compressed summaries of eliminated hypothesis branches, abandoned approaches, and failed experiments. Full technical traces are moved here from the active `hypothesis-tree.md` and `decision-log.md` to prevent artifact bloat.

The active artifacts should only contain viable branches and their immediate context. This archive preserves the history without degrading the agent's ability to reason over current state.

*Source: "Lost in the Middle" (Liu et al. 2023) — LLMs exhibit 20-30% accuracy drop for information buried in the middle of long contexts. Keeping active artifacts small prevents this degradation.*

## How to use

1. When a branch is eliminated in Phase 6 (prune) or Phase 9 (kill criterion met):
   - Move the full branch details (approach, mechanism, predictions, results) here.
   - Replace the active `hypothesis-tree.md` entry with a single sentence: "Approach X failed due to Y, do not attempt."
   - Record the elimination reason in `decision-log.md` with a pointer to the archive entry.

2. When Phase 10 (terminal reflection) runs, scan this file for the compressed list of falsified hypotheses.

## Entry format

```
### A<id>: <approach name> (eliminated)
- **Eliminated in:** Phase 6 (prune) | Phase 9 (kill criterion)
- **Date:** 
- **Reason:** one sentence — why it was eliminated
- **Original prediction:** predicted score + confidence
- **Actual result:** what happened when tried (or "not tried — eliminated by evidence")
- **Full trace:** [link to mechanism file if it exists, or inline details]
- **Lesson:** what should be avoided in future attempts
```

---

## Eliminated approaches

<!-- Add eliminated branches here. Newest at the top. -->
