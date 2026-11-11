# Golden2 evaluation protocol

AI4AI RewardBench v0.1 evaluates judgments about competing AI research and engineering solutions under a stated task, resource budget, and decision rule. A judge reads the public evidence for candidates A and B and predicts A, B, or tie. It does not produce a new candidate solution.

This release describes the frozen Golden2 development collection evaluated on 10–11 November 2026: **135 pairs, 17 source benchmarks, 105 Agent tasks, 30 Reasoning tasks, and 9 model IDs**. Earlier collections are excluded. One pair is one question; 3,645 planned evaluation cells are repeated judgments, not 3,645 distinct tasks.

## Two input modes

| Mode | Questions | What the judge receives | Interaction |
| --- | ---: | --- | --- |
| Reasoning | 30 | The complete public task package, inlined into the conversation | Direct judgment from the supplied material |
| Agent | 105 | A task description and access to manifest-allowlisted public files | Read-only inspection with `list_files`, `read_file`, `search`, `inspect_data`, `read_array`, and `read_table` |

Agent evaluation does not execute candidate code or use the network. Organizer labels and private evidence are excluded from judge inputs. The task-specific decision rule defines the objective, constraints, score direction, and meaning of a tie. These may concern quality, latency, or quality subject to resource constraints.

There are 103 questions with A/B/tie output choices and 32 that additionally permit `unresolved`. `unresolved` is an abstention, not a fourth gold label or a tie.

## Primary score: question-weighted accuracy

For model `m` and question `q`, let `R(m,q)` contain the accepted repeats. Compute:

```text
question_score(m, q) = correct accepted repeats / accepted repeats
accuracy(m, S) = 100 × sum(question_score(m, q) for q in S) / |S|
```

The main leaderboard uses all 135 questions with equal weight. Agent and Reasoning views apply the same calculation to their 105 and 30 questions. Benchmark views likewise average question scores within the selected benchmark, rather than pooling valid responses.

Normally, `R(m,q) = {1,2,3}`. The **only exception** is `claude-sonnet-5-5` on `AAB15-P016`: repeat 2 remained a refusal after the recorded retries, so repeats 1 and 3 are used as avg@2. Both were correct. Its main score is therefore `(138/3 + 2/2) / 135 = 34.8148%`, **not** `140/404`. All other model–question combinations use avg@3. No third answer was invented.

The planned matrix is `9 × 135 × 3 = 3,645` cells: **3,644 valid, 1 refusal**. The displayed scores use the final merged results, including recovery layers. Earlier root-run leaderboards and valid-response pooled subgroup reports are not the authority for this release.

## Baselines and label balance

| Policy | Expected accuracy |
| --- | ---: |
| Uniform random A/B/tie | 33.33% |
| Uniform random A/B | 49.26% |
| Always choose A | 57.78% |

The frozen labels comprise **A: 78, B: 55, tie: 2**. The A/B policy scores `(78 + 55) / (2 × 135)`, while always-A scores `78/135`. All nine evaluated models score below the always-A baseline on this selected collection. A score above 33.33% alone does not establish improvement over the other simple baselines.

## Runs and resources

Each repeat starts an independent conversation with the same fixed AB order. No BA swap experiment was performed. Sampling temperature and reasoning effort use provider defaults; fixed random seeds are not claimed. The reported IDs are `gpt-6.1-sol`, `hy4`, `kimi-k3.1-pro`, `deepseek-v4.1-flash`, `qwen3.8-flash`, `glm-5.3-flash`, `kimi-k2.6`, `gemini-4-argon`, and `claude-sonnet-5-5`. Requests were routed through DMX; recorded request and response IDs do not independently verify the underlying served checkpoints.

The initial limits were 32,768 output tokens per request, 524,288 cumulative output tokens per cell, 768 Agent model turns or 32 Reasoning model turns, and 7,200 seconds per cell including queuing and rate-limit waits. The local 6,400,000-character context guard is not a model-native token window. Some recovery cells received additional time or retry budgets, so this is not a claim of identical realized budgets for every cell.

| Resource field | Meaning |
| --- | --- |
| Input / output tokens | Known cumulative usage across original runs, failures, format clarification, transport retries, and recovery |
| Cached input tokens | A subset of input tokens; do not add again |
| Reasoning tokens | A subset of output tokens; do not add again |
| Model turns | Logical model turns, with same-turn transport retries counted separately as API attempts |
| Tool rounds | Model replies that contain tool calls |
| Tool calls | Individual invocations; multiple calls can occur in one round |
| Mean Agent turns | Agent model turns divided by 315 planned Agent cells, including failed-attempt consumption |
| Reported cost, CNY | Supplier-explicit charges only; missing values are unknown, not zero, and totals are not an account reconciliation |

Consumption associated with Claude's excluded refusal remains in resource accounting. An incorrect but valid answer was not rerun because it was incorrect.

## Interpretation and limitations

- Golden2 is manually selected and partly grounded in historical evaluations and audits. It is a development collection, not an independently sampled hidden test set. A historical label does not imply every candidate was rerun independently for this release. Related tasks or similar candidates need not be statistically independent.
- The two `DRSI-tree-T6xcqyV-rzvBsWz` and `DRSI-tree-TZKDZCh-rzvBsWz` inputs contain performance self-descriptions in source comments. They remain unchanged and explicitly flagged; the release does not claim all result cues were removed.
- Five original output schema forms were normalized. A repaired validator selected the earliest qualifying answer under the same lossless parsing rules, without consulting gold labels. Additional calls and original-response provenance remain in the audit record.
- Some Gemini routes omitted thought signatures. The recovery used a documented compatibility marker for missing signatures in 438 requests; it cannot reconstruct missing server-side state.
- Thirty-five `hy4` failure cells recovered under additional time and retry budgets. Claude's single avg@2 exception is visible in the score definition.
- This release tests agreement with frozen preferences. It does **not** demonstrate repeatable preference reversals after state changes, benefits in expensive experiment selection, successful reward-model training, or agent RL gains. These remain proposed research questions.

## Artifacts and reproduction

The v0.1 website publishes an allowlisted metadata and aggregate-results export plus reviewed case material. Internal handoff files, private labels, organizer evidence, raw provider responses, infrastructure addresses, and credentials are excluded. Full candidate packages and full raw trajectories are separate release decisions requiring source-by-source review; this website does not grant a new license over upstream material.

The data preparation and validation utilities reproduce the displayed public aggregates from the frozen handoff. This is offline score verification, not a fresh model evaluation. A portable evaluator would require parameterizing the historical runner, inputs, adapters, and output directories; v0.1 does not claim a one-command fresh-environment rerun.

Any changed question, label, candidate order, cue removal, task subset, or evaluation budget must receive a new dataset or evaluation version rather than overwrite these scores.
