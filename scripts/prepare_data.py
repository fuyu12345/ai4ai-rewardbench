#!/usr/bin/env python3
"""Build the frozen v0.1.0 Golden2 metadata snapshot from an authorized handoff.

Uses only the Python standard library. Raw inputs stay outside the repository;
individual labels, answers, paths, and correctness values are never exported.
"""

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path

EXCEPTION = ("claude-sonnet-5-5", "AAB15-P016")
PAIR_FIELDS = ("pair_id", "title", "bench", "mode", "release_status", "input_cue_flag")
USAGE_FIELDS = (
    "input_tokens_known", "output_tokens_known", "cached_input_tokens_known",
    "cache_creation_input_tokens_known", "agent_model_turns", "agent_tool_rounds",
    "agent_tool_calls", "agent_mean_model_turns_per_planned_cell",
    "api_request_attempts", "reported_cost_cny",
)


def mean(values):
    values = list(values)
    if not values:
        raise ValueError("Cannot score an empty group")
    return sum(values, Fraction(0)) / len(values)


def pair_scores(rows, pairs, models):
    """Validate the complete frozen grid and return exact, private pair scores."""
    by_pair = defaultdict(dict)
    for row in rows:
        model, pair_id, repeat = row["model"], row["pair_id"], row["repeat"]
        if model not in models or pair_id not in pairs:
            raise ValueError("Unknown model or pair")
        if row["orientation"] != "AB":
            raise ValueError("Only the frozen AB orientation is accepted")
        if type(repeat) is not int or repeat not in (1, 2, 3):
            raise ValueError("Invalid repeat")
        if row["gold"] not in ("A", "B", "tie"):
            raise ValueError("Invalid frozen label")
        if type(row["correct"]) is not bool or row["correct"] != (row["choice"] == row["gold"]):
            raise ValueError("Correctness does not match the original response")
        cell = by_pair[(model, pair_id)]
        if repeat in cell:
            raise ValueError("Duplicate logical repeat")
        cell[repeat] = row["correct"]
    result = {}
    for model in models:
        for pair_id in pairs:
            key = (model, pair_id)
            cell = by_pair[key]
            expected = {1, 3} if key == EXCEPTION else {1, 2, 3}
            if set(cell) != expected:
                raise ValueError(f"Unexpected repeat coverage: {model}/{pair_id}")
            result[key] = Fraction(sum(cell.values()), len(cell))
    return result


def competition_ranks(rows, field):
    """Equal scores receive equal ranks, using exact fractions when available."""
    ordered = sorted(rows, key=lambda row: row[field], reverse=True)
    previous = None
    rank = 0
    for index, row in enumerate(ordered, 1):
        if row[field] != previous:
            rank = index
        row["rank"] = rank
        previous = row[field]
    return ordered


def build(handoff):
    source = json.loads((handoff / "site-data.json").read_text())
    reference = json.loads((handoff / "question-weighted-summary.json").read_text())
    raw_rows = [json.loads(line) for line in (handoff / "scoring-input.private.jsonl").read_text().splitlines() if line.strip()]
    pairs = [{key: row[key] for key in PAIR_FIELDS} for row in source["pairs"]]
    pair_map = {row["pair_id"]: row for row in pairs}
    if len(pairs) != 135 or len(pair_map) != 135:
        raise ValueError("Expected 135 unique frozen pairs")
    if Counter(row["mode"] for row in pairs) != {"agent": 105, "reasoning": 30}:
        raise ValueError("Unexpected mode distribution")
    if len({row["bench"] for row in pairs}) != 17:
        raise ValueError("Expected 17 benches")
    model_names = [row["model"] for row in source["leaderboard"]]
    if len(model_names) != 9 or len(set(model_names)) != 9:
        raise ValueError("Expected nine unique models")
    scores = pair_scores(raw_rows, pair_map, model_names)
    reference_models = {row["model"]: row for row in reference["models"]}
    counts = Counter(row["bench"] for row in pairs)
    benches = []
    for bench, count in counts.most_common():
        modes = Counter(row["mode"] for row in pairs if row["bench"] == bench)
        benches.append({"bench": bench, "pairs": count, "share": count / 135,
                        "agent": modes["agent"], "reasoning": modes["reasoning"]})
    leaderboard = []
    for original in source["leaderboard"]:
        model = original["model"]
        score = mean(scores[(model, pair_id)] for pair_id in pair_map)
        if not math.isclose(float(score), original["question_equal_weight_accuracy"], abs_tol=1e-12):
            raise ValueError(f"Recomputed score differs from site snapshot: {model}")
        if not math.isclose(float(score), reference_models[model]["question_equal_weight_accuracy"], abs_tol=1e-12):
            raise ValueError(f"Recomputed score differs from final policy: {model}")
        model_rows = [row for row in raw_rows if row["model"] == model]
        row = {"model": model, "question_equal_weight_accuracy": float(score),
               "exact_fraction": str(score), "valid": len(model_rows),
               "correct": sum(item["correct"] for item in model_rows),
               "planned": 405, "pair_count": 135}
        if row["valid"] != original["valid"] or row["correct"] != original["correct"]:
            raise ValueError(f"Response counts differ: {model}")
        for mode in ("agent", "reasoning"):
            row[f"{mode}_accuracy"] = float(mean(scores[(model, pair["pair_id"])] for pair in pairs if pair["mode"] == mode))
        row["per_bench"] = {
            bench: float(mean(scores[(model, pair["pair_id"])] for pair in pairs if pair["bench"] == bench))
            for bench in counts
        }
        row.update({key: original[key] for key in USAGE_FIELDS})
        leaderboard.append(row)
    leaderboard = competition_ranks(leaderboard, "question_equal_weight_accuracy")
    label_by_pair = {}
    for row in raw_rows:
        if row["pair_id"] in label_by_pair and label_by_pair[row["pair_id"]] != row["gold"]:
            raise ValueError("Frozen labels disagree across responses")
        label_by_pair[row["pair_id"]] = row["gold"]
    labels = dict(Counter(label_by_pair.values()))
    if labels != {"A": 78, "B": 55, "tie": 2}:
        raise ValueError("Unexpected aggregate label distribution")
    mode_baselines = {}
    for mode in ("all", "agent", "reasoning"):
        group = [pair for pair in pairs if mode == "all" or pair["mode"] == mode]
        distribution = Counter(label_by_pair[pair["pair_id"]] for pair in group)
        mode_baselines[mode] = {
            "uniform_three": 1 / 3,
            "random_ab": float(Fraction(distribution["A"] + distribution["B"], 2 * len(group))),
            "always_a": float(Fraction(distribution["A"], len(group))),
            "gold_distribution": {key: distribution[key] for key in ("A", "B", "tie")},
            "pair_count": len(group),
        }
    provenance_files = ["site-data.json", "question-weighted-summary.json", "scoring-input.private.jsonl"]
    return {
        "schema_version": "1.0", "release_version": "0.1.0",
        "dataset_version": source["dataset_version"],
        "collection_date": source["collection_date"], "snapshot_date": source["snapshot_date"],
        "pair_count": 135, "bench_count": 17, "model_count": 9,
        "modes": {"agent": 105, "reasoning": 30},
        "planned_cells": 3645, "valid_cells": 3644,
        "label_distribution": {key: labels[key] for key in ("A", "B", "tie")},
        "baselines": [
            {"id": "uniform-three", "name": "Uniform A / B / tie", "accuracy": 1 / 3},
            {"id": "uniform-ab", "name": "Uniform A / B", "accuracy": float(Fraction(133, 270))},
            {"id": "always-a", "name": "Always A", "accuracy": float(Fraction(78, 135))},
        ],
        "mode_baselines": mode_baselines,
        "scoring_policy": {
            "denominator_pairs": 135,
            "aggregation": "Mean over pairs of mean correctness across included repetitions",
            "all_other_model_pair_cells": "avg@3",
            "exception": {"model": EXCEPTION[0], "pair_id": EXCEPTION[1],
                          "included_repeats": [1, 3], "excluded_repeat": 2,
                          "reason": "Repeated empty refusal", "avg_at_2": 1.0},
            "usage": "All attempts, including failed requests, refusals, and recovery runs",
        },
        "protocol": {
            "run_dates": ["2026-11-10", "2026-11-11"], "provider": "DMX proxy",
            "orientation": "Fixed AB", "sampling": "Provider defaults; no fixed random seed",
            "repeats": 3, "agent_planned_cells_per_model": 315,
            "agent_tools": ["list_files", "read_file", "search", "inspect_data", "read_array", "read_table"],
            "agent_access": "Read-only, pair manifest allowlist; no code execution, network, or organizer labels",
            "reasoning_input": "All public pair materials are inlined in the prompt",
        },
        "benches": benches, "leaderboard": leaderboard, "pairs": pairs,
        "caveats": [
            "This manually selected development collection includes historical observations; it is not an independently sampled hidden test set.",
            "Scores are question-weighted. Claude / AAB15-P016 uses repeats 1 and 3 only (avg@2); all other model-pair cells use avg@3.",
            "The fixed AB orientation and imbalanced labels limit conclusions about position bias. Always A scores 57.78%, above every evaluated model in this snapshot.",
            "Provider model names are proxy aliases; the underlying checkpoints were not independently verified.",
            "Two DeepRSI inputs contain self-reported performance comments and are flagged in the catalog.",
            "32 pairs permit unresolved as abstention; it is neither a fourth gold label nor equivalent to tie.",
            "Accepted answers were recovered with consistent, lossless parsing rules; malformed-output repair attempts remain in cumulative usage.",
            "438 Gemini requests used a compatibility marker for missing thought signatures; missing server state was not recovered.",
            "Recovery budgets varied, including additional hy4 budget. This is not a uniform compute-budget comparison.",
            "Usage includes failed and recovery attempts. Cached input tokens are a subset of input tokens, not an additional total.",
            "Reported costs are explicitly returned CNY charges, not a reconciled account bill; missing charges must not be treated as zero.",
            "Candidate materials and full raw traces are not included in this website release; redistribution permissions require source-specific review.",
        ],
        "provenance": {
            "method": "Strict field allowlist; grouped accuracies recomputed from frozen valid responses using exact rational arithmetic",
            "source_files": [{"name": name, "sha256": hashlib.sha256((handoff / name).read_bytes()).hexdigest()} for name in provenance_files],
            "individual_labels_exported": False, "raw_traces_exported": False,
            "internal_paths_exported": False,
        },
        "publication_status": "Public-safe metadata and aggregate results; no blanket redistribution license for underlying inputs or traces",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff", required=True, type=Path, help="Authorized handoff directory outside this repository")
    parser.add_argument("--output", type=Path, default=Path("data/snapshots/golden2-20261111.json"),
                        help="Frozen original snapshot; use merge_results.py for the current leaderboard")
    args = parser.parse_args()
    result = build(args.handoff)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(f"Wrote {len(result['pairs'])} pairs and {len(result['leaderboard'])} model aggregates to {args.output}")


if __name__ == "__main__":
    main()
