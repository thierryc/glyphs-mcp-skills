"""Native behavioral regression on a marked disposable fixture only.

Execute with hash-bound adapter/geometry source through MCP. Writes one new
report; no Save/Close. Most tests use copies; final successful suite repairs
the bound disposable font so it can be saved through the workflow.
"""
import hashlib
import json
import traceback
from pathlib import Path
import objc
from Foundation import NSPoint


def qualify(font, params):
    output = Path(params['report_path'])
    if output.exists():
        raise ValueError('Report already exists')
    module = {'__name__': 'dekink_native_adapter', 'Glyphs': Glyphs}
    source = params['adapter_source']
    if hashlib.sha256(source.encode()).hexdigest() != params['adapter_sha256']:
        raise ValueError('Adapter hash mismatch')
    exec(compile(source, 'native_adapter.py', 'exec'), module)
    call, snapshot, copy = module['call'], module['snapshot'], module['clone']
    raw_execute, context, pair, paths, nodes = [module[k] for k in ('execute', 'context', 'pair', 'paths', 'nodes')]
    def execute(subject, options):
        # Detached native copies have no document URL. Bind their actual identity
        # here in the fixture runner; do not weaken the production path guard.
        if subject is not font:
            assert call(subject, 'parent') is None
            options = dict(options, expected_path=str(subject.filepath))
        return raw_execute(subject, options)
    if str(font.filepath) != params['expected_path'] or call(font, 'userDataForKey_', 'dekink.rebuild.fixture') != 'dekink-native-rebuild-v1':
        raise ValueError('Expected new disposable fixture')
    base = {'expected_path': params['expected_path'], 'geometry_source': params['geometry_source'],
            'geometry_sha256': params['geometry_sha256'], 'sample_intervals': 100, 'threshold_u': 1, 'tolerance_u': .001}
    original = snapshot(font)
    results = []

    def test(name, function):
        try:
            detail = function()
            results.append({'name': name, 'status': 'pass', 'detail': detail})
        except Exception as exc:
            results.append({'name': name, 'status': 'fail', 'error': str(exc), 'traceback': traceback.format_exc()})

    def review_and_minimality():
        subject = copy(font)
        before = snapshot(subject)
        report = execute(subject, base)
        assert snapshot(subject) == before and report['live_unchanged']
        assert len(report['issues']) == 5, [(r['glyph'], r['status']) for r in report['issues']]
        assert len(report['plans']) == 5, [(r['glyph'], r['status']) for r in report['issues']]
        assert all(len(p['entries']) == 1 for p in report['plans']), report['plans']
        assert not any(r['glyph'] == 'smooth.control' for r in report['issues'])
        return report

    def selected_apply_repeat():
        subject = copy(font)
        before = snapshot(subject)
        reviewed = execute(subject, base)
        selected = reviewed['plans'][0]['id']
        applied = execute(subject, dict(base, mode='apply', expected_fingerprint=reviewed['fingerprint'], selected_ids=[selected]))
        assert applied['applied_entries'] == 1
        changed_names = [name for name in before if snapshot(subject)[name] != before[name]]
        assert changed_names == [selected.split('/')[0]], changed_names
        again = execute(subject, dict(base, glyphs=changed_names))
        assert not again['issues'] and not again['plans']
        return {'selected': selected, 'changed_glyphs': changed_names, 'applied_entries': 1, 'repeat_issues': 0}

    def stale_guard():
        subject = copy(font)
        reviewed = execute(subject, dict(base, glyphs=['cubic.asymmetric']))
        _, layers = pair(subject, 'cubic.asymmetric', context(subject))
        call(layers[0], 'setWidth_', 701)
        before = snapshot(subject)
        try:
            execute(subject, dict(base, mode='apply', expected_fingerprint=reviewed['fingerprint']))
        except ValueError as exc:
            assert 'fingerprint' in str(exc) and snapshot(subject) == before
            return {'rejected': str(exc)}
        raise AssertionError('Stale proposal accepted')

    def existing_hoi():
        subject = copy(font)
        ctx = context(subject)
        _, layers = pair(subject, 'cubic.asymmetric', ctx)
        node = nodes(paths(layers[0])[0])[3]
        call(node, 'setAttribute_forKey_', {'wght': {'rc': 'auto'}}, 'hoi')
        before = snapshot(subject)
        report = execute(subject, dict(base, glyphs=['cubic.asymmetric']))
        assert not report['plans'] and snapshot(subject) == before
        return {'issues': report['issues'], 'excluded': report['excluded']}

    def other_axis_preservation():
        subject = copy(font)
        ctx = context(subject)
        _, layers = pair(subject, 'cubic.asymmetric', ctx)
        for n in nodes(paths(layers[0])[0]):
            call(n, 'setAttribute_forKey_', {'wdth': {'ip': [13, 17]}}, 'hoi')
            call(n, 'setAttribute_forKey_', 'preserve-me', 'dekink.test')
        reviewed = execute(subject, dict(base, glyphs=['cubic.asymmetric']))
        applied = execute(subject, dict(base, glyphs=['cubic.asymmetric'], mode='apply', expected_fingerprint=reviewed['fingerprint']))
        assert applied['applied_entries'] == 1
        for n in nodes(paths(pair(subject, 'cubic.asymmetric', ctx)[1][0])[0]):
            assert module['plain'](call(n, 'attributeForKey_', 'hoi'))['wdth'] == {'ip': [13, 17]}
            assert call(n, 'attributeForKey_', 'dekink.test') == 'preserve-me'
        return {'preserved_other_axis_and_node_attributes': True}

    def source_and_topology_exclusions():
        subject = copy(font)
        _, layers = pair(subject, 'cubic.asymmetric', context(subject))
        path = paths(layers[0])[0]
        old = bool(call(layers[0], 'temporarilyDisableRounding'))
        call(layers[0], 'setTemporarilyDisableRounding_', True)
        try:
            call(nodes(path)[3], 'setPosition_', NSPoint(200, 205))
        finally:
            call(layers[0], 'setTemporarilyDisableRounding_', old)
        report = execute(subject, dict(base, glyphs=['cubic.asymmetric']))
        assert any(r['reason'] == 'source_geometry_problem' for r in report['excluded']) and not report['plans']
        subject = copy(font)
        _, layers = pair(subject, 'line.middle', context(subject))
        call(nodes(paths(layers[1])[0])[2], 'setSmooth_', False)
        report = execute(subject, dict(base, glyphs=['line.middle']))
        assert report['excluded'][0]['reason'] == 'node_correspondence_mismatch'
        return {'broken_source_rejected': True, 'incompatible_flags_rejected': True}

    def strict_threshold():
        subject = copy(font)
        report = execute(subject, dict(base, glyphs=['cubic.asymmetric']))
        peak = report['issues'][0]['before']['peak']['error_u']
        report = execute(subject, dict(base, glyphs=['cubic.asymmetric'], threshold_u=peak))
        assert not report['issues']
        for invalid in [-1, float('nan')]:
            try:
                execute(subject, dict(base, threshold_u=invalid))
            except ValueError:
                continue
            raise AssertionError('Invalid threshold accepted')
        return {'native_peak_u': peak, 'equality_not_flagged': True, 'negative_nan_rejected': True}

    def multiple_paths():
        subject = copy(font)
        _, layers = pair(subject, 'cubic.asymmetric', context(subject))
        for layer in layers:
            call(layer, 'addShape_', call(paths(layer)[0], 'copy'))
        report = execute(subject, dict(base, glyphs=['cubic.asymmetric']))
        assert len(report['issues']) == len(report['plans']) == 2
        return {'discovered_path_indices': [r['path'] for r in report['issues']]}

    def rollback_failure():
        subject = copy(font)
        reviewed = execute(subject, dict(base, glyphs=['cubic.asymmetric']))
        before = snapshot(subject)
        original_sample = module['sample']
        def fail_after_live_write(lower, upper, ctx, factor):
            if lower == pair(subject, 'cubic.asymmetric', ctx)[1][0] and snapshot(subject) != before:
                raise RuntimeError('Injected verification failure')
            return original_sample(lower, upper, ctx, factor)
        module['sample'] = fail_after_live_write
        try:
            try:
                execute(subject, dict(base, glyphs=['cubic.asymmetric'], mode='apply', expected_fingerprint=reviewed['fingerprint']))
            except RuntimeError as exc:
                assert 'Injected' in str(exc) and snapshot(subject) == before
                return {'invocation_entries_rolled_back': True}
            raise AssertionError('Injected failure was not raised')
        finally:
            module['sample'] = original_sample

    requested_tests = params.get('test_names')
    catalog = [('review_readonly_five_one_entry_proposals', review_and_minimality),
                           ('selected_apply_repeat_noop', selected_apply_repeat), ('stale_review_rejected', stale_guard),
                           ('existing_local_hoi_preserved', existing_hoi), ('unrelated_attributes_preserved', other_axis_preservation),
                           ('source_and_topology_exclusions', source_and_topology_exclusions), ('strict_native_threshold', strict_threshold),
                           ('arbitrary_multiple_path_discovery', multiple_paths), ('failed_commit_rolls_back', rollback_failure)]
    if requested_tests is not None and (not isinstance(requested_tests, list) or not requested_tests or any(n not in {name for name, _ in catalog} for n in requested_tests)):
        raise ValueError('Invalid test_names')
    for name, function in catalog:
        if requested_tests is None or name in requested_tests:
            test(name, function)
    assert snapshot(font) == original, 'Copy tests changed bound fixture'
    result = {'host': {'version': str(Glyphs.versionString), 'build': int(Glyphs.buildNumber)},
              'adapter_sha256': params['adapter_sha256'], 'geometry_sha256': params['geometry_sha256'],
              'passed': sum(r['status'] == 'pass' for r in results), 'failed': sum(r['status'] == 'fail' for r in results),
              'copy_tests_left_fixture_unchanged': True, 'tests': results}
    if result['failed'] == 0 and len(results) == len(catalog) and params.get('commit_fixture', True):
        reviewed = execute(font, dict(base, sample_intervals=1000))
        applied = execute(font, dict(base, sample_intervals=1000, mode='apply', expected_fingerprint=reviewed['fingerprint']))
        assert len(applied['plans']) == 5 and applied['applied_entries'] == 5
        rerun = execute(font, dict(base, sample_intervals=1000))
        assert not rerun['issues'] and not rerun['plans']
        result['dense_live_repair'] = applied
        result['dense_repeat_issues'] = 0
        result['native_commit_samples'] = 5 * (1001 + 1000)
    with output.open('x') as handle:
        json.dump(result, handle, indent=2)
        handle.write('\n')
    print(json.dumps({'report_path': str(output), 'passed': result['passed'], 'failed': result['failed'],
                      'tests': [{'name': r['name'], 'status': r['status'], 'error': r.get('error')} for r in results],
                      'applied_entries': result.get('dense_live_repair', {}).get('applied_entries', 0)}, indent=2))


if __name__ == '__main__':
    qualify(font, params)
