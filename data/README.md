# Public Golden2 snapshot

`public-benchmark.json` contains 135 catalog records, 17 benchmark counts, ten
model summaries, grouped accuracies, resource totals, protocol notes and source
SHA-256 digests. The current release is v0.1.1, updated on 2026-11-12. Ratios use
the range 0–1; multiply by 100 once for display.

The website snapshot is built with a strict field allowlist. It contains no
individual gold labels, individual model responses, raw trace bodies, server
addresses, internal paths or contributor directory names. Aggregate label
counts are retained because the three simple baselines are necessary context.
The catalog is metadata, not a redistribution of the candidate code or datasets.

## Score interpretation

The primary score is the mean of 135 pair scores. Each pair score is the mean
correctness of its included repeats. The current leaderboard combines:

- Eight retained original rows with three planned repeats, served through DMX.
- `gpt-6.1-sol`, official OpenAI Responses, `xhigh`, **repeat 1 only**:
  60/135 overall (44.44%), 40/105 Agent (38.10%), 20/30 Reasoning (66.67%).
  This replaces the original default-effort Sol row; it does not relabel it.
- `gpt-6.1-terra`, official OpenAI Responses, default effort, **repeat 1 only**:
  56/135 overall (41.48%), 37/105 Agent (35.24%), 19/30 Reasoning (63.33%).
  The source contains three repeats; repeats 2 and 3 are excluded from both
  this row's score and resource totals. No best-repeat selection is performed.

The original cohort's sole incomplete pair is
`claude-sonnet-5-5 / AAB15-P016`: repeats 1 and 3 give 2/2; repeat 2 remained an
empty refusal. It is not fabricated or counted as a valid result. Claude's final
score is 47/135 (34.8148%), not the pooled 140/404 (34.6535%).

Each row declares `evaluated_repeats`, `included_repeats`, `config_label`,
`evaluation_setting`, `scoring_policy`, `provider`, `cohort_id`, and
`agent_planned_cells`. The website must not label the entire table avg@3.

`planned_cells=3510` and `valid_cells=3509` refer to the displayed cohorts:
eight original three-repeat rows and two one-repeat rows. They are not the
historical total of all experiments. The immutable original nine-model snapshot
is retained as `snapshots/golden2-20261111.json`, with its original 3,645 planned
and 3,644 valid cells. `original_snapshot.sha256` identifies its exact bytes.

Agent (105 pairs), Reasoning (30 pairs) and benchmark scores are independently
reaggregated from the exact same pair scores. The mode-weighted and
benchmark-weighted averages reconstruct the primary score. Leaderboard ranks
use competition ranking: Gemini and Terra share second place; hy4 and Claude
share fourth. Unequal repetition counts, providers and effort settings limit
direct comparisons.

The collection is a manually selected development set with historical labels,
not an independently sampled hidden test. Fixed A/B ordering and A78/B55/tie2
produce three baselines: uniform A/B/tie 33.33%, uniform A/B 49.26%, always A
57.78%. Every model is below the always-A baseline in this snapshot.

`mode_baselines` supplies the matching baseline accuracies and aggregate label
distribution for `all`, `agent` and `reasoning`. Mode-filtered leaderboards must
use those values rather than the overall baselines. `baselines` remains the
original overall array for compatibility.

Resource metrics include failed requests and recovery attempts for each row's
selected repeats. Cached input is a subset of total input. Mean Agent model turns
use `agent_planned_cells`: 315 for original rows, 105 for the new single-repeat
rows. Tool rounds and tool calls are different counts. Original and recovery
request events and tool logs are counted separately; a resumed logical turn
remains an attempted model turn in its recovery layer. The combined score file
alone is insufficient for usage because it retains final-layer counters.

For the two new cohorts, tokens are summed from all-layer per-request records
filtered to repeat 1. Request attempts and model turns come from each layer's
request events; tool rounds and calls come from that layer's tool log. Compact
record-manifest hashes and per-layer totals are retained in `source_layers`.

Original `reported_cost_cny` values are explicitly reported charges, not
reconciled invoices. For the new rows `reported_cost_cny` is null;
`estimated_cost_usd` reproduces each source report's historical usage-pricing
method for selected repeat 1. These estimates are approximately USD 35.45 for
Sol and USD 7.67 for Terra. They are not current price claims or account bills.
Unknown usage remains unknown. Do not sum currencies or treat unknown charges
as zero.

## Rebuild with authorized source data

The source handoff remains outside the repository. Given authorized access:

```bash
python3 scripts/prepare_data.py --handoff /path/to/authorized-handoff
python3 scripts/merge_results.py \
  --sol-run /path/to/sol-xhigh-golden2-avg1-20261111 \
  --terra-run /path/to/terra-golden2-20261111
python3 -m unittest discover -s tests -p 'test_data.py' -v
```

The first builder creates the frozen v0.1.0 snapshot and independently validates
all 3,644 original valid logical responses against
their choices and labels, validates the one missing-repeat exception, computes
scores with exact rational arithmetic, and checks against both supplied final
summary files. The merger starts from that frozen snapshot, selects repeat 1
explicitly from both new runs, validates complete pair coverage and correctness,
recomputes mode/benchmark summaries and ranks, then aggregates both source
layers. Both scripts discard private detail and export aggregates only.

Source hashes in `provenance.source_files` and `provenance.additional_cohorts`
identify the exact input bytes; they
do not grant public access to private input files or assert redistribution rights.

No model API calls or candidate execution are made by this builder. The public
snapshot tests run without access to the private handoff. A complete fresh model
evaluation requires a separately versioned runner and authorized input assets.
