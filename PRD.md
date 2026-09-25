# DomainAdapt — Product Requirements Document

## 1. Project Summary

**Project name:** DomainAdapt  
**GitHub repository:** `domain-adapt`

DomainAdapt is a reference implementation for evaluating and improving small language models on domain-specific tasks.

The project is intentionally designed as more than a fine-tuning tutorial. Its purpose is to demonstrate a repeatable methodology for answering a harder architectural question:

> **When is a domain-specific problem best solved through prompting, retrieval, context engineering, deterministic agent-harness improvements, model adaptation, or some combination of them?**

The initial implementation will use a **financial-domain Text-to-SQL workload** because it provides:
- realistic enterprise-style domain specialization,
- strong public finance-oriented datasets,
- deterministic execution-based evaluation,
- no proprietary software dependency,
- clear opportunities for retrieval, context engineering, agent design, and fine-tuning,
- a workflow that generalizes to private APIs, CAD systems, healthcare, engineering, support, and other specialized domains.

The implementation domain is intentionally concrete, while the **DomainAdapt methodology remains domain-agnostic**.

The initial candidate SLM will be **Phi-4** or the most suitable Phi-4-family model supported by the chosen Azure/Foundry fine-tuning path at implementation time.

---

## 2. Primary Goal

Build and document an end-to-end domain adaptation workflow:

```text
Domain-specific system
       ↓
1. Freeze representative eval set
       ↓
2. Establish frontier model + current harness baseline
       ↓
3. Categorize failures
       ↓
4. Benchmark candidate SLM unchanged
       ↓
5. Measure capability gap
       ↓
6. Improve deterministic/context pieces
       ↓
7. Re-measure
       ↓
8. Apply SFT/LoRA to systematic model gaps
       ↓
9. Re-measure
       ↓
10. Consider advanced adaptation only if justified
```

The project should empirically show **what each layer contributes** rather than assume that fine-tuning is automatically the right answer.

---

## 3. Learning Objective

This project is both:

1. a **personal learning journey**, and
2. a **shareable reference implementation** for architects and engineering teams.

The implementation process should therefore optimize for understanding, not speed.

### Learning principles

- Build incrementally.
- Explain concepts before using them.
- Prefer notebooks for exploratory learning, benchmarking, data inspection, and experiments.
- Prefer small Python modules only when code has become stable and reusable.
- The learner should manually run and observe each meaningful step.
- Avoid GitHub Copilot or coding agents unless explicitly requested or the task becomes boilerplate-heavy.
- Do not hide important implementation details behind large generated code drops.
- Introduce one major concept at a time.
- Pause after every meaningful milestone for validation and reflection.
- Automate documentation, formatting, repetitive scaffolding, and low-learning-value work where useful.
- Move slowly through evaluation, model behavior, failure analysis, training data design, SFT, LoRA, and model comparison.

---

## 4. Core Research Question

> **How much of a frontier model's performance on a domain-specific workload can be recovered by a smaller model through better system design and model adaptation?**

Supporting questions:

1. How well does a frontier model perform with a reasonable domain harness?
2. How large is the capability gap when the same system uses Phi?
3. Which failures are caused by retrieval/context/harness design?
4. Which failures remain after deterministic improvements?
5. Which remaining failures are systematic and learnable through SFT?
6. What measurable uplift does SFT/LoRA provide?
7. What happens to latency, cost, reliability, and deployment flexibility?
8. When is fine-tuning worth the added operational complexity?
9. Which finance-domain semantics become learnable model behavior versus runtime context that should remain outside the weights?

---

## 5. Initial Domain: Financial Text-to-SQL

### Problem

Given:
- a natural-language financial/business question,
- an unfamiliar financial database,
- schema metadata,
- optionally relevant domain definitions/examples,

the system must generate SQL that produces the correct answer.

The V1 scope is **financial data research / analytics**, not equity valuation or investment recommendation. Example domains may include banking, transactions, cards, loans, accounting, insurance, funds, stocks, retail, and other finance-adjacent datasets represented in the selected benchmark.

Example:

```text
User:
"Which customers increased annual spending by more than 20%
while placing fewer orders than last year?"

       ↓
Schema/context retrieval
       ↓
Reasoning / query planning
       ↓
SQL generation
       ↓
SQL execution
       ↓
Result verification
```

### Why Text-to-SQL

It provides useful analogies to proprietary enterprise systems:

```text
General-purpose model knows SQL
but does not know
this organization's schema + business semantics.
```

This is analogous to:

```text
Model knows JavaScript
but does not know a proprietary CAD API.
```

or:

```text
Model knows Python
but does not know an organization's internal services.
```

---

## 6. Dataset Strategy

### Primary dataset family

Use **FINCH (Financial Intelligence using Natural language for Contextualized SQL Handling)** as the primary finance-oriented dataset family for DomainAdapt.

FINCH is well suited to this project because it:
- focuses specifically on financial Text-to-SQL,
- provides SQLite databases,
- contains natural-language / SQL pairs,
- includes multiple finance-related domains,
- supports deterministic execution-based evaluation,
- contains material derived from established benchmarks including BIRD,
- provides enough scale for both evaluation and later SFT experiments.

### Initial learning slice

Do **not** begin with the full dataset.

Start with a small, understandable database and a frozen evaluation slice.

The preferred first slice is the **BIRD `financial` database represented within FINCH**, because it is compact enough to inspect manually and already has a meaningful set of finance-domain questions.

This lets the project begin with:

```text
one financial database
→ understand schema
→ run reference SQL
→ build evaluator
→ establish baseline
→ inspect failures
```

Only after the evaluation pipeline is trusted should additional finance databases or larger training pools be introduced.

### Why not keep the domain open?

The **methodology stays generic**, but V1 should commit to finance so that:
- examples remain coherent,
- failure analysis becomes easier,
- domain semantics can be studied deeply,
- the fine-tuning hypothesis has a real specialization target,
- the final resource tells a clear story.

Future DomainAdapt implementations can reuse the same methodology with another domain.

### Evaluation versus training data

Maintain strict separation:

```text
Frozen eval data
    ≠
Training data
```

The initial frozen eval slice should never be used for SFT, few-shot selection, synthetic generation prompts, or training-data construction.

Training examples should come from disjoint partitions/databases where possible.

### Synthetic data policy

Synthetic data may later be used for **training augmentation**, not as the initial evaluation ground truth.

Synthetic examples should be accepted only after validation such as:
- SQL parses,
- SQL executes,
- schema references are valid,
- result semantics can be checked,
- duplicates/leakage are filtered.

Synthetic data should be introduced only after real failure analysis identifies a specific training-data gap.

### Dataset licensing

The repository should **not redistribute benchmark data unless its license explicitly permits that use**.

Prefer:
- download/setup scripts,
- dataset references,
- transformation code,
- locally generated metadata,
- benchmark configuration files.

Document source licenses clearly. FINCH is currently published under **CC-BY-NC-4.0**, so DomainAdapt should treat it as a research/educational dependency rather than bundle it as unrestricted commercial training data.

## 7. Evaluation Philosophy

Evaluation is a first-class product feature, not an afterthought.

### Primary metric

**Execution correctness / task success**

Generated SQL should execute against the target database and produce the expected result.

### Secondary metrics

Track where feasible:

- SQL execution success
- exact/result equivalence
- schema-selection accuracy
- table-selection accuracy
- column-selection accuracy
- syntax failures
- invalid identifiers
- reasoning/query-logic failures
- retrieval failures
- repair attempts
- tokens consumed
- latency
- inference cost
- number of model calls
- human intervention

### Failure taxonomy

Every failed evaluation should be classifiable into categories such as:

1. Retrieval failure
2. Schema-linking failure
3. Domain-semantic misunderstanding
4. Query-planning/reasoning failure
5. SQL syntax failure
6. Invalid table/column usage
7. Execution failure
8. Semantically incorrect result
9. Repair-loop failure
10. Other / ambiguous

The taxonomy may evolve as real failures are observed.

---

## 8. System Variants to Benchmark

The project should progressively compare:

### Variant A — Frontier baseline
Frontier model + minimal reasonable domain context.

### Variant B — Frontier + improved harness
Frontier model + retrieval/context/planning/validation improvements.

### Variant C — Phi baseline
Unmodified Phi + same baseline environment.

### Variant D — Phi + improved harness
Same deterministic/context improvements as the frontier system.

### Variant E — Phi + harness + SFT/LoRA
Fine-tuned Phi used within the same improved harness.

Possible later variants:

- teacher-generated synthetic augmentation,
- distillation,
- reinforcement fine-tuning,
- quantization,
- fully local inference,
- constrained decoding,
- alternative SLMs.

---

## 9. Initial Architecture

```text
Natural-language question
          ↓
      Domain context
          ↓
     Schema retrieval
          ↓
Relevant tables / columns
          ↓
    Query planning
          ↓
      SQL generation
          ↓
  Static/schema validation
          ↓
      SQL execution
          ↓
 Result-based evaluation
          ↓
 Failure classification
```

Start simpler than this and introduce components only when the baseline demonstrates a need.

---

## 10. Learning Journey / Milestones

### Milestone 0 — Environment and mental model

Goal:
Understand the project before building it.

Activities:
- repo setup,
- Python environment,
- notebook workflow,
- dataset overview,
- SQLite/DuckDB basics as needed,
- evaluation architecture,
- inspect several example tasks manually.

Deliverable:
`00_project_orientation.ipynb`

Validation:
Learner can explain the data flow and run a reference SQL query manually.

---

### Milestone 1 — Dataset and deterministic evaluator

Goal:
Build the measurement foundation before introducing an LLM.

Activities:
- acquire a small FINCH/BIRD-financial subset,
- inspect financial schemas/questions/reference SQL,
- execute reference queries,
- implement result normalization/comparison,
- create frozen development/evaluation slices.

Deliverables:
- `01_dataset_and_eval.ipynb`
- small reusable evaluation module if justified.

Validation:
Reference SQL passes the evaluator.

---

### Milestone 2 — Frontier baseline

Goal:
Establish a strong-model reference point.

Activities:
- simple prompt,
- supplied schema/context,
- SQL generation,
- execution,
- score the frozen eval set,
- inspect failures manually.

Deliverable:
`02_frontier_baseline.ipynb`

Validation:
Produce first benchmark table and failure examples.

---

### Milestone 3 — Failure taxonomy

Goal:
Understand *why* the baseline fails.

Activities:
- manually inspect failures,
- build categories,
- quantify failure distribution,
- distinguish system/context failures from reasoning/model failures.

Deliverable:
`03_failure_analysis.ipynb`

Validation:
Every sampled failure has an evidence-backed category.

---

### Milestone 4 — Phi baseline

Goal:
Measure the domain capability gap.

Activities:
- run the same frozen evaluation with Phi,
- keep prompt/context comparable,
- compare frontier vs Phi,
- classify incremental failures.

Deliverable:
`04_phi_baseline.ipynb`

Validation:
Capability-gap report.

---

### Milestone 5 — Harness improvements

Goal:
Recover performance without changing model weights.

Possible experiments introduced one at a time:
- schema retrieval,
- better schema representation,
- domain glossary,
- few-shot examples,
- explicit query planning,
- SQL/schema validation,
- execution feedback,
- bounded repair loop.

Deliverables:
- one notebook per meaningful experiment or a clearly segmented notebook,
- `05_harness_improvements.ipynb`.

Validation:
Measure incremental gain from each change.

---

### Milestone 6 — Identify residual model gaps

Goal:
Decide whether fine-tuning is justified.

Activities:
- inspect remaining Phi failures,
- isolate systematic/repetitive model behavior,
- define adaptation target,
- formulate hypothesis for SFT.

Deliverable:
`06_adaptation_hypothesis.ipynb`

Example hypothesis:

> Given correct schema context, Phi systematically struggles with multi-table aggregation and domain-semantic mappings. SFT on verified examples of these patterns should improve execution accuracy without changing retrieval.

No fine-tuning begins until this hypothesis is evidence-backed.

---

### Milestone 7 — Training-data design

Goal:
Learn how to create high-quality SFT data.

Activities:
- understand chat/SFT format,
- select public examples,
- prevent eval leakage,
- normalize prompts,
- inspect token distributions,
- decide train/validation splits,
- optionally create verified synthetic augmentation.

Deliverable:
`07_training_data.ipynb`

Validation:
Manually inspect a representative training sample set before training.

---

### Milestone 8 — SFT with Phi on Azure / Foundry

Goal:
Perform the first model adaptation experiment.

Activities:
- configure Foundry fine-tuning,
- understand SFT objective,
- understand how LoRA/PEFT is used in the chosen training path,
- select conservative hyperparameters,
- launch training,
- observe loss/validation metrics,
- save configuration and provenance.

Deliverable:
`08_phi_sft.ipynb` plus training configuration/notes.

Validation:
Successful custom model artifact and documented training run.

---

### Milestone 9 — Post-SFT evaluation

Goal:
Measure the incremental value of adaptation.

Activities:
- deploy/run adapted model,
- execute identical frozen eval,
- compare with all previous variants,
- analyze gains and regressions by failure category.

Deliverable:
`09_sft_evaluation.ipynb`

Key comparison:

| System | Task success | Exec success | Domain errors | Latency | Cost |
|---|---:|---:|---:|---:|---:|
| Frontier baseline | TBD | TBD | TBD | TBD | TBD |
| Frontier + harness | TBD | TBD | TBD | TBD | TBD |
| Phi baseline | TBD | TBD | TBD | TBD | TBD |
| Phi + harness | TBD | TBD | TBD | TBD | TBD |
| Phi + harness + SFT | TBD | TBD | TBD | TBD | TBD |

---

### Milestone 10 — Conclusions and reusable playbook

Goal:
Extract principles that transfer beyond SQL.

Questions:
- What was solved by retrieval/context?
- What was solved deterministically?
- What remained a model capability problem?
- What did SFT improve?
- What did it fail to improve?
- Was the uplift worth training/deployment complexity?
- Which lessons generalize to private APIs, CAD, finance, healthcare, engineering, and other domains?

Deliverables:
- final README,
- architecture diagram,
- benchmark summary,
- reusable domain-adaptation decision framework.

---

## 11. Repository Structure

Start lightweight:

```text
domain-adapt/
├── README.md
├── PRD.md
├── pyproject.toml
├── .gitignore
│
├── notebooks/
│   ├── 00_project_orientation.ipynb
│   ├── 01_dataset_and_eval.ipynb
│   ├── 02_frontier_baseline.ipynb
│   ├── 03_failure_analysis.ipynb
│   ├── 04_phi_baseline.ipynb
│   └── ...
│
├── src/
│   └── domain_adapt/
│       └── ...
│
├── tests/
│   └── ...
│
├── data/
│   └── README.md
│
└── docs/
    └── ...
```

Do not create modules prematurely. Start in notebooks; extract reusable code only after a pattern stabilizes.

---

## 12. Technology Preferences

Initial preferences:

- Python
- `uv` for environment/package management
- Jupyter notebooks for learning and experimentation
- SQLite or DuckDB for local deterministic execution
- Azure / Microsoft Foundry for hosted model experimentation and fine-tuning
- Phi-4-family SLM
- one frontier model for reference baseline
- standard Python evaluation utilities
- Git/GitHub for versioning and public sharing

Specific frameworks should be added only when they solve an observed need.

Avoid introducing LangChain/LangGraph in the earliest phases unless orchestration complexity later justifies them.

---

## 13. Development Rules

1. **One slice at a time.**
2. Explain *why* before implementation.
3. Show the smallest useful code.
4. Let the learner run it.
5. Inspect actual output together.
6. Do not jump ahead after a failed validation.
7. End every slice with explicit validation commands/checks.
8. Record benchmark results before changing the system.
9. Never train on the frozen eval set.
10. Prefer measurable evidence over architectural assumptions.
11. Do not optimize prematurely.
12. Avoid Copilot-generated implementation unless explicitly requested.
13. Automate low-learning-value boilerplate freely.
14. Keep public/reproducible alternatives wherever possible.
15. Preserve enough experiment metadata to reproduce benchmark results.

---

## 14. Non-Goals for V1

Do not initially attempt:

- production-grade agent platform,
- large-scale distributed fine-tuning,
- multiple model families,
- reinforcement fine-tuning,
- DPO/RLHF,
- sophisticated synthetic-data pipelines,
- large vector infrastructure,
- production UI,
- Kubernetes,
- complicated observability stacks,
- enterprise authentication,
- exhaustive BIRD/Spider benchmarking.

These may be added only after the core experiment is complete.

---

## 15. Success Criteria

DomainAdapt V1 succeeds if it can clearly demonstrate:

1. a reproducible domain-specific benchmark,
2. frontier and Phi baseline performance,
3. an evidence-based failure taxonomy,
4. measurable gains from harness/context improvements,
5. an evidence-backed reason to attempt SFT,
6. a reproducible Phi SFT/LoRA workflow on Azure/Foundry,
7. a post-training evaluation on the untouched benchmark,
8. attribution of gains to system improvements versus model adaptation,
9. a concise transferable playbook for other domains,
10. a repository that another architect can follow and reproduce.

The most important outcome is not that fine-tuning wins.

The most important outcome is that the project can **prove when fine-tuning is useful and when it is not**.
