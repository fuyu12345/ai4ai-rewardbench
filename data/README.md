# Public Golden2 snapshot

`public-benchmark.json` v0.1.2 contains 135 catalog records, 17 benchmark counts,
11 model configurations, grouped accuracies, cumulative resource totals,
protocol notes and source SHA-256 digests. Snapshot date: 2026-11-12. Ratios use
the range 0–1; multiply by 100 once for display.

The export contains no individual gold labels, raw model responses, raw tool
outputs, internal paths or credentials. Aggregate label counts are retained to
explain the baselines. Catalog metadata does not grant redistribution rights to
underlying candidate code or datasets.

## Current results

Eight original model rows are retained numerically. The complete three-model
delivery replaces Sol and Terra and adds Opus; each is one unified model row,
using all three delivery-index repetitions, rather than separate channel rows.

| Model | Setting | Overall | Agent | Reasoning |
| --- | --- | --- | --- | --- |
| gpt-6.1-sol | xhigh | 178/405 = 43.95% | 126/315 = 40.00% | 52/90 = 57.78% |
| gpt-6.1-terra | default | 173/405 = 42.72% | 116/315 = 36.83% | 57/90 = 63.33% |
| claude-opus-5-5 | high | 163/405 = 40.25% | 106/315 = 33.65% | 57/90 = 63.33% |

The primary score is the mean of 135 pair scores, each being the mean correctness
of included repetitions. The only exception remains **Claude Sonnet /
AAB15-P016**: repeats 1 and 3 give 2/2; repeat 2 remained an empty refusal.
Sonnet scores 47/135 (34.8148%), not pooled 140/404. Opus has no such exception.

`planned_cells=4455` and `valid_cells=4454` describe the displayed 11 rows:
eight retained original configurations (3,240 planned / 3,239 valid) and the
new delivery (1,215 planned / 1,215 valid). They are not a count of all historical
experiments. Every row has `evaluated_repeats=3`, `included_repeats=[1,2,3]` and
`agent_planned_cells=315`, with the Sonnet pair exception documented separately.

The delivery's `index.json` defines repetitions. For Sol and Terra, displayed
rep1/rep2/rep3 correspond to source final-path repeats 1/1/2. Opus corresponds
to 1/2/3. `source_repeat_mapping` preserves this mapping. Neither the source
directory's repeat number nor a best-repeat choice determines the current score.

Mode-weighted and benchmark-weighted averages reconstruct the overall score.
Competition ranks preserve ties: hy4 and Sonnet share fifth. Configurations and
recovery budgets still differ, so this is not an equal-compute comparison.

## Baselines and scope

The manually selected development collection uses historical labels and is not
an independently sampled hidden test. A78/B55/tie2 gives uniform A/B/tie 33.33%,
random A/B 49.26% and always A 57.78%. All current overall model scores are below
always A. `mode_baselines` supplies the matching distributions and denominators
for All, Agent and Reasoning tabs; `baselines` retains the overall array.

## Resource accounting

The merger reads all 1,461 physical attempt directories referenced by the
delivery, including previous attempts in each recovery chain. It verifies all
34,181 manifest entries, terminal selected answers, index identities, frozen
configurations and actual request effort fields. Scoring never reads a raw-path
repeat number as the displayed repeat.

Usage comes from the 7,338 normalized raw response records, plus any available
failed-attempt usage. API attempts are counted from request events, Agent model
turns from unique turns within each physical attempt, and tool rounds/calls from
tool logs. Repeated symlink targets and response identities cannot be counted
twice. Each request event reconciles with one response or error artifact.
Counters from only the final successful layer are not used as totals.

Input tokens prefer normalized `prompt_tokens`; for Claude these include cache
creation and cache reads, while its native `input_tokens` alone does not. Cached
input is a subset of total input. Reasoning tokens are a subset of output.
Opus does not report a reasoning-token count, so that field is null, not zero.

| Model | API attempts | Agent model turns | Tool rounds | Tool calls | Known CNY subtotal |
| --- | ---: | ---: | ---: | ---: | ---: |
| Sol | 3,023 | 2,713 | 2,328 | 11,035 | 1,061.143348 |
| Terra | 2,117 | 1,904 | 1,417 | 6,780 | 81.011926 |
| Opus | 2,816 | 2,685 | 2,311 | 3,962 | 651.880408 |

Mean Agent model turns divide by 315. The new CNY values sum only amounts
explicitly marked as CNY in the source records. They are **partial subtotals**,
not complete bills: `cost_status=partial_explicit_cny` on all three new rows.
No price estimates, currency conversions or inferred zero charges are included.

| Model | Attempts without complete usage | Responses without cost | Attempts without cost |
| --- | ---: | ---: | ---: |
| Sol | 290 | 841 | 1,131 |
| Terra | 295 | 626 | 921 |
| Opus | 33 | 0 | 33 |

These counts are exported as `attempts_without_usage`, `responses_without_cost`
and `attempts_without_reported_cost`. `responses_without_usage` is zero for all
three; missing usage comes from failed attempts. `possibly_billed_error_attempts`
retains the source classification and is distinct from missing usage. Returned
model IDs are retained in `returned_model_counts`: Sol includes 12 responses
identified as `gpt-6.1-sol-2`, without creating a separate leaderboard row.

## Provenance and reproducibility

`snapshots/golden2-20261111.json` preserves the original nine-model v0.1.0
snapshot and its 3,645 planned / 3,644 valid cells. `original_snapshot.sha256`
identifies its exact bytes. Current `provenance.delivery` records the delivery
source hashes, index digest and audit counts. Each new row has a compact digest
of the consumed request/response/error/tool/result records and source-layer
config/event hashes. Raw paths and private labels are not exported.
All 1,215 delivered rows were also independently checked against the original
frozen handoff: all 135 pair labels and public-input hashes match.

With authorized source access:

```bash
python3 scripts/prepare_data.py --handoff /path/to/authorized-handoff
python3 scripts/merge_delivery.py --delivery /path/to/three-models-avg3-delivery-20261112
python3 -m unittest discover -s tests -p 'test_data.py' -v
```

The first command rebuilds the frozen original snapshot. The second builds the
current 11-model release. The earlier `scripts/merge_results.py` is retained
only for reconstructing the historical v0.1.1 single-repeat release; its tests
remain alongside the current delivery tests. It is not the current build step.

The scripts make no model API calls and execute no candidate code. Snapshot
tests run without private data. Hashes identify source bytes; they neither grant
access to private sources nor establish redistribution rights.
