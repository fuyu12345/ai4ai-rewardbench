# Time cost on selected typical benchmarks

The homepage and README show **selected typical benchmarks** to illustrate
the time-cost trend on longer-running AI4AI tasks. This selection is not
statistically representative of all source benchmarks or the full collection.

There are six points per model, covering the same 31 frozen pairs. The four
configurations are Gemini 4 Argon, Terra default, Opus 5.5 high, and Sol xhigh.
The [public JSON](../data/public-runtime.json) records the pair membership,
timing scope, aggregate values and audit fingerprints. The
[CSV](../data/public-runtime.csv) contains all 24 displayed points.

## Selection

For each benchmark, prefer the pairs with complete execution timing. If only
training, final verification or a published subtask clock is available, retain
that scope separately. Pool Agent and Reasoning within each benchmark, then
keep benchmarks with a measured median of at least **300 seconds**. No filter
uses judgment time, correctness or a speedup threshold.

The resulting selection is:

| Typical benchmark | Timed pairs | X median | What the clock covers |
| --- | ---: | ---: | --- |
| AABench | 15 | 724.21 s | Candidate training/construction plus evaluation; 1 × L20X |
| MLE-Bench | 6 | 432.94 s | Candidate pipeline and grader worker; may include HPO and worker retries |
| nanoGPT | 5 | 571.51 s | Prescribed single-seed startup, training and validation; 8 × L20X |
| NatureBench | 1 | 1,020.25 s | Training/prediction command plus separate grader call |
| PostTrainBench | 3 | 3,160.08 s | **Training stage only**; excludes loading, export and final evaluation |
| MLSBench | 1 | 20,138.50 s | **One published environment × seed**, not the full multi-environment, multi-seed task |

MLGym (26.7 s), RSI-Exam (11.8 s), and Terminal-Bench Science (142.7 s)
fall below this threshold under their available preferred scopes and are not
shown in this illustrative view. Benchmarks without a verifiable candidate
clock are not assigned a budget-based estimate. Within nanoGPT, only five of
eight pairs have the required complete clock; NatureBench contributes one of
its two pairs. The missing pairs are not zeros.

## Axes and aggregation

- **X:** Take the mean of candidate A and B measured times for each pair, then
  the median across the included pairs in a benchmark. MLSBench is the
  explicit exception: its X is the median of 18 published per-environment,
  per-seed elapsed times.
- **Y:** Use exactly those pairs for each model. Treat each of the three
  repeats as a single judgment, and take the median of their observed times.
  This gives 93 matched judgments per model, or 372 across the four models.
- Each judgment compares two candidates; X covers one candidate or the
  labeled stage. It is not the serial sum of executing both candidates.
- Both axes use logarithmic scales. Below the equal-time line, the recorded
  judgment takes less time than the measured candidate execution or stage.

Original and recovery attempt durations are accumulated once per physical
attempt. These durations include episode-local queueing, transport, retry
backoff, model response and tool interactions. They exclude the calendar gap
between batches awaiting recovery. They are recorded batch costs, not
isolated inference latency. Neither the fastest repeat nor only the final
successful attempt is used.

Gemini's historical source contains 405 valid judgments and 587 unique
attempts; 93 judgments match this figure. The latest Sol/Terra/Opus delivery
contains 1,215 valid judgments and 1,461 unique attempts; the figure uses 93
judgments from each model. All selected cumulative clocks reconcile with the
underlying attempt sums. The historical batches and serving conditions differ.

## Interpretation

Solid points indicate complete selected candidate execution/evaluation.
Open points retain the two partial or subtask clocks explicitly. In particular,
neither PostTrainBench nor MLSBench establishes a full-task train-plus-validation
speedup. NatureBench uses observed command dispatch-to-completion timestamps,
including notification overhead, with the thinking gap before grading removed.

The figure is an illustration of cost, not proof that a judge can replace an
experiment at equivalent quality. Accuracy, calibration and realized experiment
selection gains require separate evaluation. Hardware has not been normalized;
the same benchmark name can cover very different task slices.

No candidate programs or new model evaluations were run to make this figure.
Raw trajectories, private reference labels and local/server paths remain outside
the public repository.
