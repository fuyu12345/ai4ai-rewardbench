"""Frozen snapshot invariants and edge cases for the aggregation policy."""

from collections import Counter
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("prepare_data", ROOT / "scripts" / "prepare_data.py")
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)


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
            "gemini-4-argon": Fraction(56, 135), "gpt-6.1-sol": Fraction(143, 405),
            "hy4": Fraction(47, 135), "claude-sonnet-5-5": Fraction(47, 135),
            "deepseek-v4.1-flash": Fraction(41, 135), "glm-5.3-flash": Fraction(116, 405),
            "qwen3.8-flash": Fraction(109, 405), "kimi-k3.1-pro": Fraction(4, 15),
            "kimi-k2.6": Fraction(92, 405),
        }
        rows = self.data["leaderboard"]
        self.assertEqual({row["model"] for row in rows}, set(expected))
        self.assertEqual([row["rank"] for row in rows], [1, 2, 3, 3, 5, 6, 7, 8, 9])
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
        self.assertEqual(sum(row["valid"] for row in self.data["leaderboard"]), 3644)
        self.assertEqual(sum(row["planned"] for row in self.data["leaderboard"]), 3645)
        for row in self.data["leaderboard"]:
            self.assertEqual(row["valid"], 404 if row["model"] == "claude-sonnet-5-5" else 405)
            self.assertAlmostEqual(row["agent_mean_model_turns_per_planned_cell"], row["agent_model_turns"] / 315)
            self.assertLessEqual(row["cached_input_tokens_known"], row["input_tokens_known"])
        exception = self.data["scoring_policy"]["exception"]
        self.assertEqual((exception["model"], exception["pair_id"], exception["included_repeats"]), ("claude-sonnet-5-5", "AAB15-P016", [1, 3]))

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


if __name__ == "__main__":
    unittest.main()
