# Mega-Plan: A Planning and Deep-Research System

> **Note:** This is a reference methodology document, not the project `mega-plan.md` implementation plan. The project implementation plan is created from `.agents/skills/research-loop/templates/mega-plan.md` and populated in Phase 7 of the research workflow.

## 1. Core idea

A good plan is not merely a list of actions. It is a traceable map from the current state to a finished, verifiable outcome.

Use three rules:

1. **Design backward:** begin with the final outcome and ask what must be true for it to count as complete.
2. **Execute forward:** complete small tasks that produce objectives, phases, and ultimately the outcome.
3. **Adapt through evidence:** when research changes what is known, revise the plan rather than blindly following the original tree.

> Design top-down, execute bottom-up, and re-plan from discovered evidence.

A useful hierarchy is:

```text
Small task → objective → phase → final outcome
```

However, research projects require a second structure:

```text
Source → evidence → claim → research question → decision → final outcome
```

The first structure manages **work**. The second manages **knowledge and justification**. A strong research plan needs both.

---

## 2. The dual architecture

### 2.1 Planning tree: what must be done?

```text
Final outcome
└── Success criteria
    ├── Phase
    │   ├── Objective
    │   │   ├── Task
    │   │   └── Task
    │   └── Phase gate
    └── Final acceptance gate
```

This is similar to a Work Breakdown Structure (WBS): the total scope is decomposed into manageable deliverables and work packages. Apply the **100% rule** at each parent node: its children should cover all work required by the parent, without unexplained gaps or unnecessary overlap.

### 2.2 Evidence graph: why should the result be believed?

```text
Final decision or conclusion
├── Claim A
│   ├── Supporting evidence
│   ├── Counterevidence
│   └── Remaining uncertainty
└── Claim B
    ├── Supporting evidence
    ├── Counterevidence
    └── Remaining uncertainty
```

Every important conclusion should be traceable through this chain:

```text
Conclusion → atomic claim → exact source passage → original source
```

A planning tree without an evidence graph can produce an organized but unreliable report. An evidence graph without a planning tree can produce valid fragments but never finish the project.

---

## 3. Vocabulary

| Term | Meaning | Completion test |
|---|---|---|
| Final outcome | The finished deliverable or changed state | Would a reviewer agree that the project is complete? |
| Success criterion | A measurable property the outcome must satisfy | Can it be evaluated as pass, partial, or fail? |
| Phase | A major state transition in the project | Is there a reviewable artifact and a gate? |
| Objective | A verifiable result inside a phase | Is there evidence that the objective was achieved? |
| Task | A concrete action small enough to execute | Can one owner complete it in a focused session? |
| Dependency | Something that must exist before another item can proceed | Is the predecessor relationship explicit? |
| Research question | A bounded unknown whose answer supports a decision | Is its scope and expected answer form clear? |
| Hypothesis | A tentative answer that can be supported or refuted | Is disconfirming evidence specified? |
| Claim | An atomic assertion made in the synthesis | Can it be checked independently? |
| Evidence | A source passage, observation, dataset, or result supporting or challenging a claim | Is its provenance preserved? |
| Gap | Missing information or reasoning needed for a reliable conclusion | Is its impact and next action recorded? |
| Gate | A review condition before continuing | Is the pass rule explicit? |

---

## 4. When research is actually deep

Deep research is not defined by report length, search count, or the number of citations. The strongest formal characterization in the downloaded literature uses two dimensions:

1. **Search intensity:** many scattered information units must be located and processed.
2. **Reasoning intensity:** finding, interpreting, comparing, or combining those units requires non-trivial reasoning.

Use this classification:

| Situation | Appropriate method |
|---|---|
| One stable fact from an authoritative source | Direct lookup |
| A bounded comparison across a few known sources | Focused research |
| Many scattered sources plus synthesis, conflict resolution, or multi-step reasoning | Deep research |
| A novel causal or performance claim requiring new data | Empirical experiment, possibly preceded by deep research |

A task is deep when it requires broad and branching exploration, not when a simple answer is padded into a long report.

### Deep-research entry test

Mark a task as deep when most of the following are true:

- The answer cannot be obtained reliably from one source.
- The question has several dimensions or competing explanations.
- Relevant evidence is scattered, heterogeneous, or difficult to retrieve.
- Sources may disagree or use incompatible definitions.
- The answer requires synthesis rather than extraction.
- Missing evidence could materially change the decision.
- The result must survive an external audit.

---

## 5. Building the plan backward

### Step 1: Write the outcome contract

Define:

- The final deliverable.
- The user or decision-maker.
- The decision the deliverable should enable.
- Included and excluded scope.
- Time horizon and freshness requirements.
- Constraints: time, cost, tools, data, ethics, and quality.
- Success criteria and acceptance reviewer.

Bad outcome:

> Research transformers.

Better outcome:

> Produce a source-backed decision memo selecting one transformer architecture for dataset X, under compute budget Y, with explicit trade-offs, unresolved risks, and a reproducible evaluation plan.

### Step 2: Convert success into a rubric tree

Ask: **What must be true for the final outcome to pass?**

```text
Final outcome passes
├── Requirement A is satisfied
│   ├── Criterion A1
│   └── Criterion A2
├── Requirement B is satisfied
└── Critical risks are addressed
```

Rubric leaves should be directly checkable. They later become phase gates, research questions, or verification checks.

### Step 3: Define phases as state changes

A phase should end with a reviewable change in project state, not merely elapsed activity.

Examples:

- Scope approved.
- Evidence map complete.
- Candidate approaches compared.
- Prototype validated.
- Final recommendation audited.

### Step 4: Define objectives as artifacts or verified states

Prefer:

> Comparison matrix covering accuracy, cost, implementation risk, and evidence strength is complete.

Avoid:

> Investigate architectures.

### Step 5: Decompose objectives into executable tasks

Stop decomposing when a task has:

- One clear action.
- One owner or agent.
- One expected output.
- Known inputs.
- A visible completion condition.
- A size suitable for one focused work session.

### Step 6: Map dependencies

Do not assume every task is sequential. Record:

- Hard dependency: B cannot begin until A finishes.
- Information dependency: B needs the answer produced by A.
- Soft dependency: B is easier after A but can proceed independently.
- Parallel branch: A and B can run concurrently.

The execution plan is therefore usually a dependency graph, not a simple checklist.

---

## 6. From objectives to research questions

Each research branch must justify its connection to the outcome:

```text
Research task
→ answers research question
→ supports or refutes claim
→ satisfies objective
→ satisfies success criterion
→ contributes to final outcome
```

If that chain cannot be written, the task is probably irrelevant or underspecified.

### Exploratory versus confirmatory research

Do not force a hypothesis too early.

| Research mode | Start with | Reason |
|---|---|---|
| Exploratory | Question tree and initial landscape scan | Premature hypotheses can create confirmation bias |
| Confirmatory | Explicit hypothesis and falsification criteria | The proposed explanation or choice is already clear enough to test |
| Mixed | Broad questions, then tentative hypotheses after the first evidence pass | Useful for most practical projects |

For every important research question, record:

```markdown
- ID:
- Parent objective:
- Question:
- Why it matters:
- Scope and exclusions:
- Expected answer form:
- Evidence needed:
- Evidence that could reverse the conclusion:
- Current status: open / partial / answered / contested
```

For a hypothesis, additionally record:

```markdown
- Tentative claim:
- Supporting rationale:
- Verification method:
- Disconfirming test:
- Expected observations if true:
- Expected observations if false:
```

---

## 7. The deep-research loop (internal stages)

A reliable process is iterative rather than search-then-summarize. The stages below are **internal to the research methodology** in this document and are independent of the workflow phases used by the `deep-research` plugin. To avoid confusion, these are labeled **Stage 0–9**, not "Phase 0–9".

```text
Scope
  ↓
Decompose questions
  ↓
Plan evidence needs
  ↓
Search and retrieve
  ↓
Extract atomic claims
  ↓
Verify and compare
  ↓
Synthesize provisional answer
  ↓
Find informational and logical gaps
  ├── material gaps remain → revise plan and search again
  └── stopping criteria met → final synthesis and audit
```

### Stage 0: Research contract

Lock down the question, intended decision, audience, scope, time boundary, deliverable, and acceptance criteria.

### Stage 1: Orientation scan

Learn the vocabulary, major schools of thought, landmark sources, and likely primary-source repositories. This is mapping, not final evidence collection.

### Stage 2: Question and hypothesis map

Build a question tree. Add hypotheses only where they improve search direction and can be challenged.

### Stage 3: Evidence plan

For each question, define:

- Required source types.
- Preferred primary sources.
- Time and jurisdiction constraints.
- Search branches and query variants.
- Minimum corroboration.
- Known disagreement or bias risks.
- Completion and stopping conditions.

### Stage 4: Retrieval and exploration

Search broadly enough to find competing evidence, then follow high-value branches. Preserve the query, URL, retrieval date, and reason each source was selected.

### Stage 5: Evidence extraction

Extract atomic claims and exact supporting passages. Do not collapse reading notes, source claims, and your own conclusions into one paragraph.

### Stage 6: Verification

Check entity identity, dates, definitions, source authority, source independence, claim-passage alignment, contradictions, and missing context.

### Stage 7: Provisional synthesis

Combine only verified and clearly labelled uncertain claims. State competing explanations rather than silently choosing one.

### Stage 8: Gap-driven re-planning

Classify each gap:

- **Informational gap:** a needed fact or source is missing.
- **Logical gap:** the evidence exists, but the reasoning link is incomplete.
- **Conflict gap:** credible sources disagree.
- **Scope gap:** the question or boundary is still ambiguous.
- **Method gap:** available evidence cannot answer the question reliably.

Prioritize gaps by their ability to change the final decision. Create targeted follow-up tasks only for material gaps.

### Stage 9: Final synthesis and audit

Write the final deliverable from the claim-evidence structure, preserve uncertainty, run the acceptance rubric, and disclose unresolved gaps.

---

## 8. Where the research skill belongs

The research skill is not merely a single box called “research.” It is an evidence-producing worker inside the planning loop.

```text
Planner
  → sends a bounded research brief
Research skill
  → returns an evidence packet
Verifier
  → checks claim-source alignment and conflicts
Gap analyst
  → identifies what is still missing
Planner
  → updates priorities, dependencies, and next tasks
```

### Research-skill input contract

Every call should include:

```markdown
## Objective link
[Which objective and success criterion this supports]

## Research question
[One bounded question]

## Decision enabled
[What will be decided with the result]

## Scope
- Included:
- Excluded:
- Time boundary:
- Geographic or domain boundary:

## Evidence requirements
- Preferred primary sources:
- Acceptable secondary sources:
- Minimum corroboration:
- Required counterevidence search:

## Expected output
[comparison, decision memo, evidence table, fact check, etc.]

## Stop condition
[What is enough, or what resource limit applies]
```

### Research-skill output contract

The output should be an evidence packet, not merely a summary or link list:

```markdown
## Answer
[Current best answer, bounded by the evidence]

## Atomic claims
### C1: [claim]
- Supports question:
- Evidence passage:
- Source:
- Source type:
- Supporting / contradicting / contextual:
- Status: trusted / uncertain / contested / refuted
- Reason for status:

## Counterevidence and alternatives
- [Competing claim and evidence]

## Synthesis
[How the claims combine; distinguish evidence from inference]

## Gaps and limitations
- [What remains unknown and why it matters]

## Recommended next action
[stop, verify, broaden, narrow, experiment, or escalate]
```

A research output is complete only when the planner can use it to make a decision, create a targeted follow-up, or explicitly accept uncertainty.

---

## 9. The claim-evidence ledger

Maintain a ledger throughout the project:

| Claim ID | Atomic claim | Research question | Source and passage | Source type | Stance | Epistemic state | Notes |
|---|---|---|---|---|---|---|---|
| C1 | [claim] | RQ1 | [URL/DOI + passage] | Primary | Supports | Trusted | Independently corroborated |
| C2 | [claim] | RQ1 | [URL/DOI + passage] | Primary | Contradicts | Contested | Definitions differ |
| C3 | [claim] | RQ2 | [URL/DOI + passage] | Secondary | Context | Uncertain | Find original data |

Use explicit epistemic states:

- **Trusted:** checked against a source and adequately corroborated for its importance.
- **Uncertain:** partial support; a specific follow-up is required.
- **Contested:** credible evidence supports incompatible claims or interpretations.
- **Refuted:** contradicted by stronger evidence or failed verification.
- **Out of scope:** potentially true but irrelevant to the current contract.

Avoid unexplained numerical confidence scores. Numbers can imply calibration that does not exist. If a score is used, always include the evidence and rationale behind it.

---

## 10. Source and verification rules

### Source hierarchy

Prefer the source that owns the claim:

1. Original dataset, experiment, specification, law, filing, source code, or official record.
2. Peer-reviewed paper or authoritative technical report.
3. High-quality synthesis that clearly cites primary evidence.
4. Expert commentary.
5. General summaries, vendor marketing, or community discussion.

A secondary source is useful for discovery and interpretation, but important claims should be traced to primary evidence whenever possible.

### Verification checklist

For every material claim, ask:

- Does the source resolve and contain the cited material?
- Does the exact passage support the exact claim?
- Is the claim stronger than the source warrants?
- Is the source primary, secondary, promotional, or commentary?
- Are corroborating sources genuinely independent?
- Are dates, versions, entities, units, and definitions aligned?
- Is contrary evidence represented fairly?
- Is the information fresh enough for the decision?
- Is an inference being presented as a sourced fact?
- Would the conclusion survive removal of the weakest source?

Citation quantity is not a quality measure. A small set of primary, independently verified sources can be stronger than hundreds of loosely related links.

---

## 11. Gates and stopping rules

### Phase gate

A phase is complete only when:

- Its required artifact exists.
- Its rubric leaves are passed or explicitly marked partial.
- Dependencies for the next phase are satisfied.
- Important claims have evidence states.
- Material contradictions and gaps are recorded.
- A reviewer can decide whether to proceed, revise, or stop.

### Research stopping rule

Stop the research loop when all of the following are true:

1. Every critical research question is answered, explicitly unresolved, or transferred to an experiment.
2. Every decision-critical claim has adequate evidence.
3. Major counterarguments and competing explanations have been searched.
4. Material contradictions are resolved or transparently represented.
5. New searches mostly repeat known evidence or have low probability of changing the decision.
6. The acceptance rubric passes, or remaining failures are accepted and disclosed.
7. The time or resource budget has not been exceeded without explicit approval.

Do not confuse:

- **Absence of evidence:** “I have not found it.”
- **Evidence of absence:** “The available evidence supports that it does not exist.”

Stopping does not require zero uncertainty. It requires enough justified knowledge for the intended decision, plus transparent disclosure of residual uncertainty.

---

## 12. Progressive elaboration

A mega-plan should not attempt to predict every future action.

- Detail the current phase and the next phase thoroughly.
- Keep distant phases at milestone level.
- Expand a branch when its dependencies become clear.
- Re-plan when evidence changes assumptions, scope, feasibility, or priorities.
- Preserve old decisions and the evidence that caused revisions.

Update the plan when:

- A research result changes an assumption.
- A dependency or risk appears.
- A hypothesis is refuted.
- A critical source is unavailable or unreliable.
- An experiment becomes necessary.
- The expected value of another research branch changes.

A plan is a controlled model of the work, not a promise that initial guesses will remain correct.

---

## 13. Common failure modes

| Failure mode | Consequence | Correction |
|---|---|---|
| Giant static plan | Becomes obsolete after new evidence | Use progressive elaboration and gap-driven re-planning |
| Infinite decomposition | Planning replaces execution | Stop when tasks are executable and verifiable |
| Search-then-summarize | Produces broad but shallow reports | Extract claims, verify, synthesize, and analyze gaps |
| Hypothesis too early | Confirmation bias | Begin exploratory work with questions and alternatives |
| Source-count optimization | Many weak or redundant citations | Optimize claim coverage and source quality |
| Citation without passage checking | Unsupported claims look authoritative | Verify claim-passage alignment |
| One-source conclusion | Hidden bias or error dominates | Seek independent corroboration for material claims |
| Premature stopping | Low recall and missing evidence | Use explicit coverage and stopping criteria |
| Endless searching | Time spent without decision value | Stop when new evidence is unlikely to change the decision |
| Overly broad question | Unbounded research and incoherent synthesis | Lock scope, exclusions, and intended decision |
| Mixing fact and inference | Readers cannot audit reasoning | Label sourced fact, derived inference, and speculation separately |
| Forced certainty | Contested evidence becomes a false answer | Preserve trusted, uncertain, contested, and refuted states |
| Context compression without state | Uncertainty is accidentally converted into fact | Preserve evidence status and follow-up actions |

---

## 14. Reusable mega-plan template

```markdown
# Project

## 1. Outcome contract
- Final deliverable:
- Intended user:
- Decision enabled:
- Included scope:
- Excluded scope:
- Time boundary:
- Constraints:
- Acceptance reviewer:

## 2. Success rubric
| ID | Criterion | Priority | Pass condition | Status |
|---|---|---|---|---|
| S1 | | Critical | | Open |

## 3. Assumptions and risks
| ID | Assumption or risk | Impact if wrong | How it will be tested | Status |
|---|---|---|---|---|
| A1 | | | | Open |

## 4. Milestone plan (project phases)

These are project milestones, not the workflow phases used by the `deep-research` plugin. To avoid confusion, they are labeled **Milestone N** rather than "Phase N".

### Milestone 1: [state transition]
- Required artifact:
- Objectives:
  - O1:
- Tasks:
  - T1:
    - Supports objective:
    - Inputs:
    - Output:
    - Completion test:
    - Dependencies:
- Gate:
- Known research gaps:

### Milestone 2: [state transition]
- Required artifact:
- Objectives:
- Gate:

## 5. Research map
### RQ1: [bounded question]
- Parent objective:
- Why it matters:
- Scope and exclusions:
- Expected answer form:
- Evidence needed:
- Possible counterevidence:
- Status: open

#### H1: [optional tentative hypothesis]
- Verification method:
- Disconfirming test:
- Status: unverified

## 6. Research tasks
### RT1
- Research question:
- Search branches:
- Preferred primary sources:
- Freshness requirements:
- Minimum corroboration:
- Expected evidence packet:
- Stop condition:

## 7. Claim-evidence ledger
| Claim ID | Claim | RQ | Source passage | Stance | State | Follow-up |
|---|---|---|---|---|---|---|
| C1 | | RQ1 | | Supports | Uncertain | |

## 8. Gap register
| Gap ID | Type | Description | Decision impact | Next action | Priority |
|---|---|---|---|---|---|
| G1 | Informational | | | | High |

## 9. Decision log
| Date | Decision | Evidence used | Alternatives rejected | Residual uncertainty |
|---|---|---|---|---|
| | | | | |

## 10. Final audit
- [ ] Every critical success criterion is evaluated.
- [ ] Every critical research question has a disposition.
- [ ] Decision-critical claims have verified evidence.
- [ ] Counterevidence was searched and represented.
- [ ] Facts, inferences, and speculation are distinguished.
- [ ] Unresolved gaps and limitations are disclosed.
- [ ] Citations resolve and support their attached claims.
- [ ] The final recommendation follows from the evidence.
```

---

## 15. Compact operating procedure

When beginning any project:

1. Define the final outcome and decision.
2. Build the success rubric.
3. Decompose the outcome into phase-level state changes.
4. Identify unknowns blocking each objective.
5. Convert unknowns into bounded research questions.
6. Choose exploratory questions or confirmatory hypotheses appropriately.
7. Give each research task an evidence contract and stopping rule.
8. Store atomic claims and exact source evidence in a ledger.
9. Verify important claims and search for counterevidence.
10. Synthesize provisionally, identify gaps, and re-plan.
11. Stop when the rubric and evidence thresholds are met.
12. Audit the final output and disclose uncertainty.

The complete model is:

```text
Plan backward from the outcome
→ execute forward through tasks
→ research outward across evidence
→ verify inward toward claims
→ re-plan from gaps
→ finish through explicit gates
```

---

## 16. Research basis and caveats

The downloaded papers support several recurring ideas:

- Deep research combines high search intensity with high reasoning intensity; its core is claim discovery and synthesis rather than report length: [Characterizing Deep Research](papers/markdown/2508.04183.md).
- A common system pipeline is planning → question development → web exploration → report generation: [Deep Research: A Survey of Autonomous Research Agents](papers/markdown/2508.12752.md).
- Hypothesis-guided work, multi-source verification, gap-driven iteration, and traceable reasoning can strengthen the process: [Hypothesis-Driven Deep Research](papers/markdown/2605.10224.md).
- Explicit verification is necessary because early errors propagate and plausible-looking results can cause premature stopping: [Marco DeepResearch](papers/markdown/2603.28376.md).
- Completeness requires balancing recall and precision and reasoning explicitly about stopping: [DeepSearchQA](papers/markdown/2601.20975.md).
- Long research trajectories benefit from preserving trusted, uncertain, and untrusted (contradicted-by-other-sources) information separately: [QUEST](papers/markdown/2605.24218.md).
- Evaluation should cover factual accuracy, completeness and depth, objectivity, and citation quality: [DRACO](papers/markdown/2602.11685.md). ReportBench uses a two-axis frame focused on cited-literature quality and claim factual accuracy: [ReportBench](papers/markdown/2508.15804.md).

Treat these sources critically. The downloaded copies are recent arXiv versions, and some performance or novelty claims may not have independent replication. Several papers concern AI-agent engineering and benchmarks rather than a universally validated human research methodology. Their most transferable ideas are decomposition, explicit evidence state, verification, iterative gap analysis, and auditable stopping rules.

Planning foundations:

- Work Breakdown Structure and the 100% rule.
- Progressive elaboration: increase detail as knowledge becomes available.
- Backward planning: derive required intermediate states from the desired outcome.
