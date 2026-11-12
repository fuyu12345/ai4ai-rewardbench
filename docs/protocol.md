# AI4AI RewardBench evaluation protocol

AI4AI RewardBench v0.1 evaluates judgments about competing AI research and engineering solutions under a stated task, resource budget, and decision rule. A judge inspects public evidence for candidates A and B and predicts A, B, or tie. It does not generate a new candidate solution or run the candidates.

The frozen development collection contains **135 pairs from 17 source benchmarks: 105 Agent tasks and 30 Reasoning tasks**. The current results update, dated 12 November 2026, displays **10 model configurations**. Additional tasks and broader domain coverage are planned for future versions and are not included in the current denominator.

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

The overall denominator is 135. Agent and Reasoning views use 105 and 30. Benchmark subgroup scores use the same rule on that subgroup. The webpage labels the metric **Accuracy** because the displayed configurations do not share one repetition policy.

| Displayed configuration | Included repeats per question | Overall | Agent | Reasoning |
| --- | --- | ---: | ---: | ---: |
| gpt-6.1-sol · xhigh | Repeat 1 only | 60/135 = 44.44% | 40/105 = 38.10% | 20/30 = 66.67% |
| gpt-6.1-terra · default | Repeat 1 only | 56/135 = 41.48% | 37/105 = 35.24% | 19/30 = 63.33% |
| Other eight displayed configurations | Repeats 1, 2, 3, except the Claude case below | Question average | Question average | Question average |

Terra's source experiment also contains repeats 2 and 3. This display explicitly uses **repeat 1**, not the best repeat, and does not pool all three. The new Sol xhigh run replaces the previous default Sol row. Different reasoning effort, repeat counts, providers, and recovery budgets limit direct comparability; equal task weights do not remove those differences.

Claude's `AAB15-P016` repeat 2 remained a refusal. Only repeats 1 and 3 enter that question's score, both correct. Its overall score is `(138/3 + 2/2) / 135 = 34.8148%`, not pooled `140/404`. No answer is invented for the refused cell.

The current displayed rows contain **3,510 planned cells and 3,509 valid cells**: eight historical configurations × 405, plus two updated configurations × 135. This is not a count of all experiments ever performed. The original nine-model, three-repeat snapshot (3,644/3,645 valid) is retained at `data/snapshots/golden2-20261111.json`, with its checksum recorded in the current export. Dataset labels and inputs have not changed.

## Baselines

| Subset | A / B / tie counts | Uniform A/B/tie | Random A/B | Always A |
| --- | --- | ---: | ---: | ---: |
| All 135 | 78 / 55 / 2 | 33.33% | 49.26% | 57.78% |
| Agent 105 | 58 / 46 / 1 | 33.33% | 49.52% | 55.24% |
| Reasoning 30 | 20 / 9 / 1 | 33.33% | 48.33% | 66.67% |

Baseline denominators follow the selected subset. Fixed AB order and label imbalance matter when interpreting accuracy.

## Runs and resources

All repeats start independent conversations with fixed AB order; no BA-swap study or fixed-random-seed claim is made. Historical configurations used provider-default settings through the recorded proxy route. The updated Sol and Terra results were recorded through the official OpenAI Responses API, with Sol reasoning effort set to xhigh and Terra's setting left at its recorded default. API model names are reported as observed; a routing label alone is not independent checkpoint verification.

Original and recovery batches are both preserved in the source record. For the two updated rows, metrics include **only repeat 1 across all of its original and recovery layers**. Terra repeats 2 and 3 do not contribute to the displayed score or usage. Costs are not mixed across currencies.

| Resource | Interpretation |
| --- | --- |
| Input/output tokens | Known usage from original attempts, failures, retries, repairs, and recovery within the displayed cohort |
| Cached input / reasoning tokens | Subsets of input/output respectively; do not add them again |
| Agent model turns | Logical model steps; transmission retries count separately as API attempts |
| Tool rounds / tool calls | A reply containing tools versus individual invocations within replies |
| Mean Agent turns | Agent turns divided by `agent_planned_cells`: 105 for the new Sol/Terra rows, 315 for historical rows |
| Reported CNY cost | Supplier-explicit charges where available; new official-API rows have no reported CNY value |
| Estimated USD cost | Historical usage-based estimates for the new official-API rows, stored separately; not a reconciled bill |

Unknown charges are not zero. Resource columns remain full-cohort totals when switching accuracy subsets. Claude's excluded refusal still contributes its observed resource usage. Incorrect valid responses were not retried because they were incorrect.

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
- Historical hy4 failures used additional recovery budgets; the Claude refusal has the documented exception. Updated Sol and Terra also include their recorded network/rate-limit recovery layers.
- Agreement with frozen preferences does not establish preference reversal, downstream research gains, successful reward-model training, or agent RL gains. These remain research directions.

The repository publishes allowlisted aggregates, English task presentations, and reviewed explanations. It excludes private labels, organizer evidence, credentials, internal paths, full candidate code/data packages, and complete raw trajectories. Full asset releases require separate source review.

The utilities verify scores offline. They do not run models or execute candidates, and v0.1 does not provide a portable end-to-end evaluator. Input, label, order, budget, or task-subset changes require a new version; updated model cohorts retain their own provenance rather than altering the original snapshot.
