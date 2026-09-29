# Training-Data Design for Supervised Fine-Tuning

This playbook explains how to turn raw examples into a small, trustworthy
supervised fine-tuning (SFT) dataset. It is intentionally domain-agnostic: the
same method applies to SQL generation, private-API usage, structured extraction,
classification, support workflows, engineering assistants, and other
specialized tasks.

The central idea is:

> SFT data is a behavioral curriculum, not a pile of input/output pairs.

A model learns the patterns demonstrated by its labels—including mistakes.
Data quality therefore means more than “the file loads” or “the answer
executes.” Every example should demonstrate a behavior that is correct,
relevant, stable, and safe to place in model weights.

## 1. Start with a falsifiable adaptation hypothesis

Do not begin by collecting everything available. First identify a stable model
behavior that remains weak after runtime context and deterministic workflow
improvements.

A useful hypothesis specifies:

- the remaining behavior;
- the conditions under which it occurs;
- why it belongs in model weights;
- the examples likely to teach it;
- the evaluation metric expected to improve;
- the regression limits that must not be crossed.

Example:

> Given accurate runtime documentation, the model repeatedly chooses invalid
> multi-step API call sequences. SFT on verified examples of dependency-aware
> call ordering should increase end-to-end task success without increasing
> unsupported parameters.

If the failure is caused by missing or changing information, fix retrieval or
runtime context instead. If it can be detected objectively, add deterministic
validation. Fine-tune only the stable behavior that the model must internalize.

## 2. Freeze evaluation before touching training data

Evaluation must be independent of training-data construction.

Protect more than the final scored rows. Exclude the entire evaluation source
family or database when practical, including:

- working/debug examples;
- frozen evaluation examples;
- neighboring records from the same protected schema;
- few-shot selection;
- synthetic-data prompts;
- label repair or augmentation prompts.

This produces a clean causal question:

> Did the model learn a transferable behavior, or did it encounter the test
> during data preparation?

Record protected identities in a manifest and enforce the boundary with code,
not memory.

## 3. Define the unit of learning

Decide what one demonstration means. A canonical record normally contains:

```json
{
  "messages": [
    {"role": "system", "content": "stable task contract"},
    {"role": "user", "content": "runtime context plus request"},
    {"role": "assistant", "content": "verified target behavior"}
  ],
  "metadata": {
    "source": "...",
    "record_id": "...",
    "split": "train",
    "behavior_tags": ["..."],
    "provenance": "..."
  }
}
```

Keep two representations:

1. **Canonical audit record:** messages plus provenance, decisions, and tags.
2. **Provider export:** only the fields accepted by the training API.

Never make the provider file the only source of truth; it usually loses the
metadata needed to investigate regressions.

## 4. Match training inputs to inference inputs

Training/serving skew occurs when the model is trained under one contract and
used under another. Reuse the production:

- system instructions;
- message roles;
- context structure;
- output envelope;
- identifier and formatting conventions.

If production receives retrieved documentation, train with documentation in
the same location and approximate format. If production must output only code
or JSON, targets should contain only code or JSON—not explanations or Markdown.

Do not train hidden chain-of-thought. Teach the observable behavior the system
needs.

## 5. Select sources for behavioral coverage

Choose source data according to the hypothesis, not raw record count.

Useful coverage dimensions include:

- simple and compositional cases;
- single-step and multi-step workflows;
- common and high-risk edge cases;
- exact output-shape requirements;
- calculations and conditional logic;
- multiple schemas, APIs, products, or document families;
- difficult negative or refusal cases where appropriate.

Structural similarity is useful when it teaches a reusable behavior. Domain
similarity alone is insufficient if the examples do not exercise the target
failure mode.

Prefer a small verified set over a large noisy set. Add synthetic data only
after a measured coverage gap is identified.

## 6. Split by the entity that could leak

Random row splitting is often too weak. Closely related rows can share templates,
documents, users, schemas, products, or time periods.

Choose the split unit that best tests transfer:

| Task | Stronger split candidates |
|---|---|
| Text-to-SQL | Database or schema |
| Private API generation | API family, service, or version |
| Support automation | Customer, product line, or issue family |
| Document extraction | Document template or organization |
| Medical/industrial workflows | Site, device family, or protocol |
| Time-sensitive prediction | Forward time window |

The validation set should answer: “Can the adapted behavior work on a meaningfully
unseen situation?”

## 7. Validate assets before validating examples

An example cannot be trusted if its dependencies are inconsistent. Validate:

- file existence and cryptographic hashes;
- database or document integrity;
- schema/documentation agreement;
- required tables, fields, tools, and versions;
- source and license provenance;
- compatibility with the intended runtime.

Reject an entire asset when its documentation cannot faithfully describe its
runtime. Training on incomplete context can teach hallucination or invalid tool
usage.

## 8. Use layered label validation

Validation should progress from cheap objective checks to expensive semantic
checks.

### Gate A — Structural validity

Examples should satisfy the task's output contract:

- parses successfully;
- contains one allowed operation;
- follows the required schema;
- contains no unwanted wrappers or explanations;
- uses valid tables, fields, tools, or labels.

### Gate B — Runtime validity

When execution is available:

- execute in a read-only sandbox;
- enforce time and resource limits;
- capture errors and result shape;
- flag empty, null-only, zero-only, or implausibly large results;
- never treat execution alone as correctness.

For non-executable tasks, use deterministic validators such as JSON Schema,
type checking, compiler checks, business-rule validation, or exact label sets.

### Gate C — Semantic validity

Ask whether the target actually fulfills the request:

- Are the correct entities or APIs used?
- Are required conditions represented?
- Is the requested output shape exact?
- Are calculations, units, ordering, and aggregation correct?
- Were assumptions invented?
- Could duplicate rows or omitted edge cases change the meaning?

This is the real label-quality gate. A perfectly executable wrong answer is a
high-confidence bad teacher.

## 9. Normalize only documented incompatibilities

Source labels sometimes encode assumptions from another runtime: casing,
date functions, quoting, dialect, enum spelling, or API version.

A safe compatibility rule is:

- narrow and deterministic;
- applied only to trusted labels;
- recorded alongside the original;
- revalidated after transformation;
- never applied silently to model predictions during evaluation.

Store:

- original target;
- compatible target;
- applied rules;
- before/after execution evidence;
- transformation version.

If evaluation repairs predictions, it measures the repair system—not the model.

## 10. Detect leakage and duplicates separately

Use multiple fingerprints because leakage has multiple forms:

- normalized exact-input hash;
- canonical exact-target hash;
- near-input similarity;
- template or structural target hash;
- source identity and lineage.

Interpret them differently:

| Match | Typical action |
|---|---|
| Protected input or target | Exclude |
| Cross-split near duplicate | Move or exclude |
| Same input and same target | Keep one |
| Same input and conflicting targets | Resolve or exclude |
| Different inputs with same target | Often keep as paraphrases |
| Same structural pattern | Usually keep; it teaches reusable behavior |

The reusable rule is: **deduplicate examples, not useful behaviors.**

## 11. Audit with deterministic risk-based sampling

Pure random sampling can select mostly easy examples. Build a reproducible audit
sample that covers:

- every source and split;
- each important behavior tag;
- difficult and high-risk records;
- transformed or manually corrected labels;
- long-context or long-output outliers;
- negative and boundary cases.

Rank candidates with a stable hash so the sample cannot be cherry-picked after
seeing the answers.

For every audited example, record one of:

- **keep** — label is semantically aligned;
- **correct** — evidence supports one unambiguous repair;
- **exclude** — ambiguous, wrong, or unverifiable;
- **escalate** — requires a qualified domain reviewer.

Manual corrections require written evidence plus the same structural and
runtime validation as original labels.

## 12. Measure coverage without gaming counts

Tag examples using observable structure or reviewed semantics. Compare the
training curriculum with the residual failure taxonomy.

Questions to ask:

- Does each hypothesized behavior have enough verified demonstrations?
- Does one source dominate the dataset?
- Are hard examples genuinely hard or merely noisy?
- Does validation cover the behaviors whose uplift will drive the decision?
- Are important negative cases absent?

Coverage is not balance for its own sake. Do not add weak data merely to make a
chart look even.

## 13. Inspect length with the actual target tokenizer

Characters or words are useful early proxies, but token limits and cost depend
on the eventual base model's tokenizer.

Before training, calculate:

- prompt tokens: median, p95, and maximum;
- target tokens: median, p95, and maximum;
- truncated-record count under the selected context limit;
- total trainable tokens;
- token distribution by behavior and source.

Do this after choosing the fine-tuning model. Using an unrelated tokenizer gives
false precision.

## 14. Version the complete data contract

A reproducible manifest should include:

- source dataset and asset hashes;
- license and intended-use constraints;
- protected evaluation definition;
- selection and split policy;
- normalization-rule versions;
- exclusions and corrections with reasons;
- prompt/instruction/context hashes;
- record and behavior counts;
- canonical and provider-file hashes;
- tokenizer and length statistics;
- known limitations and readiness status.

Avoid volatile timestamps in content-addressed artifacts unless time is part of
the experiment. Stable ordering and deterministic serialization make reruns
comparable.

## 15. Make an explicit go/no-go decision

### Minimum “go” criteria for a controlled research run

- evaluation was frozen first;
- no protected or cross-split leakage remains;
- assets and licenses are understood;
- every target passes structural validation;
- executable targets pass runtime validation;
- representative semantic review is complete;
- corrections and exclusions are auditable;
- input format matches inference;
- provider files and manifest are hashed;
- success and regression metrics were defined before training.

### Reasons to stop

- representative auditing finds unresolved systematic label errors;
- source documentation is incomplete or contradictory;
- validation is not meaningfully independent;
- the dataset does not cover the hypothesized behavior;
- most failures actually belong to retrieval, runtime context, or deterministic
  validation;
- licensing does not permit the intended use.

Stopping is not failure. It prevents an expensive training run from producing
an uninterpretable result.

## 16. Common failure modes

1. **Training on evaluation failures.** This measures memorization.
2. **Equating execution with correctness.** Wrong programs often run.
3. **Repairing predictions during evaluation.** This inflates model quality.
4. **Random row splitting related records.** This leaks templates and context.
5. **Using a different prompt format for training and inference.** This creates
   training/serving skew.
6. **Keeping metadata only in notebooks.** Decisions become unauditable.
7. **Adding synthetic volume before understanding gaps.** This amplifies unknown
   assumptions.
8. **Keeping ambiguous labels because they are scarce.** Ambiguity is not useful
   supervision.
9. **Optimizing training loss instead of task success.** Lower loss may not
   improve the real workflow.
10. **Treating SFT and LoRA as alternatives.** SFT is the learning objective;
    LoRA is one parameter-efficient way to perform it.

## 17. Compact reusable checklist

```text
[ ] Write the adaptation hypothesis
[ ] Freeze and manifest protected evaluation
[ ] Define the canonical SFT record
[ ] Select sources for behavior coverage
[ ] Split by leakage-relevant entity
[ ] Validate licenses and runtime assets
[ ] Parse/type-check every target
[ ] Execute or deterministically validate every target
[ ] Normalize only documented label incompatibilities
[ ] Detect protected, cross-split, exact, and near duplicates
[ ] Measure curriculum coverage
[ ] Run deterministic risk-based semantic review
[ ] Exclude failures; correct only with evidence
[ ] Match training and inference formats
[ ] Measure lengths with the selected model tokenizer
[ ] Export canonical data, provider JSONL, and a hashed manifest
[ ] Record go/no-go criteria before launching training
```

## Final mental model

Think of SFT data as a set of code reviews for model behavior:

- evaluation defines the exam;
- the adaptation hypothesis defines the lesson;
- runtime validation proves the demonstration can run;
- semantic review proves it teaches the right thing;
- leakage controls keep the exam independent;
- the manifest makes every decision reproducible;
- post-training evaluation determines whether the lesson transferred.

The goal is not to create the largest dataset. The goal is to create the
smallest dataset that provides credible evidence about whether adaptation adds
value.
