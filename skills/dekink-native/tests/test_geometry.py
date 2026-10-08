import importlib.util
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('geometry', ROOT / 'scripts/geometry.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.a = [(60, 200), (200, 200), (240, 200)]
        self.b = [(300, 120), (300, 200), (300, 400)]

    def test_single_candidates_span_and_endpoints(self):
        plans = g.candidates(self.a, self.b)
        self.assertGreaterEqual(sum(p['entries'] == 1 for p in plans), 2)
        for plan in plans:
            for i in range(1001):
                t = i / 1000
                points = [g.lerp(a, b, t) for a, b in zip(self.a, self.b)]
                for node, target in plan['targets'].items():
                    delta = g.sub(target, g.lerp(self.a[node], self.b[node], .5))
                    points[node] = g.add(points[node], g.scale(delta, 4 * t * (1 - t)))
                self.assertLess(g.metric(points)['error_u'], 1e-9)
                self.assertFalse(g.metric(points)['folded'])
                if t in (0, 1):
                    self.assertEqual(points, self.a if t == 0 else self.b)

    def test_threshold_is_strict_and_peak_not_midpoint(self):
        samples = [dict(g.metric([(0, 0), (1, y), (2, 0)]), factor=t) for t, y in [(0, 0), (.25, 2), (.5, 1), (1, 0)]]
        summary = g.summarize(samples)
        self.assertEqual(summary['peak']['factor'], .25)
        self.assertFalse(summary['peak']['error_u'] > 2)

    def test_folded_and_degenerate(self):
        self.assertTrue(g.metric([(0, 0), (2, 0), (1, 0)])['folded'])
        self.assertTrue(g.metric([(0, 0), (0, 0), (1, 0)])['degenerate'])

    def test_invalid_source(self):
        for bad in [[(0, 0), (0, 0), (1, 0)], [(0, 0), (2, 0), (1, 0)], [(0, 0), (math.nan, 0), (2, 0)]]:
            with self.assertRaises(ValueError):
                g.candidates(bad, self.b)

    def test_rounded_repaired_sources_are_not_excluded(self):
        a = [(516, 2), (303, 408), (252, 505)]
        b = [(224, 2), (318, 142), (514, 434)]
        source = [g.metric(p) for p in (a, b)]
        self.assertAlmostEqual(source[0]['error_u'], .07921540857870613)
        self.assertAlmostEqual(source[1]['error_u'], .015375406545237984)
        limit = g.verification_limit(source, .001)
        self.assertAlmostEqual(limit, .08021540857870613)
        plans = g.candidates(a, b)
        self.assertEqual(plans[0]['entries'], 1)
        self.assertEqual(plans[0]['strategy'], 'one join')
        for i in range(1001):
            t = i / 1000
            points = [g.lerp(x, y, t) for x, y in zip(a, b)]
            for node, target in plans[0]['targets'].items():
                delta = g.sub(target, g.lerp(a[node], b[node], .5))
                points[node] = g.add(points[node], g.scale(delta, 4 * t * (1 - t)))
            measured = g.metric(points)
            self.assertLessEqual(measured['error_u'], limit)
            self.assertFalse(measured['folded'])
            if t in (0, 1):
                self.assertEqual(points, a if t == 0 else b)

    def test_exact_sources_keep_absolute_tolerance(self):
        self.assertEqual(g.verification_limit([g.metric(self.a), g.metric(self.b)], .001), .001)

    def test_no_redundant_control_entries(self):
        self.assertEqual(g.candidates(self.a, [g.add(p, (10, 20)) for p in self.a]), [])

    def test_candidates_rank_count_before_movement(self):
        plans = g.candidates(self.a, self.b)
        self.assertEqual([(p['entries'], p['movement_u']) for p in plans], sorted((p['entries'], p['movement_u']) for p in plans))

    def test_opposite_source_directions_rejected(self):
        with self.assertRaises(ValueError):
            g.candidates(self.a, [(340, 200), (200, 200), (160, 200)])

    def test_calibration_accepts_native_precision_floor(self):
        written = []
        result = g.calibrate_midpoint((100, 200), written.append,
                                      lambda: (written[-1][0] - .01 + .000008, written[-1][1]), .0001)
        self.assertTrue(result['converged'])
        self.assertEqual(result['ip'], written[-1])
        self.assertLessEqual(result['error_u'], .0001)

    def test_exhausted_calibration_reports_last_actual_write(self):
        written = []
        result = g.calibrate_midpoint((100, 200), written.append, lambda: (0, 0), .0001, attempts=3)
        self.assertFalse(result['converged'])
        self.assertEqual(len(written), 3)
        self.assertEqual(result['ip'], written[-1])
        self.assertEqual(result['actual'], (0, 0))


if __name__ == '__main__':
    unittest.main()
