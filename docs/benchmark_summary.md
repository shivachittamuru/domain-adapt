# DomainAdapt V1 Benchmark Summary

## Executive conclusion

DomainAdapt tested three levers for financial Text-to-SQL:

1. model capability;
2. runtime context engineering; and
3. supervised fine-tuning (SFT).

The strongest measured system was **GPT-5.6 Sol with the selected engineered
context**, at **17/24 correct (70.8%)** and **24/24 executable**. It improved by
one question over GPT-5.2 with the same context, preserved all prior successes,
and cost more tokens and latency.

The most important result was not that the largest model won. It was that:

- context engineering produced substantial gains for both weak and strong
  models;
- SFT v1 produced no accuracy gain over the untuned SLM under the same runtime
  contract; and
- once every query executed, the remaining errors were primarily semantic,
  not syntactic.

For V1, the evidence supports a strong one-shot model with verified runtime
context. If higher accuracy is required, the next experiment should be a
bounded validation and one-repair workflow—not another prompt-expansion or SFT
run by default.

## Fixed benchmark results

| System | Correct | Executable | Total tokens | Median latency |
|---|---:|---:|---:|---:|
| GPT-5.2 + minimal context | 11/24 (45.8%) | 24/24 (100.0%) | 9,081 | 1.827 s |
| GPT-5.2 + engineered context | 16/24 (66.7%) | 24/24 (100.0%) | 32,117 | 1.523 s |
| **GPT-5.6 Sol + engineered context** | **17/24 (70.8%)** | **24/24 (100.0%)** | **36,316** | **3.111 s** |
| Ministral-3B + minimal context | 1/24 (4.2%) | 10/24 (41.7%) | 8,254 | 0.940 s |
| Ministral-3B + engineered context | 7/24 (29.2%) | 17/24 (70.8%) | 34,241 | 1.079 s |
| SFT v1 + engineered context | 7/24 (29.2%) | 16/24 (66.7%) | 34,306 | 1.237 s |

Token totals measure traffic, not monetary cost. Prices differ by model,
provider, deployment type, and date.

## Working-set directional checks

| System | Correct | Executable |
|---|---:|---:|
| GPT-5.2 + minimal context | 4/12 | 12/12 |
| GPT-5.2 + engineered context | 6/12 | 12/12 |
| GPT-5.6 Sol + engineered context | 7/12 | 12/12 |
| Ministral-3B + minimal context | 1/12 | 5/12 |
| Ministral-3B + selected context | 4/12 | 8/12 |
| SFT v1 + selected context | 4/12 | 9/12 |

The working set was repeatedly inspected and exists for diagnosis. It is not a
generalization estimate.

## What each intervention contributed

### Context engineering

Context engineering supplied:

- explicit table relationships;
- plain-language column meanings;
- verified categorical values and casing;
- date and unit conventions;
- compact SQL-construction guardrails; and
- strict output-envelope normalization.

Measured effects:

| Model | Accuracy change | Executability change |
|---|---:|---:|
| Ministral-3B | 1/24 → 7/24 | 10/24 → 17/24 |
| GPT-5.2 | 11/24 → 16/24 | 24/24 → 24/24 |

The same context helped models at very different capability levels. Runtime
grounding and model intelligence were complementary.

### Supervised fine-tuning

SFT v1 used:

- 222 training examples;
- 85 validation examples;
- disjoint non-financial databases;
- the same inference contract used by the untuned SLM;
- two requested epochs with automatic batch size and learning-rate settings;
  and
- 327,830 billed training tokens.

The adapted model tied the context-engineered base model at **7/24** and reduced
executability from **17/24 to 16/24**. It therefore failed the predefined
promotion criterion.

This does not prove that SFT can never help. It shows that this particular
small, heterogeneous curriculum did not teach enough transferable behavior to
justify its training and deployment complexity.

### Stronger model capability

With the engineered context held fixed, GPT-5.6 Sol changed the frozen result
from **16/24 to 17/24**:

- 16 prior passes remained correct;
- one prior failure became correct;
- no prior success regressed;
- executability remained 24/24;
- total tokens increased by 4,199; and
- median latency increased by 1.588 seconds.

The upgrade strictly improved measured correctness, but the marginal gain was
small relative to the latency and token increase.

## Residual errors in the strongest system

GPT-5.6 Sol's seven failures were:

| Category | Count |
|---|---:|
| Unordered results differed | 4 |
| Ordered results differed | 2 |
| Output column count differed | 1 |
| Execution failures | 0 |

The system no longer had a SQL-validity problem. It had an intent-to-query
alignment problem: ranking, exact projection, predicates, aggregation, or
other semantic choices could still be wrong even when the SQL was valid.

That distinction determines the next engineering move. A parser or schema
checker cannot prove semantic correctness. Higher assurance requires
question-aware checks, result-shape checks, clarification for ambiguity, or a
bounded reviewer/repair step.

## Answers to the PRD's research questions

### What was solved by runtime context?

- schema relationships and legal join paths;
- opaque column meanings such as district `A11`;
- categorical literals such as `OWNER`, `M`, and `POPLATEK TYDNE`;
- stored date formats, units, and business-code meanings; and
- some output-format and SQL-construction discipline.

These facts vary by database and belong outside model weights.

### What was solved deterministically?

- leakage-safe split construction;
- reference-only compatibility transformations;
- read-only SQL execution and result comparison;
- strict one-fence output normalization;
- duplicate-ID and artifact-contract checks;
- resumable, atomic run persistence; and
- infrastructure-failure separation from correctness retries.

### What remained a model capability problem?

- translating nuanced intent into the exact query plan;
- producing exactly the requested columns;
- ranking and extreme-value semantics;
- aggregation and calculation choices; and
- preserving semantic constraints across multi-table questions.

### What did SFT improve?

SFT v1 did not improve frozen task accuracy. On the working set it slightly
increased executability, but that did not translate into additional correct
answers.

### Was SFT worth the complexity?

Not in V1. It added data curation, training, deployment, versioning, and
evaluation work without improving task success.

## Measurement limitations

- The frozen benchmark contains only 24 questions; differences of one question
  equal 4.2 percentage points.
- The same fixed benchmark was used for several post-baseline comparisons. It
  remains useful for consistent system comparison, but after its results were
  observed it should not be described as untouched.
- Provider-default generation and hosted models can vary between runs.
- Execution equivalence inherits the quality and assumptions of the reference
  SQL and compatibility rules.
- Token totals are not directly comparable to dollar cost across deployments.
- The hard subset contains only three questions.

## V1 decision

1. Do not promote SFT v1.
2. Use GPT-5.2 plus engineered context when latency and token efficiency matter.
3. Use GPT-5.6 Sol plus engineered context when the measured one-question
   quality gain justifies the additional latency and tokens.
4. If the application requires more than 70.8% accuracy, prototype a bounded
   generate → validate → one-repair workflow on development data.
5. Before tuning that workflow against individual failures, create a new
   untouched holdout if another confirmatory generalization claim is required.
