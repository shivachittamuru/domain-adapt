# DomainAdapt

DomainAdapt is a learning-oriented reference implementation for measuring how
much of a frontier model's domain performance can be recovered by a smaller
model through evaluation, context engineering, deterministic system design,
and—only when justified—model adaptation.

## Notebook sequence

| Milestone | Notebook | Purpose |
|---:|---|---|
| 0 | `00_project_orientation.ipynb` | Understand the data flow and benchmark |
| 1 | `01_dataset_and_eval.ipynb` | Build the leakage-safe evaluator and splits |
| 2 | `02_frontier_baseline.ipynb` | Establish the strong-model reference point |
| 3 | `03_failure_analysis.ipynb` | Classify frontier working-set failures |
| 4 | `04_slm_baseline.ipynb` | Measure the unadapted candidate-SLM gap |
| 5 | `05_context_engineering.ipynb` | Test schema grounding, domain context, guardrails, and deterministic output handling |
| 6 | `06_adaptation_hypothesis.ipynb` | Classify residual model gaps and decide whether adaptation is justified |

“Context engineering” is used for Milestone 5 because most experiments change
the information and instructions supplied to the model. A model harness is a
broader term for the surrounding invocation, validation, execution, and repair
logic; it does not require an agent, but it is less precise for this milestone.

See `PRD.md` for the complete research plan and leakage policy.
