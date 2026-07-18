# Mega-Plan: SAD-Lora-KV (Semantic-Aware Dynamic Low-Rank KV Cache)

Concrete implementation plan for the selected approach. Created from template in Phase 1; populated in Phase 7 and refined each iteration.

## 1. Goal restatement

- **Target:** Design a novel KV Cache optimization technique that achieves >4x compression over standard GQA while retaining <0.1 perplexity loss on reasoning tasks.
- **Constraints:** Max 60 minutes research/planning budget, runtime-compatible with standard PyTorch transformers.
- **Success criterion:** Formal formulation of SAD-Lora-KV and a defined HuggingFace prototype hook structure.
- **Kill criterion:** Low-rank reconstruction error exceeds acceptable variance, or compute overhead of dynamic gating scales worse than O(d).

## 2. Selected approach

- **Branch ID:** B1
- **Approach summary:** SAD-Lora-KV integrates low-rank latent projections (MLA-style) with a dynamic semantic gating vector that adjusts the latent rank compression coefficients on-the-fly based on the attention heads' entropy and token category (e.g. system commands, delimiters).
- **Why this approach was chosen:** It directly addresses the "accuracy wall" bottleneck of traditional eviction and the rigidity of static quantization.
- **Key unknowns resolved:** U1 (frontier of hybrid/latent compression), U2 (decode bandwidth constraints), U3 (transformers module prototyping).

## 3. Milestone plan

### Milestone 1: Math & Architecture Formulation
- **Required artifact:** SAD-Lora-KV LaTeX math and block diagram definitions.
- **Objectives:** Formalize the low-rank projection equations $K_c = W_{d\_k} h$ and the dynamic scaling gating factor $g(t)$.
- **Gate:** Verification of positional embedding (RoPE) decoupling constraints.

### Milestone 2: Hugging Face Attention Wrapper Prototype
- **Required artifact:** Wrapper python class for LlamaAttention KV cache override.
- **Objectives:** Implement hooks to inject dynamic compression during generation.
- **Gate:** Execution script runs mock inputs without OOM.

## 4. Risk and assumptions

| ID | Assumption or risk | Impact if wrong | How it will be tested | Status |
|---|---|---|---|---|
| A1 | Dynamic gating overhead is low | high latency | Profile runtime on GPU | Open |
| A2 | Positional info stays decoupled | bad attention scores | Compare attention matrix maps | Open |

## 5. Research questions

| ID | Question | Evidence needed | Status |
|---|---|---|---|
| RQ1 | | | Open |

## 6. Claim-evidence ledger

| Claim ID | Claim | RQ | Source passage | Stance | State | Follow-up |
|---|---|---|---|---|---|---|
| C1 | | | | | | |

## 7. Stop conditions

- Goal reached.
- All approaches exhausted.
- Time budget `halt` mode triggered.
- Human escalation triggered.
