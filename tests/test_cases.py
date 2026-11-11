"""Release boundaries and source identity for the curated case explorer."""

from collections import Counter
import json
from pathlib import Path, PurePosixPath
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE_HASHES = {
    ("AAB15-P016", "A/rsi_method/reconstruct.py"):
        "e6259844eb2415e395f85700de1ee5ce746f737d5026d24252cbebbd508d4e96",
    ("AAB15-P016", "B/rsi_method/reconstruct.py"):
        "87496f70906b56a1f504838a0b53e2f853a10d118120fe0633a269b844222b1a",
    ("KBV3N-083", "A/solution.py"):
        "371750d9410bb5e5828fc13e62b5f9d7a82a7e2f460586a8b7eeff1ca9d7d795",
    ("KBV3N-083", "B/solution.py"):
        "7516c111d6806c0c95317e6e5704b105bf04005e211f67a95105a24fd53eb5bf",
    ("NG15-P001", "A/train_gpt_simple.py"):
        "9a7765f01291dbe257c8704e75d031017cee1139e52ff2673de5c2ddddb73b57",
    ("NG15-P001", "B/train_gpt_simple.py"):
        "3875c2744561f6a26c2c46955061a3df34caa9341da549f48279e921666f589d",
}
INPUT_HASHES = {
    "AAB15-P016": "1cf91b2d8bf40cac696ef34177cbb3624a9adcbd4bb18eff5c9dd697b9635b58",
    "KBV3N-083": "dfa5339a5e7dfd70a81db41188bf49e429cc33c68e36ae540f08abd69fbb4d75",
    "NG15-P001": "936d12747b61538838ce72d1f457e9e8b6f8260aa4251e37da792019ce92f3c4",
}


class CaseReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (ROOT / "data/public-cases.json").read_text()
        cls.data = json.loads(cls.raw)
        cls.cases = {case["id"]: case for case in cls.data["cases"]}

    def assert_public_relative_path(self, value):
        path = PurePosixPath(value)
        self.assertFalse(path.is_absolute())
        self.assertNotIn("..", path.parts)
        self.assertNotIn("organizer", path.parts)
        self.assertNotIn("\\", value)

    def test_three_frozen_cases_cover_both_modes(self):
        self.assertEqual(len(self.data["cases"]), 3)
        self.assertEqual(set(self.cases), set(INPUT_HASHES))
        self.assertEqual(Counter(case["mode"] for case in self.cases.values()),
                         {"agent": 1, "reasoning": 2})
        expected_counts = {"AAB15-P016": 2, "KBV3N-083": 3, "NG15-P001": 2}
        for pair_id, case in self.cases.items():
            self.assertEqual(case["pair_id"], pair_id)
            self.assertEqual(len(case["evidence"]), expected_counts[pair_id])
            self.assertEqual(set(case["candidates"]), {"A", "B"})

    def test_verified_source_identity_and_authored_summary_boundary(self):
        observed_sources = set()
        for pair_id, case in self.cases.items():
            self.assertEqual(case["provenance"]["input_sha256"], INPUT_HASHES[pair_id])
            self.assertTrue(case["provenance"]["source_files_verified_against_manifest"])
            for item in case["evidence"]:
                key = (pair_id, item["source"])
                observed_sources.add(key)
                self.assertEqual(item["sha256"], SOURCE_HASHES[key])
                self.assertEqual(item["hash_scope"], "complete_source_file")
                self.assertEqual(item["kind"], "authored_summary")
                self.assertIn("authored source summary", item["label"])
                self.assertGreaterEqual(item["line_start"], 1)
                self.assertGreaterEqual(item["line_end"], item["line_start"])
                self.assertEqual(item["lines"], f'{item["line_start"]}–{item["line_end"]}')
                self.assert_public_relative_path(item["source"])
                self.assertNotRegex(item["text"], r"__global__|torch::Tensor|optimizer1\s*=|RESCALE_ALPHA\s*=|```")
        self.assertEqual(observed_sources, set(SOURCE_HASHES))

    def test_twenty_seven_unique_trace_records_and_references(self):
        total = 0
        valid = 0
        expected = {(model, repeat) for model in self.data["models"] for repeat in (1, 2, 3)}
        self.assertEqual(len(expected), 9)
        for case in self.cases.values():
            traces = case["traces"]
            total += len(traces)
            self.assertEqual(len(traces), 9)
            self.assertEqual({(t["model"], t["repeat"]) for t in traces}, expected)
            for trace in traces:
                self.assertEqual(trace["mode"], case["mode"])
                self.assertEqual(trace["orientation"], "AB")
                layers = {layer["id"]: layer for layer in trace["layers"]}
                self.assertEqual(len(layers), len(trace["layers"]))
                self.assertIn("main", layers)
                for event in trace["events"]:
                    self.assertIn(event["layer"], layers)
                    self.assertIsInstance(event["turn"], int)
                    self.assertGreaterEqual(event["turn"], 0)
                    for tool in event["tools"]:
                        self.assertIn(tool["name"], {"list_files", "read_file", "search", "inspect_data", "read_array", "read_table"})
                        self.assertEqual(set(tool), {"name", "arguments", "error"})
                        self.assertLessEqual(set(tool["arguments"]),
                                             {"path", "start", "end", "limit", "offset", "line_start", "line_end"})
                        if "path" in tool["arguments"]:
                            self.assert_public_relative_path(tool["arguments"]["path"])
                if trace["status"] == "valid":
                    valid += 1
                    self.assertTrue(trace["scoring_included"])
                    self.assertIn(trace["answer"], {"A", "B", "tie"})
                    answers = [event for event in trace["events"] if event["kind"] == "answer"]
                    self.assertEqual(len(answers), 1)
                    self.assertEqual(answers[0]["turn"], trace["accepted_turn"])
                    self.assertTrue(layers[answers[0]["layer"]]["selected"])
                    self.assertEqual(sum(layer["selected"] for layer in layers.values()), 1)
                if case["mode"] == "reasoning":
                    self.assertFalse(any(event["kind"] == "tool" for event in trace["events"]))
                    self.assertTrue(any(event["kind"] == "input" for event in trace["events"]))
        self.assertEqual(total, 27)
        self.assertEqual(valid, 26)

    def test_claude_refusal_is_not_fabricated_or_scored(self):
        failures = [(case["id"], trace) for case in self.cases.values()
                    for trace in case["traces"] if trace["status"] != "valid"]
        self.assertEqual(len(failures), 1)
        pair_id, trace = failures[0]
        self.assertEqual((pair_id, trace["model"], trace["repeat"]),
                         ("AAB15-P016", "claude-sonnet-5-5", 2))
        self.assertFalse(trace["scoring_included"])
        self.assertIsNone(trace["answer"])
        self.assertIsNone(trace["accepted_turn"])
        self.assertEqual(len(trace["layers"]), 3)
        self.assertFalse(any(layer["selected"] for layer in trace["layers"]))
        refusals = [event for event in trace["events"] if event["kind"] == "refusal"]
        self.assertEqual(len(refusals), 3)
        self.assertEqual({event["layer"] for event in refusals},
                         {"main", "recovery-1", "recovery-2"})
        self.assertEqual({event["turn"] for event in refusals}, {5})
        self.assertFalse(any(event["kind"] == "answer" for event in trace["events"]))

    def test_release_has_no_sensitive_payloads_or_private_labels(self):
        self.assertNotRegex(self.raw, r"/mnt/|/Users/|/home/|/root/|\b(?:\d{1,3}\.){3}\d{1,3}\b")
        self.assertNotRegex(self.raw, r"(?i)Bearer\s+[A-Za-z0-9]|sk-[A-Za-z0-9]{16}|BEGIN .*PRIVATE KEY|api[_-]?key\s*[:=]")
        self.assertNotRegex(self.raw, r"\b(?:call_|req_|chatcmpl-)[A-Za-z0-9]{10,}")
        forbidden_keys = {"gold", "correct", "private_label", "reasoning_content",
                          "thoughtSignature", "api_key", "authorization", "response_body"}

        def inspect(value):
            if isinstance(value, dict):
                self.assertFalse(forbidden_keys.intersection(value))
                for child in value.values():
                    inspect(child)
            elif isinstance(value, list):
                for child in value:
                    inspect(child)

        inspect(self.data)

    def test_pruning_candidate_summaries_include_both_changed_parameters(self):
        candidates = self.cases["AAB15-P016"]["candidates"]
        for candidate, alpha, cap in (("A", "0.4", "1.5"), ("B", "0.1", "1.15")):
            self.assertIn(alpha, candidates[candidate])
            self.assertIn(cap, candidates[candidate])
            self.assertIn("cap", candidates[candidate])


if __name__ == "__main__":
    unittest.main()
