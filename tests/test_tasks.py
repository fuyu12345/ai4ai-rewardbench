"""Public task catalog contract, provenance, and critical protocol regressions."""
from collections import Counter
import json
from pathlib import Path, PurePosixPath
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]

class TaskCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=(ROOT/'data/public-tasks.json').read_text()
        cls.data=json.loads(cls.raw)
        cls.tasks={t['pair_id']:t for t in cls.data['tasks']}
        cls.catalog=json.loads((ROOT/'data/public-benchmark.json').read_text())['pairs']

    def test_exact_catalog_coverage_and_modes(self):
        self.assertEqual(self.data['task_count'],135)
        self.assertEqual(len(self.data['tasks']),135)
        self.assertEqual(len(self.tasks),135)
        self.assertEqual(set(self.tasks),{p['pair_id'] for p in self.catalog})
        self.assertEqual(Counter(t['mode'] for t in self.tasks.values()),{'agent':105,'reasoning':30})
        self.assertEqual(len({t['bench'] for t in self.tasks.values()}),17)
        for p in self.catalog:
            t=self.tasks[p['pair_id']]
            self.assertEqual(t['bench'],p['bench'])
            self.assertEqual(t['mode'],p['mode'])
            self.assertEqual(t['input_cue_flag'],p['input_cue_flag'])

    def test_english_substantive_display_fields(self):
        for t in self.tasks.values():
            with self.subTest(pair=t['pair_id']):
                self.assertGreater(len(t['title']),10)
                self.assertGreater(len(t['background']),40)
                self.assertGreater(len(t['task']),350)
                self.assertGreater(len(t['decision_rule']),40)
                self.assertNotEqual(t['title'],t['pair_id'])
                self.assertTrue(t['conditions'])
                for value in [t['title'],t['background'],t['task'],t['decision_rule'],*t['conditions'],*t['candidates'].values()]:
                    self.assertIsNone(re.search(r'[\u4e00-\u9fff]',value))
                self.assertEqual(set(t['candidates']),{'A','B'})
                self.assertTrue(all(len(v)>60 for v in t['candidates'].values()))
                self.assertIn('not bundled',t['disclosure'])

    def test_relative_metadata_and_hashes(self):
        for t in self.tasks.values():
            self.assertTrue(t['provenance']['inspected_sources_match_manifest'])
            self.assertIn(t['provenance']['text_kind'],{'edited_public_task_statement','authored_english_translation_summary','authored_contract_summary'})
            self.assertEqual(t['input_files_shown'],len(t['input_files']))
            self.assertLessEqual(t['input_files_shown'],24)
            self.assertGreaterEqual(t['input_file_count'],t['input_files_shown'])
            refs=t['input_files']+t['provenance']['source_files']
            for f in refs:
                self.assertFalse(PurePosixPath(f['path']).is_absolute())
                self.assertNotIn('..',PurePosixPath(f['path']).parts)
                self.assertNotIn('organizer',PurePosixPath(f['path']).parts)
                self.assertRegex(f['sha256'],r'^[0-9a-f]{64}$')
            inspected={s['path'] for s in t['provenance']['source_files']}
            self.assertTrue({'TASK.md','CONTEXT.json','DECISION_RULE.json','manifest.json'}<=inspected)
            self.assertTrue(any(p.startswith('A/') for p in inspected))
            self.assertTrue(any(p.startswith('B/') for p in inspected))

    def test_no_private_payload_or_candidate_source_bodies(self):
        self.assertIsNone(re.search(r'/mnt/|/Users/|/root/|ssh |BEGIN .*PRIVATE KEY|sk-[A-Za-z0-9]{20,}',self.raw))
        def visit(value):
            if isinstance(value,dict):
                self.assertFalse({'gold','original_gold','correct','correctness','private_evidence','source_code','raw_response'} & set(value))
                for v in value.values():visit(v)
            elif isinstance(value,list):
                for v in value:visit(v)
        visit(self.data)

    def test_task_specific_protocol_boundaries(self):
        self.assertIn('three complete stochastic runs',self.tasks['AIRS-010']['decision_rule'])
        self.assertIn('3,190',self.tasks['NG15-P020']['title'])
        self.assertIn('3,250',self.tasks['NG15-P021']['title'])
        self.assertIn('9,984',self.tasks['mlagentbench-v3-20261107-043']['task'])
        self.assertIn('350',self.tasks['PTB-P112']['candidates']['A'])
        self.assertIn('600',self.tasks['PTB-P112']['candidates']['B'])
        self.assertIn('250',self.tasks['RSI-048']['candidates']['A'])
        self.assertIn('all six public cases',self.tasks['RSI-036']['decision_rule'])
        self.assertIn('1,024',self.tasks['RSI-050']['candidates']['B'])

    def test_readable_typography_and_nonrepeated_background(self):
        for t in self.tasks.values():
            self.assertFalse(t['task'].startswith(t['background']),t['pair_id'])
        pruning=self.tasks['AAB15-P016']
        self.assertIn('about 70% zeros',pruning['background'])
        self.assertIn('32 decoder layers',pruning['task'])
        self.assertIn('128 C4 training-shard sequences, 2048 tokens each, seed 0',pruning['task'])
        self.assertIn('coefficient 0.4',pruning['candidates']['A'])
        self.assertIn('coefficient 0.1',pruning['candidates']['B'])
        kernel=self.tasks['KBV3N-083']
        self.assertIn('A [4096] and B [4096, 4096]',kernel['background'])
        self.assertIn('diag(A) @ B',kernel['background'])
        self.assertIn('16 × 16',kernel['candidates']['A'])
        self.assertIn('256-thread',kernel['candidates']['B'])
        self.assertIn('AdamW',self.tasks['NG15-P001']['candidates']['A'])
        self.assertIn('NadamW',self.tasks['NG15-P001']['candidates']['B'])

if __name__=='__main__':unittest.main()
