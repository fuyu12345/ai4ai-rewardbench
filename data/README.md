# Public Golden2 snapshot

`public-benchmark.json` contains 135 catalog records, 17 benchmark counts, nine
model summaries, grouped accuracies, resource totals, protocol notes and source
SHA-256 digests. Ratios use the range 0–1; multiply by 100 once for display.

The website snapshot is built with a strict field allowlist. It contains no
individual gold labels, individual model responses, raw trace bodies, server
addresses, internal paths or contributor directory names. Aggregate label
counts are retained because the three simple baselines are necessary context.
The catalog is metadata, not a redistribution of the candidate code or datasets.

## Score interpretation

The primary score is the mean of 135 pair scores. Each pair score is the mean
correctness of its three valid repeats. The sole exception is
`claude-sonnet-5-5 / AAB15-P016`: repeats 1 and 3 give 2/2; repeat 2 remained an
empty refusal. It is not fabricated or counted as a valid result. Claude's final
score is 47/135 (34.8148%), not the pooled 140/404 (34.6535%).

Agent (105 pairs), Reasoning (30 pairs) and benchmark scores are independently
reaggregated from the exact same pair scores. The mode-weighted and
benchmark-weighted averages reconstruct the primary score. Leaderboard ranks
use competition ranking: tied third place is followed by fifth.

The collection is a manually selected development set with historical labels,
not an independently sampled hidden test. Fixed A/B ordering and A78/B55/tie2
produce three baselines: uniform A/B/tie 33.33%, uniform A/B 49.26%, always A
57.78%. Every model is below the always-A baseline in this snapshot.

`mode_baselines` supplies the matching baseline accuracies and aggregate label
distribution for `all`, `agent` and `reasoning`. Mode-filtered leaderboards must
use those values rather than the overall baselines. `baselines` remains the
original overall array for compatibility.

Resource metrics include failed requests and recovery attempts. Cached input is
a subset of total input. Mean Agent model turns use 315 planned Agent cells per
model as denominator; tool rounds and tool calls are different counts. CNY costs
are explicitly reported charges, not a reconciled invoice. Do not turn unknown
charges into zero.

## Rebuild with authorized source data

The source handoff remains outside the repository. Given authorized access:

```bash
python3 scripts/prepare_data.py --handoff /path/to/authorized-handoff
python3 -m unittest discover -s tests -p 'test_data.py' -v
```

The builder independently validates all 3,644 valid logical responses against
their choices and labels, validates the one missing-repeat exception, computes
scores with exact rational arithmetic, and checks against both supplied final
summary files. It then discards private detail and exports aggregates only.
Source hashes in `provenance.source_files` identify the exact input bytes; they
do not grant public access to private input files or assert redistribution rights.

No model API calls or candidate execution are made by this builder. The public
snapshot tests run without access to the private handoff. A complete fresh model
evaluation requires a separately versioned runner and authorized input assets.
