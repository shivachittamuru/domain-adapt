# Adaptation Hypothesis Playbook

## Purpose

This playbook explains how to decide whether a model should be fine-tuned after
prompting, grounding, and deterministic workflow improvements have been tried.
It is intentionally domain-agnostic: the same method can be applied to
Text-to-SQL, private API generation, domain-specific scripting, structured
document generation, and similar enterprise workloads.

The central principle is:

> Put changing facts in runtime context, objective checks in deterministic
> code, stable reusable behaviors in model adaptation, and genuine ambiguity
> in front of a human.

Fine-tuning is not the automatic next step after a model fails. It becomes a
reasonable experiment only when the remaining mistakes are systematic,
repetitive, and teachable.

---

## 1. The four places a solution can live

Before deciding how to fix a failure, determine where the fix belongs.

| Place | Use it for | Examples |
|---|---|---|
| Runtime context or retrieval | Facts that vary by customer, database, version, or time | Schemas, API signatures, valid enum values, business definitions, current documentation |
| Deterministic workflow | Properties that software can verify objectively | Syntax, schema references, required fields, compilation, safe execution, timeouts, output envelopes |
| Model weights | Stable, reusable behavioral skills | Following a supplied relationship graph, selecting exact outputs, using an API according to retrieved documentation, recurring calculation patterns |
| Human clarification | Questions with multiple reasonable interpretations | Ambiguous terminology, conflicting requirements, missing business intent |

### A quick routing test

For every failure, ask:

1. Could the relevant fact change for another customer, database, or version?
   Keep it at runtime.
2. Can ordinary code determine correctness with certainty? Implement a
   deterministic check.
3. Is the weakness a stable behavior that recurs across varied inputs?
   Consider adaptation.
4. Could informed humans reasonably disagree about the intended answer? Ask
   for clarification.

This boundary prevents model weights from becoming a stale knowledge store and
prevents agent loops from compensating indefinitely for weak learned behavior.

---

## 2. What systematic, repetitive, and teachable mean

### Systematic

A mistake is systematic when multiple failures have the same underlying cause,
not merely similar error messages.

Examples include repeatedly:

- inventing direct relationships instead of following supplied join paths;
- returning extra fields instead of the requested output shape;
- confusing an entity's identifier with another table's identifier;
- omitting one value from a documented multi-value business predicate;
- constructing a difference when percentage growth was requested.

An authentication failure, service outage, or corrupted input is not a
systematic model-behavior failure.

### Repetitive

The weakness must appear often enough to suggest that it will recur on future
tasks. One unusual failure may be noise, ambiguity, or an edge case. A cluster
of failures across different questions is stronger evidence.

Repetition should be measured at the behavioral level. Five queries may have
different database errors but share one root cause: failure to respect the
supplied schema.

### Teachable

A behavior is teachable when new, unambiguous examples can demonstrate:

- the input;
- the desired output;
- a stable rule connecting them;
- an objective method for verifying correctness.

“Follow only relationships supplied in the schema” is teachable. “Guess what
the user meant by an ambiguous phrase” is not.

---

## 3. Establish the decision before analyzing failures

Do not begin with “How should we fine-tune?” Begin with:

> Is there enough evidence to justify a controlled adaptation experiment?

A reasonable decision standard requires evidence that:

1. the necessary information was available to the model;
2. the behavioral weakness repeats;
3. additional prompt or context work is showing diminishing returns;
4. the desired behavior can be taught using verified examples;
5. the target is a stable skill rather than a changing fact;
6. the likely quality improvement could justify training and deployment cost.

The output of this stage is permission to design training data—not a claim that
fine-tuning will succeed.

---

## 4. Build a leakage-safe evidence boundary

Use separate datasets for development and final evaluation.

### Working-development set

This is the diagnostic laboratory. It may be inspected repeatedly to:

- read individual questions and generated outputs;
- compare reference and candidate behavior;
- build a failure taxonomy;
- design prompts and deterministic checks;
- evaluate regressions during development.

### Frozen evaluation set

This is the exam. Before the final experiment, use only aggregate results and
artifact hashes. Do not inspect its individual failures and then design
training examples around them.

### Strong exclusion rule

Neither working nor frozen evaluation examples should be used as:

- direct training records;
- paraphrased training records;
- few-shot demonstrations;
- seeds for synthetic generation;
- templates with superficial entity or value substitutions.

After training, the working set remains useful for behavioral diagnosis and
regression testing; the frozen set measures generalization.

---

## 5. Make comparisons causally interpretable

Change one major variable at a time.

For an adaptation experiment, hold constant:

- base-model version, unless a model change is separately baselined;
- runtime context and retrieval policy;
- system instructions;
- output normalization;
- number of attempts;
- repair policy;
- evaluator and database version;
- decoding settings;
- evaluation IDs.

Then change only the model adaptation.

If the fine-tuning platform requires a different base model, first run that
unadapted model under the identical runtime contract. Compare:

```text
new base model + fixed runtime
            versus
adapted new model + fixed runtime
```

Otherwise, the effect of the new base model is confounded with the effect of
fine-tuning.

Use content hashes for prompts, context, datasets, and run artifacts. A hash is
an experiment fingerprint: it establishes exactly which inputs produced a
result.

---

## 6. Analyze transitions, not only aggregate accuracy

An aggregate increase such as `1/12 -> 4/12` does not reveal how the system
changed. Classify every example's transition:

| Transition | Interpretation |
|---|---|
| Newly correct | The intervention fixed a previous failure |
| Retained correct | A prior success remained stable |
| Regressed | A prior success became a failure |
| Execution recovered but incorrect | Structural validity improved without semantic correctness |
| Still incorrect | The intervention did not solve the task |

This distinguishes stable improvement from score churn. A system that fixes
six examples while breaking three is less dependable than one that fixes three
and preserves every prior success, even if both end at the same score.

Also keep these metrics separate:

- **Executable:** the output can run or compile.
- **Semantically correct:** the output produces the intended result.

Executability is necessary for many tasks, but it is not sufficient.

---

## 7. Diagnose each residual failure from evidence

For every remaining working-set failure, collect:

- the user's request;
- the expected behavior or verified reference;
- the model output;
- evaluator or compiler result;
- small expected and candidate result previews, when safe;
- the exact runtime context available to the model.

Then answer:

1. What operation did the user request?
2. What did the model do instead?
3. Where is the first meaningful divergence?
4. Was the required information already present?
5. What reusable behavior would have prevented the mistake?
6. Could new, disjoint examples teach and verify that behavior?

Focus on the first meaningful divergence. Later errors may be symptoms of an
earlier misunderstanding.

---

## 8. Build an evidence-backed taxonomy

A failure can have several contributing causes, but assign one primary gap for
counting. Record other symptoms separately.

Recommended fields:

```yaml
primary_gap: multi_table_join_path
cluster: schema_constrained_construction
contributing_gaps:
  - nonexistent_identifier
  - aggregation_semantics
context_was_available: true
adaptation_candidate: true
confidence: high
evidence: >
  The model invented a direct relationship even though the supplied context
  showed the required bridge entity.
```

### Why use both narrow gaps and broad clusters?

Narrow labels preserve diagnostic precision. Broader clusters reveal repeated
behavior.

For example:

```text
ambiguous identifier
wrong table ownership       -> schema-constrained construction
invented direct join
incorrect projection
```

Do not count every visible symptom as an independent failure. That inflates the
evidence for adaptation.

Taxonomies require judgment. Every label should include written evidence and a
confidence level so another reviewer can challenge it.

---

## 9. Understand what repair loops can and cannot do

Execution or compilation provides strong signals for structural failures:

- invalid syntax;
- nonexistent tables, columns, functions, or API methods;
- ambiguous identifiers;
- type errors;
- missing required parameters.

A bounded repair attempt can be useful for these failures.

But valid output may still be semantically wrong:

- the wrong table or API operation was selected;
- a valid filter was omitted;
- the wrong business value was used;
- extra output fields were returned;
- a valid formula answered a different question.

In production, the reference answer is normally unavailable. Successful
execution therefore cannot certify semantic correctness.

Measure repair as its own intervention:

- additional correct answers;
- additional executable outputs;
- regressions;
- extra tokens;
- latency;
- added failure modes.

If repair improves only executability while accuracy remains flat, it is
treating symptoms rather than the central reasoning weakness. More open-ended
agent loops are then unlikely to be the cleanest next experiment.

This does not make agents unnecessary. A production workflow can still use
retrieval, validators, safe execution, bounded repair, and clarification. The
question is whether those mechanisms should compensate for the same weak
first-attempt behavior on every request.

---

## 10. Write a falsifiable adaptation hypothesis

Use this template:

> Given **[fixed and sufficient runtime information]**, the model repeatedly
> fails at **[specific behavioral clusters]**. Supervised adaptation on
> **[verified, disjoint examples of named behaviors]** should improve
> **[predefined quality and operational metrics]** while preserving
> **[existing successful behavior and runtime grounding]**.

Avoid hypotheses such as:

> Fine-tuning should make the model better.

That statement does not specify what will improve, why it should improve, or
what evidence would disprove it.

### Example behavioral targets

- follow relationships supplied at runtime;
- use identifiers only from their owning entity;
- return exactly the requested fields in the requested order;
- apply documented enum or status mappings;
- avoid invented assumptions and filters;
- construct recurring conditional aggregation or arithmetic patterns;
- use retrieved private API documentation consistently.

### SFT and LoRA

Supervised fine-tuning (SFT) describes the learning task: train on inputs paired
with verified desired outputs. LoRA describes a parameter-efficient way to
perform that training by updating small adapters instead of every model
parameter. A project may therefore conduct SFT using LoRA.

---

## 11. Pre-register success and failure criteria

Define thresholds before training. At minimum, record:

- task accuracy target;
- structural validity or execution target;
- allowed regressions;
- API or infrastructure failure allowance;
- latency and token budgets;
- number of attempts and repair policy;
- deployment and ongoing cost ceiling;
- the exact comparison system.

Example:

```yaml
success:
  frozen_task_success: at_least_10_of_24
  frozen_execution_success: at_least_20_of_24
  regressions_on_prior_working_passes: 0
  api_errors: 0
  attempts_per_question: 1
  repair_enabled: false
failure:
  - gains require leakage or changed evaluation inputs
  - task success remains below the threshold
  - previously correct behaviors regress
  - deployment economics outweigh quality improvement
```

Pre-registration prevents moving the goalposts after results are visible.

On a small evaluation set, each question has a large effect on the percentage.
Treat thresholds as pilot decision gates, not estimates of universal production
quality. Repeat runs or confidence intervals may be needed before making larger
claims.

---

## 12. The reusable end-to-end method

1. Define the business outcome and evaluation metric.
2. Freeze a leakage-safe evaluation set.
3. Establish frontier and target-model baselines.
4. Fix missing context, metadata, retrieval, and deterministic workflow issues.
5. Re-evaluate under a versioned, fixed runtime contract.
6. Measure question-level transitions, not only aggregate uplift.
7. Inspect residual working failures using concrete evidence.
8. Assign one primary cause and cluster repeated behaviors.
9. Route each issue to runtime context, deterministic code, model behavior, or
   human clarification.
10. Test bounded repair separately and measure its marginal value and cost.
11. Write a narrow, falsifiable adaptation hypothesis.
12. Define training targets and facts that must remain runtime-only.
13. Exclude evaluation questions, paraphrases, and templates from training.
14. Pre-register quality, regression, latency, and economic thresholds.
15. Design and manually inspect the training dataset.
16. Baseline any replacement model before adapting it.
17. Train while keeping the runtime and evaluator fixed.
18. Evaluate working regressions and frozen generalization.
19. Compare measured benefit with deployment and maintenance cost.
20. Adopt, revise, or reject the adaptation hypothesis based on evidence.

---

## 13. Applying the method to a private API or scripting engagement

Consider a model that generates scripts against a customer's private API.

### Keep at runtime

- current API documentation;
- available endpoints and function signatures;
- authentication requirements;
- parameter definitions and enum values;
- customer-specific objects and permissions;
- version and deprecation information.

### Put in deterministic workflow

- parser or compiler checks;
- function and parameter existence validation;
- type checking;
- sandboxed execution;
- permission and policy enforcement;
- bounded correction for explicit compiler or API errors.

### Consider for adaptation

- repeatedly selecting the correct documented API operation;
- composing multi-step calls in the required order;
- passing retrieved parameters without inventing fields;
- producing the required script envelope;
- recurring domain-specific transformation patterns;
- consistent adherence to stable coding conventions.

### Escalate or clarify

- unclear business intent;
- conflicting documentation;
- destructive actions;
- several valid workflows with materially different consequences.

An evidence-backed engagement statement might be:

> Given current private API documentation at runtime, the model repeatedly
> invents parameters and misorders dependent calls. SFT using disjoint,
> verified examples of documentation-grounded parameter selection and call
> sequencing should improve compilation and task success under the same
> retrieval, validation, and execution workflow.

This is far stronger than saying, “The model needs domain fine-tuning.”

---

## 14. Common mistakes to avoid

1. **Fine-tuning missing knowledge.** Supply changing facts at runtime instead.
2. **Training directly on evaluation failures.** This measures memorization,
   not generalization.
3. **Changing model, prompt, tools, and retries together.** The improvement
   becomes causally uninterpretable.
4. **Treating executable output as correct output.** Semantic errors often run
   successfully.
5. **Counting every symptom as a separate root cause.** Use one primary gap and
   preserve contributing gaps separately.
6. **Building an agent loop before measuring marginal repair value.** Retries
   can add cost without recovering semantic correctness.
7. **Training on ambiguous requirements.** Clarify or exclude them.
8. **Ignoring regressions.** Protect behaviors that already work.
9. **Ignoring deployment economics.** Technical improvement may not justify a
   dedicated endpoint, GPU, or maintenance process.
10. **Declaring success after one percentage rises.** Evaluate correctness,
    structural validity, latency, token usage, reliability, and cost together.

---

## 15. Compact review worksheet

Use this worksheet during failure review:

```markdown
### Failure ID

- User request:
- Expected behavior:
- Model behavior:
- First meaningful divergence:
- Required information present? Yes / No
- Primary gap:
- Contributing gaps:
- Broader cluster:
- Best fix location: Runtime / Code / Weights / Clarification
- Adaptation candidate: Yes / No / Conditional
- Confidence: Low / Medium / High
- Evidence:
- How a disjoint example could teach the behavior:
- How correctness would be verified:
```

After reviewing all failures, ask:

- Which clusters repeat?
- Which failures disappear when context is corrected?
- Which are executable but semantically wrong?
- Which can deterministic validation catch?
- Which remain after bounded repair?
- Which examples are ambiguous?
- Is the potential gain large enough to justify adaptation economics?

---

## Final takeaway

The goal is not to prove that fine-tuning is powerful. The goal is to determine
whether it is the right intervention for a specific residual behavior.

The durable mental model is:

```text
Changing facts       -> runtime context or retrieval
Objective constraints -> deterministic validation and tools
Stable repeated skill -> adaptation candidate
Ambiguous intent      -> human clarification
```

Fine-tuning begins only after evidence shows that the model had the information
it needed, repeatedly failed to use it in the same teachable way, and could
create enough value to justify the additional training and deployment lifecycle.
