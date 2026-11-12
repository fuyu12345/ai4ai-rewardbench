"""Frozen snapshot invariants and edge cases for the aggregation policy."""

from collections import Counter
from fractions import Fraction
import importlib.util
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("prepare_data", ROOT / "scripts" / "prepare_data.py")
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)
merge_spec = importlib.util.spec_from_file_location("merge_results", ROOT / "scripts" / "merge_results.py")
merger = importlib.util.module_from_spec(merge_spec)
merge_spec.loader.exec_module(merger)
delivery_spec = importlib.util.spec_from_file_location("merge_delivery", ROOT / "scripts" / "merge_delivery.py")
delivery_merger = importlib.util.module_from_spec(delivery_spec)
delivery_spec.loader.exec_module(delivery_merger)


class SnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (ROOT / "data" / "public-benchmark.json").read_text()
        cls.data = json.loads(cls.raw)

    def test_catalog_counts_and_unique_ids(self):
        pairs = self.data["pairs"]
        self.assertEqual(len(pairs), 135)
        self.assertEqual(len({row["pair_id"] for row in pairs}), 135)
        self.assertEqual(Counter(row["mode"] for row in pairs), {"agent": 105, "reasoning": 30})
        self.assertEqual(len({row["bench"] for row in pairs}), 17)
        self.assertEqual(sum(row["input_cue_flag"] for row in pairs), 2)
        actual = Counter(row["bench"] for row in pairs)
        for bench in self.data["benches"]:
            self.assertEqual(bench["pairs"], actual[bench["bench"]])
            self.assertEqual(bench["agent"] + bench["reasoning"], bench["pairs"])

    def test_scores_match_frozen_exact_results_and_ties(self):
        expected = {
            "gemini-4-argon": Fraction(56, 135), "gpt-6.1-sol": Fraction(178, 405),
            "gpt-6.1-terra": Fraction(173, 405), "claude-opus-5-5": Fraction(163, 405),
            "hy4": Fraction(47, 135), "claude-sonnet-5-5": Fraction(47, 135),
            "deepseek-v4.1-flash": Fraction(41, 135), "glm-5.3-flash": Fraction(116, 405),
            "qwen3.8-flash": Fraction(109, 405), "kimi-k3.1-pro": Fraction(4, 15),
            "kimi-k2.6": Fraction(92, 405),
        }
        rows = self.data["leaderboard"]
        self.assertEqual({row["model"] for row in rows}, set(expected))
        self.assertEqual(self.data["model_count"], 11)
        self.assertEqual([row["rank"] for row in rows], [1, 2, 3, 4, 5, 5, 7, 8, 9, 10, 11])
        for row in rows:
            self.assertEqual(Fraction(row["exact_fraction"]), expected[row["model"]])
            self.assertAlmostEqual(row["question_equal_weight_accuracy"], float(expected[row["model"]]), places=14)

    def test_group_scores_reconstruct_question_weighted_total(self):
        counts = {row["bench"]: row["pairs"] for row in self.data["benches"]}
        for row in self.data["leaderboard"]:
            total = row["question_equal_weight_accuracy"]
            self.assertAlmostEqual((row["agent_accuracy"] * 105 + row["reasoning_accuracy"] * 30) / 135, total, places=14)
            self.assertEqual(set(row["per_bench"]), set(counts))
            self.assertAlmostEqual(sum(score * counts[bench] for bench, score in row["per_bench"].items()) / 135, total, places=14)

    def test_coverage_exception_and_usage_denominator(self):
        self.assertEqual(sum(row["valid"] for row in self.data["leaderboard"]), 4454)
        self.assertEqual(sum(row["planned"] for row in self.data["leaderboard"]), 4455)
        self.assertEqual(self.data["valid_cells"], 4454)
        self.assertEqual(self.data["planned_cells"], 4455)
        for row in self.data["leaderboard"]:
            expected_valid = 404 if row["model"] == "claude-sonnet-5-5" else 405
            self.assertEqual(row["valid"], expected_valid)
            self.assertEqual(row["evaluated_repeats"], 3)
            self.assertEqual(row["agent_planned_cells"], 315)
            self.assertAlmostEqual(row["agent_mean_model_turns_per_planned_cell"], row["agent_model_turns"] / row["agent_planned_cells"])
            self.assertLessEqual(row["cached_input_tokens_known"], row["input_tokens_known"])
        exception = self.data["scoring_policy"]["exception"]
        self.assertEqual((exception["model"], exception["pair_id"], exception["included_repeats"]), ("claude-sonnet-5-5", "AAB15-P016", [1, 3]))

    def test_original_snapshot_is_preserved_and_original_rows_unchanged(self):
        path = ROOT / "data" / self.data["original_snapshot"]["path"]
        original = json.loads(path.read_text())
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), self.data["original_snapshot"]["sha256"])
        self.assertEqual(original["model_count"], 9)
        self.assertEqual((original["planned_cells"], original["valid_cells"]), (3645, 3644))
        updated = {row["model"]: row for row in self.data["leaderboard"]}
        for old in original["leaderboard"]:
            if old["model"] == "gpt-6.1-sol":
                self.assertAlmostEqual(old["question_equal_weight_accuracy"], 143 / 405)
                continue
            for field, value in old.items():
                if field != "rank":
                    self.assertEqual(updated[old["model"]][field], value)

    def test_new_avg3_rows_include_all_layers_and_report_partial_costs(self):
        models = {row["model"]: row for row in self.data["leaderboard"]}
        expected = {
            "gpt-6.1-sol": (126, 52, 160349315, 2786935, 3023, 2713, 2328, 11035),
            "gpt-6.1-terra": (116, 57, 46949632, 633300, 2117, 1904, 1417, 6780),
            "claude-opus-5-5": (106, 57, 89169442, 2077046, 2816, 2685, 2311, 3962),
        }
        for model, values in expected.items():
            row = models[model]
            agent, reasoning, inp, out, requests, turns, rounds, calls = values
            self.assertAlmostEqual(row["agent_accuracy"], agent / 315)
            self.assertAlmostEqual(row["reasoning_accuracy"], reasoning / 90)
            for field, value in zip(("input_tokens_known", "output_tokens_known", "api_request_attempts", "agent_model_turns", "agent_tool_rounds", "agent_tool_calls"), (inp, out, requests, turns, rounds, calls)):
                self.assertEqual(row[field], value)
            self.assertEqual(row["included_repeats"], [1, 2, 3])
            self.assertGreater(row["reported_cost_cny"], 0)
            self.assertNotIn("estimated_cost_usd", row)
            self.assertEqual(row["cost_status"], "partial_explicit_cny")
            self.assertGreaterEqual(len(row["source_layers"]), 2)
            for field in ("api_request_attempts", "agent_model_turns", "agent_tool_rounds", "agent_tool_calls"):
                self.assertEqual(row[field], sum(layer.get(field, 0) for layer in row["source_layers"]))
        self.assertEqual(models["gpt-6.1-sol"]["config_label"], "xhigh")
        self.assertEqual(models["gpt-6.1-terra"]["config_label"], "default")
        self.assertEqual(models["claude-opus-5-5"]["config_label"], "high")
        self.assertIsNone(models["claude-opus-5-5"]["reasoning_tokens_known"])
        self.assertEqual(models["gpt-6.1-sol"]["returned_model_counts"], {"gpt-6.1-sol":2721, "gpt-6.1-sol-2":12})
        costs = {"gpt-6.1-sol": (1061.143348, 290, 841, 1131), "gpt-6.1-terra": (81.011926, 295, 626, 921), "claude-opus-5-5": (651.880408, 33, 0, 33)}
        for model, (cost, missing_usage, missing_response_cost, missing_attempt_cost) in costs.items():
            row = models[model]
            self.assertAlmostEqual(row["reported_cost_cny"], cost, places=6)
            self.assertEqual(row["attempts_without_usage"], missing_usage)
            self.assertEqual(row["responses_without_cost"], missing_response_cost)
            self.assertEqual(row["attempts_without_reported_cost"], missing_attempt_cost)
            self.assertEqual(row["api_request_attempts"], row["usage_response_records"] + row["failed_transport_attempts"])
            self.assertEqual(row["responses_without_usage"], 0)
            self.assertEqual(sum(row["returned_model_counts"].values()), row["usage_response_records"])

    def test_delivery_numbering_and_audit_coverage(self):
        for row in self.data["leaderboard"]:
            if row["model"] not in delivery_merger.EFFORTS:
                continue
            expected = [(1, 1), (2, 2), (3, 3)] if row["model"] == "claude-opus-5-5" else [(1, 1), (2, 1), (3, 2)]
            self.assertEqual([(item["repeat"], item["source_repeat"]) for item in row["source_repeat_mapping"]], expected)
            self.assertTrue(all(item["cells"] == 135 for item in row["source_repeat_mapping"]))
            self.assertEqual(sum(item["correct"] for item in row["repeat_results"]), row["correct"])
        audit = self.data["provenance"]["delivery"]
        self.assertEqual(audit["physical_attempt_directories"], 1461)
        self.assertEqual(audit["response_records"], 7338)
        self.assertEqual(audit["manifest_files"], 34181)
        for source in audit["source_files"]:
            self.assertRegex(source["sha256"], r"^[0-9a-f]{64}$")

    def test_baselines_and_publication_boundary(self):
        scores = {row["id"]: row["accuracy"] for row in self.data["baselines"]}
        self.assertAlmostEqual(scores["uniform-three"], 1 / 3)
        self.assertAlmostEqual(scores["uniform-ab"], 133 / 270)
        self.assertAlmostEqual(scores["always-a"], 78 / 135)
        self.assertIsNone(re.search(r"/mnt/|/Users/|/root/|ssh |BEGIN .*PRIVATE KEY|sk-[A-Za-z0-9]{20,}", self.raw))
        for pair in self.data["pairs"]:
            self.assertEqual(set(pair), set(pipeline.PAIR_FIELDS))
            self.assertNotIn("gold", pair)
        for source in self.data["provenance"]["source_files"]:
            self.assertRegex(source["sha256"], r"^[0-9a-f]{64}$")

    def test_mode_baselines_use_matching_denominators(self):
        modes = self.data["mode_baselines"]
        self.assertEqual(set(modes), {"all", "agent", "reasoning"})
        for mode, count in (("all", 135), ("agent", 105), ("reasoning", 30)):
            baseline = modes[mode]
            gold = baseline["gold_distribution"]
            self.assertEqual(baseline["pair_count"], count)
            self.assertEqual(sum(gold.values()), count)
            self.assertAlmostEqual(baseline["uniform_three"], 1 / 3)
            self.assertAlmostEqual(baseline["random_ab"], (gold["A"] + gold["B"]) / (2 * count))
            self.assertAlmostEqual(baseline["always_a"], gold["A"] / count)
        self.assertEqual(modes["all"]["gold_distribution"], self.data["label_distribution"])
        for label in ("A", "B", "tie"):
            self.assertEqual(modes["all"]["gold_distribution"][label],
                             modes["agent"]["gold_distribution"][label] + modes["reasoning"]["gold_distribution"][label])
        for field in ("uniform_three", "random_ab", "always_a"):
            self.assertAlmostEqual(modes["all"][field], (modes["agent"][field] * 105 + modes["reasoning"][field] * 30) / 135)


class ScoringPolicyTests(unittest.TestCase):
    def setUp(self):
        self.pairs = {"AAB15-P016": {}, "ordinary": {}}
        self.models = ["claude-sonnet-5-5"]
        self.rows = []
        for pair_id, repeats in (("AAB15-P016", (1, 3)), ("ordinary", (1, 2, 3))):
            for repeat in repeats:
                self.rows.append({"model": self.models[0], "pair_id": pair_id,
                                  "repeat": repeat, "orientation": "AB", "gold": "A",
                                  "choice": "A" if pair_id == "AAB15-P016" else "B",
                                  "correct": pair_id == "AAB15-P016"})

    def test_exception_retains_equal_pair_weight(self):
        scores = pipeline.pair_scores(self.rows, self.pairs, self.models)
        self.assertEqual(pipeline.mean(scores.values()), Fraction(1, 2))
        self.assertNotEqual(pipeline.mean(scores.values()), Fraction(2, 5))

    def test_rejects_duplicate_response(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            pipeline.pair_scores(self.rows + [self.rows[0]], self.pairs, self.models)

    def test_rejects_missing_regular_repeat(self):
        with self.assertRaisesRegex(ValueError, "coverage"):
            pipeline.pair_scores(self.rows[:-1], self.pairs, self.models)

    def test_rejects_fabricated_exception_repeat(self):
        fabricated = dict(self.rows[0], repeat=2)
        with self.assertRaisesRegex(ValueError, "coverage"):
            pipeline.pair_scores(self.rows + [fabricated], self.pairs, self.models)

    def test_rejects_changed_correctness(self):
        changed = [dict(row) for row in self.rows]
        changed[0]["correct"] = False
        with self.assertRaisesRegex(ValueError, "Correctness"):
            pipeline.pair_scores(changed, self.pairs, self.models)


class NewCohortTests(unittest.TestCase):
    def test_rep1_selection_does_not_choose_best_repeat(self):
        pairs = {"p": {"mode": "agent", "bench": "AABench"}}
        rows = [{"model": "test", "pair_id": "p", "repeat": repeat, "status": "valid",
                 "orientation": "AB", "mode": "agent", "bench_id": "aabench",
                 "gold": "A", "choice": "B" if repeat == 1 else "A", "correct": repeat != 1}
                for repeat in (1, 2, 3)]
        result = merger.select_rep1(rows, "test", pairs)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["repeat"], 1)
        self.assertFalse(result[0]["correct"])
        self.assertEqual(result[0]["bench_id"], "AABench")
        with self.assertRaisesRegex(ValueError, "exactly once"):
            merger.select_rep1(rows + [rows[0]], "test", pairs)
        with self.assertRaisesRegex(ValueError, "exactly once"):
            merger.select_rep1(rows[1:], "test", pairs)

    def test_layer_accounting_counts_original_and_recovery_but_not_rep2(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pair_map = {"p": {"mode": "agent", "bench": "Test"}}
            for layer in (root, root / "recovery-test"):
                layer.mkdir(exist_ok=True)
                jobs = [{"job_id": f"job{repeat}", "model": "test", "pair_id": "p", "repeat": repeat, "mode": "agent"} for repeat in (1, 2)]
                (layer / "jobs.jsonl").write_text("\n".join(json.dumps(job) for job in jobs))
                events = [{"event": "request_sent", "job_id": f"job{repeat}", "turn": 1} for repeat in (1, 2)]
                (layer / "events.jsonl").write_text("\n".join(json.dumps(event) for event in events))
                (layer / "config.json").write_text("{}")
                for repeat in (1, 2):
                    base = layer / "runs" / "test" / "p" / f"rep{repeat}" / "AB"
                    base.mkdir(parents=True)
                    (base / "result.json").write_text('{"status":"valid"}')
                    (base / "tools.jsonl").write_text('{"turn":1}\n')
            totals, layers, _ = merger.aggregate_layers(root, "test", pair_map)
            self.assertEqual(totals["api_request_attempts"], 2)
            self.assertEqual(totals["agent_model_turns"], 2)
            self.assertEqual(totals["agent_tool_rounds"], 2)
            self.assertEqual(totals["agent_tool_calls"], 2)
            self.assertEqual([layer["selected_jobs"] for layer in layers], [1, 1])


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.pairs = {"p": {"mode": "agent", "bench": "AABench"}}
        self.rows = [{"model": model, "effort": effort, "repeat": repeat, "pair_id": "p",
                      "bench": "aabench", "mode": "agent", "orientation": "AB", "status": "valid",
                      "gold": "A", "choice": "A", "correct": True, "input_sha256": "abc"}
                     for model, effort in delivery_merger.EFFORTS.items() for repeat in (1, 2, 3)]

    def test_complete_delivery_grid_and_index_repeat_validation(self):
        self.assertEqual(delivery_merger.validate_cells(self.rows, self.pairs), {"p": "abc"})
        changed = [dict(row) for row in self.rows]
        changed[1]["repeat"] = 1  # Raw rep1 must not replace the delivery rep2.
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            delivery_merger.validate_cells(changed, self.pairs)
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            delivery_merger.validate_cells(self.rows[:-1], self.pairs)

    def test_changed_input_or_effort_cannot_be_merged(self):
        changed = [dict(row) for row in self.rows]
        changed[2]["input_sha256"] = "changed"
        with self.assertRaisesRegex(ValueError, "input hashes"):
            delivery_merger.validate_cells(changed, self.pairs)
        changed = [dict(row) for row in self.rows]
        changed[0]["effort"] = "high"
        with self.assertRaisesRegex(ValueError, "configuration"):
            delivery_merger.validate_cells(changed, self.pairs)

    def test_normalized_claude_input_includes_cache_and_unknown_is_not_zero(self):
        result = delivery_merger.normalized_usage({"input_tokens":2, "cache_creation_input_tokens":13641,
                   "cache_read_input_tokens":7760, "prompt_tokens":21403, "output_tokens":109})
        self.assertEqual(result["input_tokens"], 21403)
        self.assertEqual(result["cached_input_tokens"], 7760)
        self.assertEqual(result["cache_creation_input_tokens"], 13641)
        self.assertIsNone(result["reasoning_tokens"])
        self.assertIsNone(delivery_merger.normalized_usage({"usage_unknown":True})["input_tokens"])

    def test_currency_is_never_guessed_or_converted(self):
        self.assertEqual(str(delivery_merger.explicit_cny("¥0.359726")), "0.359726")
        self.assertIsNone(delivery_merger.explicit_cny("$0.359726"))
        self.assertIsNone(delivery_merger.explicit_cny(0.359726))
        self.assertIsNone(delivery_merger.explicit_cny(None))


if __name__ == "__main__":
    unittest.main()
