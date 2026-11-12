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

    def test_available_repeats_and_unique_trace_records(self):
        total = 0
        valid = 0
        repeats = {model: [1, 2, 3] for model in ("gpt-6.1-sol", "gpt-6.1-terra",
                   "claude-opus-5-5", "gemini-4-argon", "claude-sonnet-5-5")}
        expected = {(model, repeat) for model, available in repeats.items() for repeat in available}
        self.assertEqual(len(expected), 15)
        for case in self.cases.values():
            traces = case["traces"]
            total += len(traces)
            self.assertEqual(len(traces), 15)
            self.assertEqual(case["available_repeats"], repeats)
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
                        self.assertLessEqual(set(tool), {"name", "arguments", "error", "returned_range",
                                                        "returned_file_count", "total_file_lines", "output_sha256"})
                        self.assertTrue({"name", "arguments", "error"}.issubset(tool))
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
        self.assertEqual(total, 45)
        self.assertEqual(valid, 44)

    def test_final_explanations_and_observations_are_attributed(self):
        expected_new = {
            ('AAB15-P016', 'gpt-6.1-sol', 1): ('B', '630156ef2b2621f6439a8f3c5a64d61124db81ef6dac5cf9dfe87a891b8d2e37', 2),
            ('AAB15-P016', 'gpt-6.1-sol', 2): ('B', 'e29e1851dd2875510c79cd273c98840d8481f41bad3a0b9bbc54807837a081ca', 1),
            ('AAB15-P016', 'gpt-6.1-sol', 3): ('B', '7bbbc7adf34c9ed145b99f146590d1ec40878e9d3141b69fe6889c492f2f91c7', 1),
            ('AAB15-P016', 'gpt-6.1-terra', 1): ('B', '20137b2d4d633614c7f4ace5e9512d38bfba30c2494c6277f07a445351b8050b', 2),
            ('AAB15-P016', 'gpt-6.1-terra', 2): ('B', '7852108fd2816133a7cb2afe8b7c5bdaff4f40a5be94d87299dace6f7e9d599f', 2),
            ('AAB15-P016', 'gpt-6.1-terra', 3): ('B', '92e9d41e620889b400d8e6eeec8b75b7cfc7cb492534669754d63d1f0ff3d5f9', 1),
            ('AAB15-P016', 'claude-opus-5-5', 1): ('B', '791e80ec5064eba52ebe4388cd50e45873af022096980531d2570e003f126658', 1),
            ('AAB15-P016', 'claude-opus-5-5', 2): ('B', 'cc26bc5f77a09499d7e3fcc11c9d8bdcaa29a02c63260fe1b0b6c5e69e61520d', 1),
            ('AAB15-P016', 'claude-opus-5-5', 3): ('B', 'b646c2a3ad9c5fa7a7065bbdacd1ec68a22d256d848a592fc7adfa5e105f996f', 1),
            ('KBV3N-083', 'gpt-6.1-sol', 1): ('B', 'a598d76df1a005bf39e571b158a98dc062e0990734a3541dbc1d019c2ad8cd93', 1),
            ('KBV3N-083', 'gpt-6.1-sol', 2): ('B', '0a8cba15898deb0304bbc9357585df550ed75bd7627864d5403523e99fdeca90', 1),
            ('KBV3N-083', 'gpt-6.1-sol', 3): ('B', 'f8f7b365adc44e86f2b63bffa0e707ab445596d1f912de4e7391d2183f070b0a', 1),
            ('KBV3N-083', 'gpt-6.1-terra', 1): ('B', '0c388f26d72a835be20f76ee900f4e02875dd2b357b244159bb46245e88b9751', 2),
            ('KBV3N-083', 'gpt-6.1-terra', 2): ('B', '8cabc5adcf1bf724a798836c65b8f58dd4c77857000af47b07942175de208580', 1),
            ('KBV3N-083', 'gpt-6.1-terra', 3): ('B', '339e4511ff3919b244bece01ee67868f7acb211c3b5cf4043a877d631aec6d37', 1),
            ('KBV3N-083', 'claude-opus-5-5', 1): ('B', '7cc17de30526b66f33ac398e59229bd4a8e2c083a5ab87ce364ed0c536e07a4a', 1),
            ('KBV3N-083', 'claude-opus-5-5', 2): ('B', '6f217a0901844621df6f3f88c877ac2f20b001ca9b6da4d25fe1aa63da54317d', 1),
            ('KBV3N-083', 'claude-opus-5-5', 3): ('B', '036929ee87910f72665e10644532215b4d5471a32a91081a004506609523272c', 1),
            ('NG15-P001', 'gpt-6.1-sol', 1): ('A', 'af0c3b1904254ae32e4756d43d65d8277d57579b475b6591f4b0842bd246e493', 1),
            ('NG15-P001', 'gpt-6.1-sol', 2): ('B', '67f360dae44ac45cdbe3420be5556580f02a0d6fa4097da6df0d10eee85be678', 1),
            ('NG15-P001', 'gpt-6.1-sol', 3): ('A', '497cc1bfb6819abf442197780a679d1840396d57413208a653f4211a3dfc2159', 1),
            ('NG15-P001', 'gpt-6.1-terra', 1): ('A', '61ecea4e82de29665245696a200de2d540c973b462a0322b1ad5d6ff5c833a2d', 1),
            ('NG15-P001', 'gpt-6.1-terra', 2): ('A', 'ede9e30b2a104294e239eb48c4b5424979a7fca408b979e65661ebf139547da1', 1),
            ('NG15-P001', 'gpt-6.1-terra', 3): ('A', '21ce2a1027248cd5dbffd508734b228e173e624fa7ea895ab6b679fd9df18c0b', 1),
            ('NG15-P001', 'claude-opus-5-5', 1): ('tie', '933d8973988d61df6ed7fa21f79be8087670ef3d63a84f64c551e314d7981d54', 1),
            ('NG15-P001', 'claude-opus-5-5', 2): ('tie', 'cefa4f951248064f3b7a3792536036785ba4fc87df2983468725319bcbc67884', 1),
            ('NG15-P001', 'claude-opus-5-5', 3): ('tie', '5a96c349b0bdb9648876a43c8224576834f271694e3539053c9772d3eb69e68c', 1),
        }
        for case in self.cases.values():
            self.assertEqual(case["traces"][0]["model"], "gpt-6.1-sol")
            for trace in case["traces"]:
                final = trace["final_response"]
                self.assertEqual(final["kind"], "model_final_response")
                self.assertEqual(trace["analysis_summary"]["kind"], "authored_summary")
                layer_ids = {layer["id"] for layer in trace["layers"]}
                if trace["status"] == "valid":
                    self.assertEqual(final["availability"], "available")
                    self.assertEqual(final["choice"], trace["answer"])
                    self.assertGreater(len(final["reason"]), 60)
                    self.assertIn(final["text_policy"], {"verbatim_fields", "private_identifiers_redacted"})
                    self.assertTrue(final["evidence"])
                    self.assertTrue(final["uncertainties"])
                    self.assertIn(final["source"]["layer"], layer_ids)
                    self.assertRegex(final["source"]["sha256"], r"^[0-9a-f]{64}$")
                    self.assert_public_relative_path(final["source"]["file"])
                    for citation in final["evidence"]:
                        self.assertEqual(set(citation), {"file", "line_start", "line_end", "claim"})
                        self.assert_public_relative_path(citation["file"])
                    if (case["id"], trace["model"], trace["repeat"]) in expected_new:
                        choice, digest, attempt_count = expected_new[(case["id"], trace["model"], trace["repeat"])]
                        self.assertEqual((trace["answer"], final["source"]["sha256"]), (choice, digest))
                        self.assertEqual(len(trace["layers"]), attempt_count)
                        self.assertEqual(trace["delivery_provenance"]["attempt_count"], attempt_count)
                        self.assertEqual(trace["repeat_numbering"], "delivery")
                        expected_original = trace["repeat"] if trace["model"] == "claude-opus-5-5" else {1: 1, 2: 1, 3: 2}[trace["repeat"]]
                        self.assertEqual(trace["original_repeat"], expected_original)
                        self.assertEqual({layer["original_repeat"] for layer in trace["layers"]}, {expected_original})
                        self.assertEqual([layer["delivery_attempt"] for layer in trace["layers"]], list(range(1, attempt_count + 1)))
                        provenance = trace["delivery_provenance"]
                        self.assertEqual(provenance["index_file"], f'trajectories/{trace["model"]}/rep{trace["repeat"]}/{case["id"]}/index.json')
                        self.assert_public_relative_path(provenance["final_result_file"])
                        self.assertRegex(provenance["index_sha256"], r"^[0-9a-f]{64}$")
                        self.assertRegex(provenance["final_result_sha256"], r"^[0-9a-f]{64}$")
                else:
                    self.assertEqual(final["availability"], "refusal")
                    self.assertIsNone(final["reason"])
                    self.assertIsNone(final["source"])
                for event in trace["events"]:
                    analysis = event["analysis"]
                    if event["kind"] == "answer":
                        self.assertEqual(analysis["kind"], "model_final_reason")
                        self.assertEqual(analysis["text"], final["reason"])
                        self.assertIn("shown in the final explanation panel", event["detail"])
                    if event["kind"] == "tool":
                        self.assertEqual(analysis["kind"], "authored_observation")
                        self.assertEqual(analysis["availability"], "tool_only")
                        self.assertTrue(analysis["source_refs"])
                        for citation in event["final_evidence_links"]:
                            self.assertIn(citation, final["evidence"])
                    if event["kind"] == "model_message":
                        self.assertEqual(analysis["kind"], "model_message_excerpt")
                        self.assertTrue(analysis["text"])
                    for ref in analysis["source_refs"]:
                        self.assertIn(ref["layer"], layer_ids)
                        self.assertRegex(ref["sha256"], r"^[0-9a-f]{64}$")

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

    def test_model_order_settings_and_curated_display_fields(self):
        models = ["gpt-6.1-sol", "gpt-6.1-terra", "claude-opus-5-5", "gemini-4-argon", "claude-sonnet-5-5"]
        self.assertEqual(self.data["models"], models)
        self.assertFalse(self.cases["NG15-P001"]["show_limitations"])
        self.assertTrue(any("Claude Sonnet repeat 2" in note for note in self.cases["AAB15-P016"]["limitations"]))
        efforts = {"gpt-6.1-sol": "xhigh", "gpt-6.1-terra": "provider_default", "claude-opus-5-5": "high"}
        for case in self.cases.values():
            self.assertEqual([trace["model"] for trace in case["traces"]], [model for model in models for _ in range(3)])
            for trace in case["traces"]:
                self.assertNotIn("avg@", trace["run_label"])
                if trace["model"] in efforts:
                    self.assertEqual(trace["reasoning_effort"], efforts[trace["model"]])
        sol_second = next(trace for trace in self.cases["NG15-P001"]["traces"]
                          if trace["model"] == "gpt-6.1-sol" and trace["repeat"] == 2)
        self.assertEqual(sol_second["answer"], "B")
        self.assertIn("Favors B", sol_second["analysis_summary"]["text"])

    def test_pruning_candidate_summaries_include_both_changed_parameters(self):
        candidates = self.cases["AAB15-P016"]["candidates"]
        for candidate, alpha, cap in (("A", "0.4", "1.5"), ("B", "0.1", "1.15")):
            self.assertIn(alpha, candidates[candidate])
            self.assertIn(cap, candidates[candidate])
            self.assertIn("cap", candidates[candidate])


if __name__ == "__main__":
    unittest.main()
