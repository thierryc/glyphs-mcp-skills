"""Check verification policy without pretending to evaluate native Glyphs."""
import ast
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

source = (Path(__file__).resolve().parents[1] / 'scripts/native_adapter.py').read_text()
tree = ast.parse(source)
definitions = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
namespace = {'hashlib': hashlib, 'json': json, 'math': math}
exec(compile(ast.Module(body=definitions, type_ignores=[]), '<adapter policy>', 'exec'), namespace)
acceptable = namespace['acceptable']


def row(error, invalid=False):
    return {'invalid': invalid, 'peak': {'error_u': error}}


class AdapterPolicyTests(unittest.TestCase):
    def test_repair_requires_explicit_scope(self):
        ns = dict(namespace)
        exec(compile(ast.Module(body=definitions, type_ignores=[]), '<adapter policy>', 'exec'), ns)
        ns.update(context=lambda font: {'path': '/test.glyphs'}, snapshot=lambda font: {})
        geometry = "__name__ = 'test'"
        with self.assertRaisesRegex(ValueError, 'explicit glyph scope'):
            ns['execute'](object(), {'geometry_source': geometry,
                                    'geometry_sha256': hashlib.sha256(geometry.encode()).hexdigest(),
                                    'expected_path': '/test.glyphs', 'mode': 'repair'})

    def test_one_run_repair_of_clean_join_is_noop_without_external_fingerprint(self):
        ns = dict(namespace)
        exec(compile(ast.Module(body=definitions, type_ignores=[]), '<adapter policy>', 'exec'), ns)
        shape = {'selected': {}, 'unrelated': {}}
        measure = Mock(return_value={'selected/0/1': row(0)})
        writes = Mock(side_effect=AssertionError('Clean joins must not be written'))
        ns.update(context=lambda font: {'path': '/test.glyphs'}, snapshot=lambda font: shape,
                  clone=lambda font: object(), pair=lambda *args: (object(), [object(), object()]),
                  compatible=lambda *args: None,
                  joins=lambda layer: ([{'path': 0, 'node': 1}], []),
                  triple=lambda *args: [(0, 0), (1, 0), (2, 0)],
                  measurements=measure, set_ip=writes,
                  Glyphs=SimpleNamespace(versionString='test', buildNumber=0))
        geometry = (Path(__file__).resolve().parents[1] / 'scripts/geometry.py').read_text()
        result = ns['execute'](object(), {'geometry_source': geometry,
                                       'geometry_sha256': hashlib.sha256(geometry.encode()).hexdigest(),
                                       'expected_path': '/test.glyphs', 'mode': 'repair',
                                       'glyphs': ['selected']})
        self.assertEqual(result['applied_entries'], 0)
        self.assertTrue(result['live_unchanged'])
        self.assertFalse(result['issues'])
        self.assertGreaterEqual(measure.call_count, 3)
        writes.assert_not_called()

    def test_compact_output_preserves_verification_evidence(self):
        report = {'plans': [{'after': {'peak': {'error_u': .00001}, 'sample_count': 101,
                                       'samples': [{'error_u': 0}] * 101},
                             'committed_peak': {'error_u': .00001},
                             'interleaved_peak': {'error_u': .00002}}]}
        compact = namespace['compact_report'](report)
        self.assertNotIn('samples', compact['plans'][0]['after'])
        self.assertEqual(compact['plans'][0]['after']['sample_count'], 101)
        self.assertEqual(compact['plans'][0]['committed_peak'], report['plans'][0]['committed_peak'])
        self.assertEqual(compact['plans'][0]['interleaved_peak'], report['plans'][0]['interleaved_peak'])
        self.assertIn('samples', report['plans'][0]['after'])

    def test_source_floor_does_not_relax_other_joins(self):
        before = {'target': row(67), 'neighbor': row(0)}
        after = {'target': row(.0792), 'neighbor': row(0)}
        self.assertTrue(acceptable(before, after, 'target', .001, .0802))
        after['neighbor'] = row(.01)
        self.assertFalse(acceptable(before, after, 'target', .001, .0802))

    def test_target_excess_and_invalid_orientation_are_rejected(self):
        before = {'target': row(67)}
        self.assertFalse(acceptable(before, {'target': row(.081)}, 'target', .001, .0802))
        self.assertFalse(acceptable(before, {'target': row(.01, True)}, 'target', .001, .0802))
        self.assertFalse(acceptable(before, {'target': row(.0792)}, 'target', .001))
