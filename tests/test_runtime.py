"""Publication and matched-subset invariants for the typical-benchmark figures."""
import csv
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]

class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'data/public-runtime.json').read_text())
        cls.pairs = {p['pair_id']: p for p in json.loads((ROOT / 'data/public-benchmark.json').read_text())['pairs']}

    def test_matched_coverage_and_selection(self):
        data = self.data
        self.assertEqual(len(data['models']), 4)
        self.assertEqual(len(data['benchmarks']), 6)
        self.assertEqual(len(data['points']), 24)
        ids = []
        for bench in data['benchmarks']:
            ids.extend(bench['pair_ids'])
            self.assertEqual(bench['pairs'], len(bench['pair_ids']))
            self.assertGreaterEqual(bench['experiment_seconds'], data['selection']['min_benchmark_median_seconds'])
            self.assertTrue(all(self.pairs[p]['bench'] == bench['name'] for p in bench['pair_ids']))
            for mode, count in bench['mode_counts'].items():
                self.assertEqual(sum(self.pairs[p]['mode'] == mode for p in bench['pair_ids']), count)
        self.assertEqual(len(ids), 31)
        self.assertEqual(len(set(ids)), 31)
        for model in data['models']:
            points = [p for p in data['points'] if p['model'] == model['id']]
            self.assertEqual({p['bench'] for p in points}, {b['name'] for b in data['benchmarks']})
            self.assertEqual(sum(p['judgments'] for p in points), 93)
            for point in points:
                bench = next(b for b in data['benchmarks'] if b['name'] == point['bench'])
                self.assertEqual(point['judgments'], 3 * bench['pairs'])
                self.assertGreater(point['judgment_seconds'], 0)

    def test_partial_clocks_and_csv_are_explicit(self):
        scopes = {b['name']: b['scope'] for b in self.data['benchmarks']}
        self.assertEqual(scopes['PostTrainBench'], 'training_only')
        self.assertEqual(scopes['MLSBench'], 'published_subtask')
        with (ROOT / 'data/public-runtime.csv').open() as source:
            rows = list(csv.DictReader(source))
        self.assertEqual(len(rows), 24)
        for row in rows:
            point = next(p for p in self.data['points'] if p['model'] == row['model'] and p['bench'] == row['benchmark'])
            self.assertEqual(float(row['judgment_seconds']), point['judgment_seconds'])
            self.assertEqual(row['timing_scope'], scopes[row['benchmark']])

    def test_publication_boundary_and_chart_coverage(self):
        raw = (ROOT / 'data/public-runtime.json').read_text()
        for forbidden in ['/Users/', '/mnt/', 'original_path', 'correct', 'gold_label', 'api_key']:
            self.assertNotIn(forbidden, raw)
        for model in self.data['models']:
            path = ROOT / 'docs/assets/runtime' / (model['asset'] + '.svg')
            svg = path.read_text()
            self.assertEqual(len(re.findall(r'id="bench-\d+"', svg)), 6)
            self.assertIn('Selected typical benchmarks', svg)
            self.assertNotIn('/Users/', svg)
            self.assertTrue(path.with_suffix('.png').is_file())

if __name__ == '__main__':
    unittest.main()
