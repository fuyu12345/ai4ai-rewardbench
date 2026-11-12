# Animated workflow preview

The process player on the Sites homepage illustrates two workflows:

- Construction: discover public/available local traces; organize Bench → Task → Run → Unit; extract, audit and screen Units; skill-guided pair curation with Codex-6 Astra; human review; per-benchmark golden pairs.
- Evaluation: open public pair inputs; inspect through Reasoning or read-only Reward Agent; compare; submit a structured prediction; validate and preserve original/recovery attempts; score offline with question-equal weighting and separate resource accounting.

This is an explanatory animation, not a live run or a claim that all existing v0.1 pairs have already been rebuilt under the new Unit-first process. Unit extraction/screening does not construct pairs. A Unit contains the generation process and artifact identity and links real evaluation feedback; absent information is recorded, never invented. Private reference labels and label evidence do not enter judge inputs.

The player supports step selection, previous/next, play/pause/replay, run-format and evaluation-mode switches. It plays once when first scrolled into view, stops at the end, and suspends its timer off-screen or in a hidden tab. Reduced-motion preferences disable automatic playback and visual transitions; manual step navigation remains available.

Source is split between `web/src/pipeline.js` (state and explanations), `pipeline.css` (player layout), and `pipeline-scenes.js` / `pipeline-scenes.css` (schematic scenes). The normal static build inlines all files. There are no animation libraries, external assets, model calls, or new data dependencies.

## Preview publication

This change is developed on `codex/animated-pipelines` and published only to the existing Sites project. Do not push or merge it into GitHub `main` until the GitHub Pages update is requested. The Pages workflow publishes only `main`; a normal feature-branch push does not deploy it.
