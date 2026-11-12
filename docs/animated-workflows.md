# Pair construction animation preview

The Sites homepage illustrates one six-step curation workflow:

1. Discover public and available local trajectories for each benchmark.
2. Organize Bench → Task → Run → Unit. Search trees, agent sessions, and single-step rollouts are shown together as supported Run forms.
3. Extract, audit and screen Units, linking generation, artifacts and real execution feedback. Missing information is preserved explicitly; this stage does not construct pairs.
4. Apply skill-guided pair curation with Codex-6 Astra.
5. Review comparisons and their evidence with human reviewers.
6. Freeze versioned golden pairs per benchmark, separating public inputs from private labels and evidence.

This is a process illustration, not a live run or a claim that all existing v0.1 pairs have been rebuilt using the new Unit-first process. The evaluation animation and format selectors have been removed.

The player supports step selection, previous/next, play/pause/replay and keyboard navigation. It plays once when first scrolled into view and suspends its timer off-screen or in a hidden tab. Reduced-motion preferences disable automatic playback and visual transitions.

## Preview publication

Changes on `codex/animated-pipelines` are published only to the existing Sites project. Do not merge or push these changes to GitHub `main` until a GitHub Pages update is requested. The Pages workflow publishes only `main`.
