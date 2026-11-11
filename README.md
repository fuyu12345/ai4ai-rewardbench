# AI4AI RewardBench

AI4AI RewardBench evaluates whether a model can judge competing algorithmic solutions under a task's conditions, resource constraints, and comparison rule.

[Homepage](https://ai4ai-rewardbench-v01.candid-book-7348.chatgpt.site) · [Repository](https://github.com/fuyu12345/ai4ai-rewardbench) · [Evaluation protocol](docs/protocol.md) · [Data notes](data/README.md)

This repository is the **v0.1 Golden2 homepage and verified results snapshot**. It contains a lightweight, responsive website with a mode-filtered leaderboard, benchmark distribution, searchable task catalog, and curated evidence/trace explorer. The visual system follows FRONTIS VI. It has no runtime package dependencies, server database, or model API integration.

## Snapshot

| Item | Count |
| --- | ---: |
| Preference pairs | 135 |
| Source benchmarks | 17 |
| Agent / Reasoning pairs | 105 / 30 |
| Evaluated model IDs | 9 |
| Valid / planned evaluation cells | 3,644 / 3,645 |
| Curated cases / displayed model–repeat trace records | 3 / 27 |

The collection was evaluated on 10–11 November 2026. It is a manually selected development collection with historical labels, not an independently sampled hidden test set. The current results measure agreement with frozen preferences; preference reversal, reward-model training, and downstream research gains remain future work.

## Run locally

Requirements: Node.js 20.11 or later, npm, and Python 3. No `npm install` step is needed.

```bash
npm test
npm run build
npm run dev
```

Open the printed local URL, normally `http://127.0.0.1:4173`. Set `PORT` to choose another port. The development command serves `dist/`; rerun `npm run build` after editing source or data, then refresh the browser.

The build creates a self-contained `dist/index.html` with inline CSS, JavaScript, and data. The page can also be opened directly from disk. Keep the other generated files beside it for the protocol and JSON download links to work. Any static host can serve the contents of `dist/`.

## What is included

- `data/public-benchmark.json`: 135 task metadata records, benchmark counts, model scores, mode and benchmark breakdowns, cumulative resource metrics, baseline definitions, and source fingerprints.
- `data/public-cases.json`: three authored case summaries with source file references and 27 inspected model–repeat records, including the documented refusal. Model predictions are not reference labels.
- `web/src/`: the HTML template, styles, and browser interactions.
- `scripts/build.mjs` and `scripts/serve.mjs`: dependency-free static build and local server.
- `scripts/prepare_data.py`: allowlisted export and exact-rational aggregate scoring from an authorized frozen handoff.
- `tests/test_data.py`: score, coverage, ranking, baseline, and publication-boundary checks that run against the bundled snapshot.
- `docs/`: the [protocol](docs/protocol.md), [case provenance](docs/case-provenance.md), and [homepage references](docs/references.md).

Full candidate packages, datasets, private reference labels, organizer evidence, and the complete raw trajectory collection are **not included**. The task catalog is metadata, and case evidence is authored summary text rather than redistributed candidate source code. The public trace view preserves inspected actions and selected predictions; it is not a full raw-log replay.

## Read the leaderboard correctly

The primary score first averages accepted repeats within each question, then gives every question equal weight. Normally there are three repeats. The sole exception is `claude-sonnet-5-5 / AAB15-P016`, scored from repeats 1 and 3 as avg@2; repeat 2 remained a refusal. Claude's score is `47/135 = 34.8148%`, not pooled `140/404` accuracy. The Agent and Reasoning tabs use their own question subsets and corresponding baselines.

The overall label distribution is A: 78, B: 55, tie: 2. Uniform A/B/tie, random A/B, and always-A baselines are 33.33%, 49.26%, and 57.78%. All nine models fall below always-A on this fixed-order collection. The main table retains full-run resource totals when switching accuracy modes; mean Agent turns always divide by 315 planned Agent cells.

Tokens and interaction counts include original runs, failures, retries, format repairs, and recovery. Cache input is part of total input. Explicitly reported CNY charges are not a reconciled account bill, and unknown charges are not zero. Exact API IDs were recorded through the DMX proxy; they do not independently establish served checkpoint identities. See the [full protocol](docs/protocol.md) for budgets and limitations.

## Rebuild the data export

The website and tests work with the included public snapshot. Re-exporting the benchmark data requires separately authorized access to the frozen internal handoff:

```bash
python3 scripts/prepare_data.py --handoff /path/to/authorized-handoff
npm test
npm run build
```

The exporter validates the accepted-repeat matrix, recomputes scores, checks the supplied final summaries, and emits only allowlisted aggregate fields. It makes no model API calls and does not execute candidates. The source hashes identify the input bytes without distributing private files. Curated cases have a separate extraction and verification record in [case provenance](docs/case-provenance.md).

This is offline score reproduction, not a portable implementation of the historical evaluation runner. A fresh end-to-end model evaluation requires separately versioned runner code, adapters, and authorized task assets. Dataset changes or changed evaluation conditions require a new version instead of overwriting Golden2 results.

## License and release scope

Code and data licensing have not yet been selected. No open-source or dataset license is granted by this repository. The availability of metadata, source references, or an upstream manifest does not confer redistribution rights over candidate code, datasets, models, or calibration assets. See [NOTICE](NOTICE). Full input and trajectory releases remain separate decisions.
