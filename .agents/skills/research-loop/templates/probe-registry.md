# Probe Registry

Tracks probe scripts generated during research and their execution status. Probes are the strongest form of evidence: they test claims by running code rather than reading about them.

The registry is read before every Phase 8 execution step. Pending probes for the active branch's P0/P1 unknowns must be run before any implementation step begins.

## Probe statuses

- `pending` — probe returned by deep-dive, not yet executed
- `passed` — probe ran and confirmed the claim
- `failed` — probe ran and contradicted the claim; the unknown should be marked `eliminated`
- `blocked` — probe cannot run in this environment (document the blocker and escalate for P0/P1)
- `not-applicable` — the unknown cannot be tested by a probe (e.g., deadline, rule interpretation)

## Entry format

```
### P<id>: <claim being tested>
- **Unknown ID:** U<id> (link to the unknown in `unknowns-registry.md`)
- **Status:** pending | passed | failed | blocked | not-applicable
- **Probe path:** `probes/<unknown-id>.py` (or `.sh`, `.js`, etc.)
- **What it tests:** one-sentence description of the claim
- **Script:** (include the full script or a reference to the file path)
- **Result:** (filled after execution) stdout / stderr / observation
- **Executed by:** (model / user / not run)
- **Blocked reason:** (filled if status is `blocked`)
- **Date:** (filled when created or executed)
```

## Pending probes

<!-- Add pending probes here. The orchestrator runs these before any Phase 8 implementation step. -->

---

## Completed probes

<!-- Move probes here after execution. Keep result visible. -->

---

## Blocked / not-applicable probes

<!-- Move probes here if they cannot be run or do not apply. Document why. -->
