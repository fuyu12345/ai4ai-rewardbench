#!/usr/bin/env python3
"""Merge the explicit rep1 official-API cohorts into the Golden2 public snapshot.

This deliberately does not select a best repeat. Original and recovery requests
are both counted for the selected repeat, without exporting raw response data.
"""

import argparse
from collections import Counter
import copy
from fractions import Fraction
import hashlib
import json
from pathlib import Path

BENCH_ALIASES = {
    "mle": "MLE-Bench", "terminal-bench-science-0.1": "Terminal-Bench Science",
    "rsi_exam": "RSI-Exam", "airs_bench": "AIRS-Bench", "rsibench_harness": "RSIBench Harness",
}


def read_json(path):
    return json.loads(path.read_text())


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def select_rep1(rows, model, pair_map):
    """Validate and select exactly repeat 1, regardless of other repeat scores."""
    selected = [dict(row) for row in rows if row["model"] == model and row["repeat"] == 1]
    if len(selected) != len(pair_map) or len({row["pair_id"] for row in selected}) != len(pair_map):
        raise ValueError("Repeat 1 must cover every pair exactly once")
    if {row["pair_id"] for row in selected} != set(pair_map):
        raise ValueError("Repeat 1 pair set differs from the frozen catalog")
    for row in selected:
        pair = pair_map[row["pair_id"]]
        if row["status"] != "valid" or row["orientation"] != "AB":
            raise ValueError("Expected valid, fixed-AB responses")
        bench = BENCH_ALIASES.get(row["bench_id"], row["bench_id"])
        if row["mode"] != pair["mode"] or bench.casefold() != pair["bench"].casefold():
            raise ValueError("Response mode or benchmark differs from the catalog")
        row["bench_id"] = pair["bench"]
        if row["gold"] not in ("A", "B", "tie") or type(row["correct"]) is not bool:
            raise ValueError("Invalid scoring fields")
        if row["correct"] != (row["choice"] == row["gold"]):
            raise ValueError("Correctness does not match choice and frozen label")
    return selected


def aggregate_layers(run, model, pair_map):
    """Count real requests/tool logs in each layer; resumed turn IDs stay local."""
    totals = Counter()
    layers = []
    source_files = []
    for layer in [run] + sorted(run.glob("recovery-*")):
        if not layer.is_dir() or not (layer / "jobs.jsonl").exists():
            continue
        jobs = [job for job in read_jsonl(layer / "jobs.jsonl") if job["model"] == model and job["repeat"] == 1]
        if not jobs:
            continue
        job_map = {job["job_id"]: job for job in jobs}
        if len(job_map) != len(jobs):
            raise ValueError("Duplicate layer job")
        if any(job["pair_id"] not in pair_map for job in jobs):
            raise ValueError("Layer contains an unknown pair")
        sent = [event for event in read_jsonl(layer / "events.jsonl")
                if event.get("job_id") in job_map and event["event"] == "request_sent"]
        agent_sent = [event for event in sent if job_map[event["job_id"]]["mode"] == "agent"]
        counts = Counter(api_request_attempts=len(sent),
                         agent_model_turns=len({(event["job_id"], event["turn"]) for event in agent_sent}))
        hashed_files = [layer / "jobs.jsonl", layer / "events.jsonl", layer / "config.json"]
        for job in jobs:
            base = layer / "runs" / model / job["pair_id"] / "rep1" / "AB"
            result_path = base / "result.json"
            if not result_path.exists():
                raise ValueError("Every selected layer job must have a terminal result")
            hashed_files.append(result_path)
            tool_path = base / "tools.jsonl"
            if tool_path.exists():
                hashed_files.append(tool_path)
                logs = read_jsonl(tool_path)
                if job["mode"] == "agent":
                    counts["agent_tool_rounds"] += len({row["turn"] for row in logs})
                    counts["agent_tool_calls"] += len(logs)
            for error_path in sorted(base.glob("turn-*.error.json")):
                hashed_files.append(error_path)
                error = read_json(error_path)
                counts["failed_transport_attempts"] += 1
                counts["possibly_billed_error_attempts"] += bool(error.get("request_may_be_billed"))
        # A compact digest commits to all selected input records without copying
        # internal paths or response content into the public data artifact.
        digest = hashlib.sha256()
        for path in sorted(hashed_files):
            digest.update(f"{path.relative_to(layer).as_posix()}\0{sha256(path)}\n".encode())
        layer_id = "original" if layer == run else layer.name
        layers.append({"layer": layer_id, "selected_repeat": 1, "selected_jobs": len(jobs),
                       **dict(counts), "record_manifest_sha256": digest.hexdigest()})
        for name in ("config.json", "jobs.jsonl", "events.jsonl"):
            source_files.append({"name": f"{layer_id}/{name}", "sha256": sha256(layer / name)})
        totals.update(counts)
    if not layers or layers[0]["selected_jobs"] != len(pair_map):
        raise ValueError("Missing complete original layer")
    return dict(totals), layers, source_files


def official_row(run, model, effort, pair_map, expected_counts):
    config = read_json(run / "config.json")
    if config["models"] != [model] or config["reasoning_effort"] != effort:
        raise ValueError("Requested model/effort differs from source configuration")
    if config["endpoint"] != "https://api.openai.com/v1/responses":
        raise ValueError("Expected the official Responses endpoint")
    scores_path = run / "combined" / "scored-results.private.json"
    requests_path = run / "combined" / "metrics.per_request.json"
    selected = select_rep1(read_json(scores_path), model, pair_map)
    counts = (sum(row["correct"] for row in selected),
              sum(row["correct"] for row in selected if row["mode"] == "agent"),
              sum(row["correct"] for row in selected if row["mode"] == "reasoning"))
    if counts != expected_counts:
        raise ValueError(f"Unexpected frozen rep1 result: {model}: {counts}")
    requests = [row for row in read_json(requests_path) if row["model"] == model and row["repeat"] == 1]
    if len({row["response_path"] for row in requests}) != len(requests):
        raise ValueError("Duplicate usage record would double-count tokens")
    if any(row["pair_id"] not in pair_map for row in requests):
        raise ValueError("Usage record contains an unknown pair")
    totals, layers, source_files = aggregate_layers(run, model, pair_map)
    token_fields = ("input_tokens", "output_tokens", "cached_input_tokens", "cache_creation_input_tokens", "reasoning_tokens")
    tokens = {field + "_known": sum(row[field] for row in requests if row.get(field) is not None) for field in token_fields}
    # Reproduce the historical report's price estimate, not a current price or
    # an invoice. Unknown usage remains unknown and is not estimated as free.
    usd_estimate = 0
    for request in requests:
        inp, out, cached = (request.get(field) for field in ("input_tokens", "output_tokens", "cached_input_tokens"))
        if inp is None or out is None or cached is None:
            continue
        long = inp > 272000
        if model == "gpt-6.1-sol":
            rate_in, rate_cached, rate_out = (4, .2, 15) if long else (2, .1, 10)
        else:
            rate_in, rate_cached, rate_out = (2, .1, 7.5) if long else (1, .05, 5)
        usd_estimate += ((inp - cached) * rate_in + cached * rate_cached + out * rate_out) / 1e6
    score = Fraction(counts[0], len(pair_map))
    label = "default" if effort == "provider_default" else effort
    cohort = "sol-xhigh-rep1-20261111" if model == "gpt-6.1-sol" else "terra-default-rep1-20261111"
    row = {
        "model": model, "question_equal_weight_accuracy": float(score), "exact_fraction": str(score),
        "valid": len(selected), "correct": counts[0], "planned": len(pair_map), "pair_count": len(pair_map),
        "agent_accuracy": counts[1] / 105, "reasoning_accuracy": counts[2] / 30,
        "per_bench": {
            bench: sum(item["correct"] for item in selected if item["bench_id"] == bench) /
                   sum(item["bench_id"] == bench for item in selected)
            for bench in dict.fromkeys(pair["bench"] for pair in pair_map.values())
        },
        **tokens, **totals,
        "agent_mean_model_turns_per_planned_cell": totals["agent_model_turns"] / 105,
        "agent_planned_cells": 105, "evaluated_repeats": 1, "included_repeats": [1],
        "config_label": label, "evaluation_setting": f"Official OpenAI Responses · {label} · rep1",
        "scoring_policy": "avg@1; repeat 1 only, no best-repeat selection",
        "provider": "OpenAI official API", "cohort_id": cohort,
        "source_repeats_available": config["repeats"],
        "reported_cost_cny": None, "estimated_cost_usd": usd_estimate,
        "cost_status": "Historical usage-based USD estimate; no provider-reported CNY charge; not an account bill",
        "usage_scope": "All original and recovery attempts for repeat 1 only",
        "source_layers": layers,
        "usage_response_records": len(requests),
        "responses_without_usage": sum(not request.get("usage_present") for request in requests),
        "returned_models": sorted({request["returned_model"] for request in requests if request.get("returned_model")}),
    }
    source_files.extend({"name": name, "sha256": sha256(run / name)} for name in
                        ("combined/scored-results.private.json", "combined/metrics.per_request.json", "combined/billing_summary.json"))
    return row, {"cohort_id": cohort, "source_run": run.name, "source_files": source_files}


def merge(base, sol_run, terra_run):
    result = copy.deepcopy(base)
    if result["model_count"] != 9 or result["release_version"] != "0.1.0":
        raise ValueError("Merge must start with the frozen v0.1.0 nine-model snapshot")
    pair_map = {row["pair_id"]: row for row in result["pairs"]}
    original_rows = [row for row in result["leaderboard"] if row["model"] != "gpt-6.1-sol"]
    for row in original_rows:
        row.update(evaluated_repeats=3, included_repeats=[1, 2, 3], config_label="default",
                   evaluation_setting="DMX proxy · provider defaults · 3 repeats",
                   scoring_policy="avg@3" if row["model"] != "claude-sonnet-5-5" else "avg@3; AAB15-P016 uses repeats 1 and 3 (avg@2)",
                   provider="DMX proxy", cohort_id="golden2-frozen-20261111", agent_planned_cells=315,
                   usage_scope="All original and recovery attempts for included model and all three planned repeats")
    sol, sol_provenance = official_row(sol_run, "gpt-6.1-sol", "xhigh", pair_map, (60, 40, 20))
    terra, terra_provenance = official_row(terra_run, "gpt-6.1-terra", "provider_default", pair_map, (56, 37, 19))
    rows = sorted(original_rows + [sol, terra], key=lambda row: Fraction(row["exact_fraction"]), reverse=True)
    previous, rank = None, 0
    for index, row in enumerate(rows, 1):
        exact = Fraction(row["exact_fraction"])
        if exact != previous:
            rank = index
        row["rank"] = rank
        previous = exact
    result.update(schema_version="1.1", release_version="0.1.1", snapshot_date="2026-11-12",
                  leaderboard=rows, model_count=len(rows),
                  planned_cells=sum(row["planned"] for row in rows),
                  valid_cells=sum(row["valid"] for row in rows),
                  cell_count_scope="Displayed leaderboard cohorts only: eight original three-repeat rows plus two repeat-1 rows")
    result["original_snapshot"] = {
        "release_version": "0.1.0", "snapshot_date": base["snapshot_date"],
        "model_count": 9, "planned_cells": 3645, "valid_cells": 3644,
        "path": "snapshots/golden2-20261111.json",
        "note": "Frozen original nine-model snapshot retained; the old default Sol row is replaced, not relabeled as xhigh",
    }
    result["evaluation_cohorts"] = [
        {"id": "golden2-frozen-20261111", "model_count": 8, "evaluated_repeats": 3,
         "planned_cells": 3240, "valid_cells": 3239, "provider": "DMX proxy"},
        {"id": sol["cohort_id"], "model_count": 1, "evaluated_repeats": 1,
         "planned_cells": 135, "valid_cells": 135, "provider": sol["provider"]},
        {"id": terra["cohort_id"], "model_count": 1, "evaluated_repeats": 1,
         "planned_cells": 135, "valid_cells": 135, "provider": terra["provider"]},
    ]
    result["scoring_policy"].pop("all_other_model_pair_cells", None)
    result["scoring_policy"]["repetitions"] = "Per-row: Sol xhigh and Terra default use rep1 only (avg@1); eight original rows use avg@3 except the documented Claude single-pair avg@2"
    result["protocol"].update(provider="Mixed: DMX proxy for original rows; official OpenAI Responses for new Sol and Terra rows",
                                  run_dates=["2026-11-10", "2026-11-11"],
                                  sampling="Provider defaults; Sol's new row explicitly sets reasoning effort xhigh",
                                  repeats="Per-row evaluated_repeats", agent_planned_cells_per_model="Per-row agent_planned_cells")
    result["caveats"][1] = "Repetition counts differ: Sol xhigh and Terra default use repeat 1 only; original rows use three repeats with the documented Claude single-pair avg@2 exception. These are not uniformly avg@3 results."
    result["caveats"][3] = "Original model IDs are DMX proxy aliases; new Sol and Terra evaluations use the official OpenAI Responses API. Provider and effort differ across cohorts."
    result["caveats"][10] = "Original costs are provider-reported CNY. New Sol and Terra costs are historical usage-based USD estimates with missing-usage attempts unknown; currencies and charge types must not be added together."
    result["provenance"]["additional_cohorts"] = [sol_provenance, terra_provenance]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=Path("data/snapshots/golden2-20261111.json"))
    parser.add_argument("--sol-run", required=True, type=Path)
    parser.add_argument("--terra-run", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/public-benchmark.json"))
    args = parser.parse_args()
    result = merge(read_json(args.base), args.sol_run, args.terra_run)
    result["original_snapshot"]["sha256"] = sha256(args.base)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(f"Wrote {len(result['leaderboard'])} rows; displayed cohort coverage {result['valid_cells']}/{result['planned_cells']}")


if __name__ == "__main__":
    main()
