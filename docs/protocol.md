# AI4AI RewardBench evaluation protocol

AI4AI RewardBench v0.1 evaluates judgments about competing AI research and engineering solutions under a stated task, resource budget, and decision rule. A judge inspects public evidence for candidates A and B and predicts A, B, or tie. It does not generate a new candidate solution or run the candidates.

The frozen development collection contains **135 pairs from 17 source benchmarks: 105 Agent tasks and 30 Reasoning tasks**. The current results update, dated 12 November 2026, displays **11 model configurations**. Additional tasks and broader domain coverage are planned for future versions and are not included in the current denominator.

## Two input modes

| Mode | Questions | What the judge receives | Interaction |
| --- | ---: | --- | --- |
| Reasoning | 30 | The complete public task package, inlined into the conversation | Direct judgment from supplied material |
| Agent | 105 | A task description and manifest-allowlisted public files | Read-only inspection with list_files, read_file, search, inspect_data, read_array, and read_table |

Agent evaluation does not execute candidate code or use the network. Organizer labels and private evidence are excluded. The decision rule defines the objective, constraints, score direction, and meaning of a tie. There are 103 questions with A/B/tie choices and 32 that additionally permit `unresolved`. It is an abstention, not a fourth reference label.

## Primary score: question-weighted accuracy

For each model and question, average correctness across the included repeats; then give each question equal weight:

```text
question_score(model, question) = correct included responses / included responses
accuracy(model, subset) = sum(question_score over subset) / number of questions
```

The overall denominator is 135. Agent and Reasoning views use 105 and 30. Benchmark subgroup scores use the same rule on that subgroup. The webpage labels the metric **Accuracy** and specifies **avg@3**, with the Claude Sonnet exception described below. For a complete three-repeat cohort, equal question weights are equivalent to correct responses divided by 405 overall, 315 for Agent, or 90 for Reasoning.

| Displayed configuration | Included repeats per question | Overall | Agent | Reasoning |
| --- | --- | ---: | ---: | ---: |
| gpt-6.1-sol · xhigh | Repeats 1, 2, 3 | 178/405 = 43.95% | 126/315 = 40.00% | 52/90 = 57.78% |
| gpt-6.1-terra · default | Repeats 1, 2, 3 | 173/405 = 42.72% | 116/315 = 36.83% | 57/90 = 63.33% |
| claude-opus-5-5 · high | Repeats 1, 2, 3 | 163/405 = 40.25% | 106/315 = 33.65% | 57/90 = 63.33% |
| Other eight displayed configurations | Repeats 1, 2, 3, except the Sonnet case below | Question average | Question average | Question average |

All 1,215 responses in the three updated cohorts are valid. Every delivered repeat is included; no best-repeat selection is used. Results are grouped by model and delivered repeat, across the recorded provider routes. Original directory repeat numbers can differ from the unified delivery index. The delivery's result and trajectory index defines the mapping, including original and recovery attempts.

The updated Sol and Terra averages replace their earlier single-repeat display. Different reasoning effort, providers, and recovery budgets still limit direct comparability; equal task weights do not remove those differences.

**Claude Sonnet** (`claude-sonnet-5-5`) / `AAB15-P016` repeat 2 remained a refusal. Only repeats 1 and 3 enter that question's score, both correct. Its overall score is `(138/3 + 2/2) / 135 = 34.8148%`, not pooled `140/404`. No answer is invented for the refused cell. This exception does not apply to Opus.

The current displayed rows contain **4,455 planned cells and 4,454 valid cells**: eleven configurations × 405 planned responses, with the single Sonnet refusal. This is not a count of all experiments ever performed. The original nine-model, three-repeat snapshot (3,644/3,645 valid) is retained at `data/snapshots/golden2-20261111.json`, with its checksum recorded in the current export. Dataset labels and inputs have not changed.

## Baselines

| Subset | A / B / tie counts | Uniform A/B/tie | Random A/B | Always A |
| --- | --- | ---: | ---: | ---: |
| All 135 | 78 / 55 / 2 | 33.33% | 49.26% | 57.78% |
| Agent 105 | 58 / 46 / 1 | 33.33% | 49.52% | 55.24% |
| Reasoning 30 | 20 / 9 / 1 | 33.33% | 48.33% | 66.67% |

Baseline denominators follow the selected subset. Fixed AB order and label imbalance matter when interpreting accuracy.

## Runs and resources

All repeats start independent conversations with fixed AB order; no BA-swap study or fixed-random-seed claim is made. Sol uses xhigh reasoning effort, Opus 5.5 uses high, and Terra uses its recorded default. The other eight configurations retain their recorded default settings. Rows are grouped by the requested API model and effort setting. Returned model identifiers are retained in source metadata, including the small number of Sol responses labeled gpt-6.1-sol-2. A returned identifier or routing label alone is not independent checkpoint verification.

Original and recovery batches are both preserved in the source record. For the three updated rows, resource metrics cover **all three delivered repeats and all linked attempts**, with duplicate physical attempts counted once. Each model is presented as one row across its source routes. Costs are not mixed across currencies.

| Resource | Interpretation |
| --- | --- |
| Input/output tokens | Known usage from original attempts, failures, retries, repairs, and recovery within the displayed cohort |
| Cached input / reasoning tokens | Subsets of input/output respectively; do not add them again |
| Agent model turns | Logical model steps; transmission retries count separately as API attempts |
| Tool rounds / tool calls | A reply containing tools versus individual invocations within replies |
| Mean Agent turns | Agent turns divided by 315 planned Agent cells for every displayed model |
| Reported CNY cost | Sum of explicitly reported CNY charges where available; some cohorts have partial coverage, so this is not a complete run price |

Unknown charges are not zero. Resource columns remain full-cohort totals when switching accuracy subsets. Sonnet's excluded refusal still contributes its observed resource usage. Incorrect valid responses were not retried because they were incorrect.

The historical main-run limits included 32,768 output tokens per request, 524,288 cumulative output tokens per cell, 768 Agent turns or 32 Reasoning turns, and 7,200 seconds per cell including queues. Recovery layers could add time or retry budgets. These are historical run settings, not guarantees that every displayed cohort has identical effective budgets.

## Reading case studies and task details

The task catalog provides English presentations of all 135 tasks, with background, question, candidate descriptions, constraints, decision rules, and source-file inventory. These are adapted or translated from the frozen public input. They are not complete executable task packages.

Case studies expose the **actual saved final explanations**, their stated confidence, evidence citations and uncertainties. These are model claims, not verified reference answers. The explorer also preserves original/recovery layers, tool arguments, returned line ranges, and selected public assistant messages. Editorial observations are labeled separately. Links between a read step and a later final citation are retrospective references, not claims about the model's thinking at that step.

Many pre-tool responses contain tool calls only. Some saved reasoning fields contain empty summaries and encrypted state. Those do not provide readable intermediate analysis and are never reconstructed or presented as a thought transcript. Three cases are curated examples, not a representative performance sample.

## Limitations and release scope

- This is a manually selected development collection with historical labels, not an independently sampled hidden test set. A historical label does not mean every candidate was independently rerun for this release. Related tasks need not be statistically independent.
- Two DeepRSI tree inputs retain performance self-descriptions and are flagged in metadata.
- Historical schema normalization selected the earliest qualifying answer under lossless rules without consulting labels. Additional request consumption remains accounted for.
- Some historical Gemini routes required a missing-signature compatibility marker. The marker cannot recreate missing server state.
- Historical hy4 failures used additional recovery budgets; the Sonnet refusal has the documented exception. Updated Sol, Terra, and Opus include all attempts linked by the delivery, including network and rate-limit recovery layers.
- Agreement with frozen preferences does not establish preference reversal, downstream research gains, successful reward-model training, or agent RL gains. These remain research directions.

The repository publishes allowlisted aggregates, English task presentations, and reviewed explanations. It excludes private labels, organizer evidence, credentials, internal paths, full candidate code/data packages, and complete raw trajectories. Full asset releases require separate source review.

The utilities verify scores offline. They do not run models or execute candidates, and v0.1 does not provide a portable end-to-end evaluator. Input, label, order, budget, or task-subset changes require a new version; updated model cohorts retain their own provenance rather than altering the original snapshot.
