#!/usr/bin/env python3
"""Merge the audited three-model avg@3 delivery without publishing private inputs.

The delivery index owns repetition numbering. Every linked original/recovery
attempt contributes usage once; final-layer counters are never used as totals.
"""

import argparse
from collections import Counter, defaultdict
import copy
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re

EFFORTS = {"gpt-6.1-sol": "xhigh", "gpt-6.1-terra": "provider_default", "claude-opus-5-5": "high"}
EXPECTED_CORRECT = {"gpt-6.1-sol": (178, 126, 52), "gpt-6.1-terra": (173, 116, 57), "claude-opus-5-5": (163, 106, 57)}
BENCH_ALIASES = {"mle": "MLE-Bench", "terminal-bench-science-0.1": "Terminal-Bench Science", "rsi_exam": "RSI-Exam", "airs_bench": "AIRS-Bench", "rsibench_harness": "RSIBench Harness"}
TOKEN_FIELDS = ("input_tokens", "output_tokens", "cached_input_tokens", "cache_creation_input_tokens", "reasoning_tokens")
RECORD_PATTERN = re.compile(r"^turn-(\d+)-transport-(\d+)\.(response|error)\.json$")


def read(path):
    return json.loads(path.read_text())


def read_lines(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def first_number(*values):
    return next((value for value in values if isinstance(value, (int, float)) and not isinstance(value, bool)), None)


def normalized_usage(usage):
    """Prefer normalized totals, especially Claude prompt totals including cache."""
    prompt_details = usage.get("prompt_tokens_details") or usage.get("input_tokens_details") or {}
    output_details = usage.get("completion_tokens_details") or usage.get("output_tokens_details") or {}
    billing_cache = (((usage.get("billing_usage") or {}).get("openai_usage") or {}).get("prompt_tokens_details") or {})
    return {
        "input_tokens": first_number(usage.get("prompt_tokens"), usage.get("input_tokens")),
        "output_tokens": first_number(usage.get("completion_tokens"), usage.get("output_tokens")),
        "cached_input_tokens": first_number(billing_cache.get("cached_tokens"), prompt_details.get("cached_tokens"), usage.get("cache_read_input_tokens"), usage.get("prompt_cache_hit_tokens")),
        "cache_creation_input_tokens": first_number(usage.get("cache_creation_input_tokens"), prompt_details.get("cache_write_tokens")),
        "reasoning_tokens": first_number(output_details.get("reasoning_tokens"), usage.get("reasoning_tokens")),
    }


def explicit_cny(value):
    """Only an explicitly marked CNY amount is a known CNY charge."""
    if isinstance(value, str):
        match = re.fullmatch(r"\s*(?:¥|￥|CNY\s*)\s*(\d+(?:\.\d+)?)\s*", value)
        if match:
            return Decimal(match.group(1))
    return None


def validate_cells(rows, pair_map):
    """Validate scoring and exact model × delivery-repeat × pair coverage."""
    seen = set()
    labels, input_hashes = {}, {}
    for row in rows:
        model, repeat, pair_id = row["model"], row["repeat"], row["pair_id"]
        key = model, repeat, pair_id
        if model not in EFFORTS or type(repeat) is not int or repeat not in (1, 2, 3) or pair_id not in pair_map:
            raise ValueError("Unknown delivery cell")
        if key in seen:
            raise ValueError("Duplicate delivery cell")
        seen.add(key)
        pair = pair_map[pair_id]
        bench = BENCH_ALIASES.get(row["bench"], row["bench"])
        if row["mode"] != pair["mode"] or bench.casefold() != pair["bench"].casefold():
            raise ValueError("Delivery mode/benchmark does not match the frozen catalog")
        if row["effort"] != EFFORTS[model] or row["orientation"] != "AB" or row["status"] != "valid":
            raise ValueError("Delivery configuration or validity mismatch")
        if row["gold"] not in ("A", "B", "tie") or type(row["correct"]) is not bool or row["correct"] != (row["choice"] == row["gold"]):
            raise ValueError("Delivery correctness disagrees with frozen label")
        if pair_id in labels and labels[pair_id] != row["gold"]:
            raise ValueError("Labels changed across models or repetitions")
        if pair_id in input_hashes and input_hashes[pair_id] != row["input_sha256"]:
            raise ValueError("Public input hashes changed across models or repetitions")
        labels[pair_id], input_hashes[pair_id] = row["gold"], row["input_sha256"]
    expected = {(model, repeat, pair_id) for model in EFFORTS for repeat in (1, 2, 3) for pair_id in pair_map}
    if seen != expected:
        raise ValueError("Incomplete model × repeat × pair grid")
    return input_hashes


def attempt_root(path):
    for parent in path.parents:
        if parent.name == "runs":
            return parent.parent
    raise ValueError("Attempt is outside a recorded runs directory")


def add_record_digest(hasher, identity, path):
    hasher.update(f"{identity}\0{digest(path)}\n".encode())


def collect_delivery(delivery, rows, pair_map):
    """Audit indexes/configs and deduplicate physical attempts and API records."""
    metrics = {model: Counter() for model in EFFORTS}
    tokens = {model: {field: [] for field in TOKEN_FIELDS} for model in EFFORTS}
    costs = {model: Decimal(0) for model in EFFORTS}
    returned = {model: Counter() for model in EFFORTS}
    maps = {model: Counter() for model in EFFORTS}
    hashes = {model: hashlib.sha256() for model in EFFORTS}
    source_layers = {model: {} for model in EFFORTS}
    event_cache, config_cache = {}, {}
    seen_attempts, seen_responses = {}, {}
    index_hash = hashlib.sha256()
    manifest = read(delivery / "trajectory-file-manifest.json")
    manifest_map = {(row["model"], row["repeat"], row["pair_id"], row["attempt"]): row for row in manifest}
    if len(manifest_map) != len(manifest):
        raise ValueError("Duplicate trajectory manifest entry")
    manifest_seen = set()
    for row in rows:
        model, repeat, pair_id = row["model"], row["repeat"], row["pair_id"]
        cell = delivery / "trajectories" / model / f"rep{repeat}" / pair_id
        index_path = cell / "index.json"
        if read(index_path) != row:
            raise ValueError("Per-cell index differs from all-results delivery index")
        add_record_digest(index_hash, f"{model}/{repeat}/{pair_id}", index_path)
        final_path = cell / "final-result.json"
        final = read(final_path)
        for field, expected in (("model", model), ("pair_id", pair_id), ("status", "valid"), ("canonical_choice", row["choice"]), ("input_sha256", row["input_sha256"])):
            if final.get(field) != expected:
                raise ValueError(f"Final result mismatch: {field}")
        if final.get("answer") != row["answer"]:
            raise ValueError("Final answer differs from the delivered selected answer")
        maps[model][(repeat, final["repeat"])] += 1
        previous = None
        for ordinal, attempt in enumerate(row["attempts"], 1):
            if attempt["attempt"] != ordinal:
                raise ValueError("Attempt order is not contiguous")
            manifest_key = model, repeat, pair_id, ordinal
            entry = manifest_map[manifest_key]
            manifest_seen.add(manifest_key)
            directory = (cell / f"attempt-{ordinal:02d}").resolve(strict=True)
            if directory != Path(attempt["original_path"]).resolve(strict=True) or directory != Path(entry["original_path"]).resolve(strict=True):
                raise ValueError("Attempt symlink disagrees with delivery provenance")
            identity = model, repeat, pair_id, ordinal
            if directory in seen_attempts:
                if seen_attempts[directory] != identity:
                    raise ValueError("One physical attempt assigned to multiple scored cells")
                continue
            seen_attempts[directory] = identity
            if len(entry["files"]) != attempt["files"]:
                raise ValueError("Manifest file count differs from index")
            for listed in entry["files"]:
                artifact = directory / listed["name"]
                if not artifact.is_file() or artifact.stat().st_size != listed["bytes"]:
                    raise ValueError("Trajectory manifest file missing or byte count changed")
            result_path = directory / "result.json"
            raw = read(result_path)
            if raw["model"] != model or raw["pair_id"] != pair_id or raw["input_sha256"] != row["input_sha256"]:
                raise ValueError("Attempt identity or public input differs from indexed cell")
            prior = raw.get("source_attempt")
            if (previous is None and prior) or (previous is not None and (not prior or Path(prior).resolve() != previous)):
                raise ValueError("Recovery chain omits or changes a previous attempt")
            previous = directory
            root = attempt_root(directory)
            config_path = cell / f"attempt-{ordinal:02d}-config.json"
            if config_path.resolve(strict=True) != root / "config.json":
                raise ValueError("Frozen config symlink disagrees with attempt root")
            if root not in config_cache:
                config_cache[root] = read(config_path)
                events = defaultdict(list)
                for event in read_lines(root / "events.jsonl"):
                    if event["event"] == "request_sent":
                        events[event["job_id"]].append(event)
                event_cache[root] = events
            config = config_cache[root]
            effort = config["reasoning_effort"]
            effort = effort[model] if isinstance(effort, dict) else effort
            if effort != EFFORTS[model] or model not in config["models"]:
                raise ValueError("Attempt effort/model differs from delivered configuration")
            layer = source_layers[model].setdefault(root, {"layer": f"source-{len(source_layers[model])+1:02d}", "attempt_directories": 0, "counts": Counter(), "config_sha256": digest(config_path), "events_sha256": digest(root / "events.jsonl")})
            layer["attempt_directories"] += 1
            count = Counter(attempt_directories=1)
            sent = event_cache[root][raw["job_id"]]
            request_keys = {(event["turn"], event["transport_attempt"]) for event in sent}
            if len(request_keys) != len(sent):
                raise ValueError("Duplicate request_sent event in physical attempt")
            if any(event["model"] != model or event["pair_id"] != pair_id for event in sent):
                raise ValueError("Request event identity mismatch")
            count["api_request_attempts"] = len(request_keys)
            if row["mode"] == "agent":
                count["agent_model_turns"] = len({turn for turn, _ in request_keys})
            prefix = f"{model}/{repeat}/{pair_id}/{ordinal}"
            add_record_digest(hashes[model], prefix + "/result.json", result_path)
            for request_path in sorted(directory.glob("turn-*.request.json")):
                if "-transport-" in request_path.name:
                    continue
                request = read(request_path)
                actual_effort = (request.get("reasoning") or {}).get("effort", "provider_default") if model.startswith("gpt-") else (request.get("output_config") or {}).get("effort")
                if request.get("model") != model or actual_effort != EFFORTS[model]:
                    raise ValueError("Actual request model/effort differs from frozen configuration")
                add_record_digest(hashes[model], prefix + "/" + request_path.name, request_path)
            outcomes = set()
            for record in sorted(directory.glob("turn-*.json")):
                match = RECORD_PATTERN.match(record.name)
                if not match:
                    continue
                turn, transport, kind = int(match[1]), int(match[2]), match[3]
                key = turn, transport
                if key in outcomes:
                    raise ValueError("A request has both response and error records")
                outcomes.add(key)
                obj = read(record)
                add_record_digest(hashes[model], prefix + "/" + record.name, record)
                if kind == "response":
                    response_id = obj.get("request_id")
                    identity = (model, response_id) if response_id else (model, str(record.resolve()))
                    if identity in seen_responses:
                        if seen_responses[identity] != digest(record):
                            raise ValueError("Conflicting duplicate API response identity")
                        count["duplicate_response_records_removed"] += 1
                        continue
                    seen_responses[identity] = digest(record)
                    count["usage_response_records"] += 1
                    usage = obj.get("usage") or {}
                    if obj.get("returned_model"):
                        returned[model][obj["returned_model"]] += 1
                else:
                    count["failed_transport_attempts"] += 1
                    count["possibly_billed_error_attempts"] += bool(obj.get("request_may_be_billed"))
                    salvage = record.with_name(record.name.replace(".error.json", ".failed-usage.json"))
                    saved = read(salvage) if salvage.exists() else {}
                    if salvage.exists():
                        add_record_digest(hashes[model], prefix + "/" + salvage.name, salvage)
                    usage = saved.get("usage", saved)
                normalized = normalized_usage(usage)
                for field, value in normalized.items():
                    if value is not None:
                        tokens[model][field].append(value)
                complete_usage = normalized["input_tokens"] is not None and normalized["output_tokens"] is not None
                if not complete_usage:
                    count["attempts_without_usage"] += 1
                    if kind == "response":
                        count["responses_without_usage"] += 1
                cost = explicit_cny(usage.get("cost"))
                if cost is None:
                    count["attempts_without_reported_cost"] += 1
                    if kind == "response":
                        count["responses_without_cost"] += 1
                else:
                    costs[model] += cost
                    count["responses_with_reported_cost"] += 1
            if request_keys != outcomes:
                raise ValueError("Request events and response/error artifacts do not reconcile")
            tool_log = directory / "tools.jsonl"
            if tool_log.exists():
                tool_rows = read_lines(tool_log)
                if row["mode"] == "agent":
                    count["agent_tool_calls"] = len(tool_rows)
                    count["agent_tool_rounds"] = len({tool["turn"] for tool in tool_rows})
                add_record_digest(hashes[model], prefix + "/tools.jsonl", tool_log)
            metrics[model].update(count)
            layer["counts"].update(count)
        if previous is None or final_path.resolve(strict=True) != previous / "result.json":
            raise ValueError("Selected result is not the end of the indexed attempt chain")
    if manifest_seen != set(manifest_map):
        raise ValueError("Unused trajectory manifest entries")
    output = {}
    fields = ("attempt_directories", "api_request_attempts", "agent_model_turns", "agent_tool_rounds", "agent_tool_calls", "failed_transport_attempts", "possibly_billed_error_attempts", "usage_response_records", "attempts_without_usage", "responses_without_usage", "responses_without_cost", "attempts_without_reported_cost", "responses_with_reported_cost", "duplicate_response_records_removed")
    for model in EFFORTS:
        count = metrics[model]
        output[model] = {field: count[field] for field in fields}
        output[model].update({field + "_known": sum(values) if values else None for field, values in tokens[model].items()})
        output[model].update(
            reported_cost_cny=float(costs[model]) if count["responses_with_reported_cost"] else None,
            cost_status="partial_explicit_cny" if count["attempts_without_reported_cost"] else "complete_explicit_cny",
            returned_models=sorted(returned[model]), returned_model_counts=dict(sorted(returned[model].items())),
            source_repeat_mapping=[{"repeat": repeat, "source_repeat": source_repeat, "cells": n} for (repeat, source_repeat), n in sorted(maps[model].items())],
            source_layers=[{**{key: value for key, value in layer.items() if key != "counts"}, **dict(layer["counts"])} for layer in source_layers[model].values()],
            usage_record_manifest_sha256=hashes[model].hexdigest(),
        )
    return output, {"index_manifest_sha256": index_hash.hexdigest(), "physical_attempt_directories": len(seen_attempts), "response_records": len(seen_responses), "manifest_files": sum(len(entry["files"]) for entry in manifest)}


def merge(base, delivery):
    if base["release_version"] != "0.1.0" or base["model_count"] != 9:
        raise ValueError("Start from the preserved original nine-model v0.1.0 snapshot")
    result = copy.deepcopy(base)
    pair_map = {pair["pair_id"]: pair for pair in result["pairs"]}
    rows = read(delivery / "all-results.json")
    input_hashes = validate_cells(rows, pair_map)
    if Counter(row["gold"] for row in rows if row["model"] == "gpt-6.1-sol" and row["repeat"] == 1) != base["label_distribution"]:
        raise ValueError("Delivery label distribution differs from the frozen collection")
    metrics, audit = collect_delivery(delivery, rows, pair_map)
    summaries = {row["model"]: row for row in read(delivery / "summary.json")}
    original_rows = [row for row in result["leaderboard"] if row["model"] != "gpt-6.1-sol"]
    for row in original_rows:
        row.update(evaluated_repeats=3, included_repeats=[1, 2, 3], config_label="default",
                   evaluation_setting="DMX proxy · provider defaults · 3 repeats",
                   scoring_policy="avg@3" if row["model"] != "claude-sonnet-5-5" else "avg@3; AAB15-P016 uses repeats 1 and 3 (avg@2)",
                   provider="DMX proxy", cohort_id="golden2-frozen-20261111", agent_planned_cells=315,
                   usage_scope="All original and recovery attempts for all three planned repeats")
    new_rows = []
    for model, effort in EFFORTS.items():
        selected = [row for row in rows if row["model"] == model]
        counts = (sum(row["correct"] for row in selected), sum(row["correct"] for row in selected if row["mode"] == "agent"), sum(row["correct"] for row in selected if row["mode"] == "reasoning"))
        if counts != EXPECTED_CORRECT[model]:
            raise ValueError("Delivery totals differ from the audited frozen results")
        exact = Fraction(counts[0], 405)
        if not math.isclose(float(exact), summaries[model]["avg_at_3"], abs_tol=1e-12):
            raise ValueError("Recomputed result differs from delivery summary")
        repeats = [{"repeat": repeat, "valid": 135, "correct": sum(row["correct"] for row in selected if row["repeat"] == repeat)} for repeat in (1, 2, 3)]
        for repeat in repeats:
            expected = next(item for item in summaries[model]["repeats"] if item["repeat"] == repeat["repeat"])
            if repeat["correct"] != expected["correct"] or expected["valid"] != 135:
                raise ValueError("Recomputed per-repeat result differs from summary")
        label = "default" if effort == "provider_default" else effort
        new_rows.append({
            "model": model, "question_equal_weight_accuracy": float(exact), "exact_fraction": str(exact),
            "valid": 405, "correct": counts[0], "planned": 405, "pair_count": 135,
            "agent_accuracy": counts[1] / 315, "reasoning_accuracy": counts[2] / 90,
            "per_bench": {bench: sum(row["correct"] for row in selected if pair_map[row["pair_id"]]["bench"] == bench) / sum(pair_map[row["pair_id"]]["bench"] == bench for row in selected) for bench in dict.fromkeys(pair["bench"] for pair in pair_map.values())},
            **metrics[model], "agent_mean_model_turns_per_planned_cell": metrics[model]["agent_model_turns"] / 315,
            "agent_planned_cells": 315, "evaluated_repeats": 3, "included_repeats": [1, 2, 3],
            "config_label": label, "evaluation_setting": f"{label} · 3 repeats · unified delivery",
            "scoring_policy": "avg@3; all three delivery-index repetitions, equal weight per question",
            "provider": "DMX proxy" if model.startswith("claude") else "Official OpenAI API + DMX proxy",
            "cohort_id": "three-models-avg3-delivery-20261112", "repeat_results": repeats,
            "usage_scope": "Every indexed original/recovery attempt for all three delivery repetitions, deduplicated by physical attempt and API response identity",
            "cost_note": "Known explicit CNY subtotal only; missing charges remain unknown. No currency conversion or price estimate is included.",
        })
    leaderboard = sorted(original_rows + new_rows, key=lambda row: Fraction(row["exact_fraction"]), reverse=True)
    previous, rank = None, 0
    for i, row in enumerate(leaderboard, 1):
        score = Fraction(row["exact_fraction"])
        if score != previous:
            rank = i
        row["rank"], previous = rank, score
    result.update(schema_version="1.2", release_version="0.1.2", snapshot_date="2026-11-12", model_count=11,
                  leaderboard=leaderboard, planned_cells=4455, valid_cells=4454,
                  cell_count_scope="Displayed rows: eight retained original configurations plus three complete delivery configurations, each with 405 planned cells")
    result["original_snapshot"] = {"release_version": "0.1.0", "snapshot_date": base["snapshot_date"], "model_count": 9, "planned_cells": 3645, "valid_cells": 3644, "path": "snapshots/golden2-20261111.json", "note": "Frozen original snapshot retained; default Sol has been replaced by the complete xhigh delivery"}
    result["evaluation_cohorts"] = [
        {"id": "golden2-frozen-20261111", "model_count": 8, "evaluated_repeats": 3, "planned_cells": 3240, "valid_cells": 3239},
        {"id": "three-models-avg3-delivery-20261112", "model_count": 3, "evaluated_repeats": 3, "planned_cells": 1215, "valid_cells": 1215},
    ]
    result["scoring_policy"]["repetitions"] = "Three delivery-index or frozen repetitions per model and pair; only Sonnet / AAB15-P016 retains its documented avg@2 exception"
    result["protocol"].update(run_dates=["2026-11-10", "2026-11-11", "2026-11-12"], provider="Requested-model configurations are unified across recorded delivery channels; source metadata retains returned model aliases", sampling="Sol xhigh; Opus high; other displayed settings use their recorded defaults", repeats=3, agent_planned_cells_per_model=315)
    result["caveats"][1] = "All displayed configurations use three question-weighted repetitions; the only exception is Claude Sonnet / AAB15-P016, which uses repeats 1 and 3 (avg@2)."
    result["caveats"][3] = "Rows group requested model and effort across recorded channels. Returned model aliases are retained in source metadata; Sol includes 12 responses identified as gpt-6.1-sol-2."
    result["caveats"][10] = "CNY figures are known provider-reported subtotals, not complete invoices. Some attempts lack usage or charges; no fees are estimated or converted, and missing values are not zero."
    result["caveats"].append("The latest three-model delivery owns repeat numbering; original trajectory paths may carry different repeat numbers. Every preceding attempt in the selected chains contributes to cumulative usage.")
    result["provenance"]["delivery"] = {
        "id": "three-models-avg3-delivery-20261112", "source_files": [{"name": name, "sha256": digest(delivery / name)} for name in ("all-results.json", "summary.json", "trajectory-file-manifest.json", "verification.json", "build_delivery.py")],
        **audit, "input_identity_manifest_sha256": hashlib.sha256(json.dumps(input_hashes, sort_keys=True).encode()).hexdigest(),
        "method": "Exact delivery-index grid validation; selected-answer and config checks; every preceding attempt included; raw normalized response usage; event/tool-log counts; physical-path and request-ID deduplication; explicit currency amounts only",
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delivery", required=True, type=Path)
    parser.add_argument("--base", type=Path, default=Path("data/snapshots/golden2-20261111.json"))
    parser.add_argument("--output", type=Path, default=Path("data/public-benchmark.json"))
    args = parser.parse_args()
    result = merge(read(args.base), args.delivery)
    result["original_snapshot"]["sha256"] = digest(args.base)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(f"Wrote {result['model_count']} models; {result['valid_cells']}/{result['planned_cells']} displayed cells")


if __name__ == "__main__":
    main()
