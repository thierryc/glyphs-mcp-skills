"""Run ONE bounded phase on an explicitly bound working copy of the old font.

Requires hash-bound adapter/geometry source and a new report path. Each phase
persists a progress marker before native calls so uncertain outcomes have a
diagnostic record. No Save, Close, document switching, or automatic replay.
"""
import hashlib
import json
from pathlib import Path


def run_phase(font, params):
    output = Path(params['report_path'])
    if output.exists():
        raise ValueError('Refusing to overwrite a phase report')
    if str(font.filepath) != params['expected_path']:
        raise ValueError('Wrong bound working copy')
    phase = params['phase']
    if phase not in ('inspect', 'sample', 'review', 'apply', 'rerun'):
        raise ValueError('Unknown test phase')
    module = {'__name__': 'previous_font_adapter', 'Glyphs': Glyphs}
    source = params['adapter_source']
    if hashlib.sha256(source.encode()).hexdigest() != params['adapter_sha256']:
        raise ValueError('Adapter hash mismatch')
    exec(compile(source, 'native_adapter.py', 'exec'), module)
    geo_source = params['geometry_source']
    if hashlib.sha256(geo_source.encode()).hexdigest() != params['geometry_sha256']:
        raise ValueError('Geometry hash mismatch')
    geo = {'__name__': 'previous_font_geometry'}
    exec(compile(geo_source, 'geometry.py', 'exec'), geo)
    state = {'phase': phase, 'status': 'running', 'last_stage': 'loaded_sources',
             'expected_path': params['expected_path'], 'adapter_sha256': params['adapter_sha256'],
             'geometry_sha256': params['geometry_sha256'],
             'host': {'version': str(Glyphs.versionString), 'build': int(Glyphs.buildNumber)}}
    with output.open('x') as handle:
        json.dump(state, handle, indent=2)

    def progress(stage):
        state['last_stage'] = stage
        output.write_text(json.dumps(state, indent=2) + '\n')

    try:
        progress('context')
        ctx = module['context'](font)
        progress('snapshot')
        before = module['snapshot'](font)
        if set(before) != {'kink.test', 'smooth.control'}:
            raise ValueError('Expected previous two-glyph regression font')
        state['context'] = ctx
        if phase == 'inspect':
            state['snapshot'] = before
        elif phase == 'sample':
            glyph, layers = module['pair'](font, 'kink.test', ctx)
            if module['compatible'](glyph, layers):
                raise ValueError('Previous fixture has unsupported topology')
            found, excluded = module['joins'](layers[0])
            for j in found:
                j['id'] = f"kink.test/{j['path']}/{j['node']}"
            progress('native_samples_0_50_100')
            state['native'] = module['measurements'](layers, ctx, found, [0, .5, 1], geo)
            state['excluded'] = excluded
            if not any(r['peak'] and r['peak']['error_u'] > 1 for r in state['native'].values()):
                raise RuntimeError('Fixture no longer has a meaningful native kink')
        else:
            progress('adapter_' + phase)
            # Persist where a native stall occurs without changing adapter logic.
            original_clone, original_sample = module['clone'], module['sample']
            sample_calls = [0]
            def traced_clone(subject):
                progress('native_detached_font_copy')
                return original_clone(subject)
            def traced_sample(lower, upper, context, factor):
                sample_calls[0] += 1
                progress('native_sample_' + str(sample_calls[0]) + '_factor_' + str(factor))
                return original_sample(lower, upper, context, factor)
            module['clone'], module['sample'] = traced_clone, traced_sample
            options = {'expected_path': params['expected_path'], 'geometry_source': geo_source,
                       'geometry_sha256': params['geometry_sha256'], 'glyphs': ['kink.test', 'smooth.control'],
                       'sample_intervals': params.get('sample_intervals', 20),
                       'threshold_u': 1, 'tolerance_u': .001,
                       'mode': 'apply' if phase == 'apply' else 'review'}
            if phase == 'apply':
                options['expected_fingerprint'] = params['expected_fingerprint']
                options['selected_ids'] = params['selected_ids']
            result = module['execute'](font, options)
            state['result'] = result
            if phase == 'review' and (len(result['issues']) != 1 or len(result['plans']) != 1):
                raise RuntimeError('Expected one kink and one verified proposal')
            if phase == 'apply' and result['applied_entries'] < 1:
                raise RuntimeError('Expected a committed repair')
            if phase == 'rerun' and (result['issues'] or result['plans']):
                raise RuntimeError('Repair did not become a repeat-run no-op')
        progress('preservation')
        after = module['snapshot'](font)
        if phase != 'apply' and after != before:
            raise RuntimeError('Read-only phase changed recorded font state')
        if phase == 'apply' and after['smooth.control'] != before['smooth.control']:
            raise RuntimeError('Control glyph changed')
        state['status'] = 'pass'
        state['last_stage'] = 'complete'
    except Exception as exc:
        state['status'] = 'fail'
        state['error'] = str(exc)
        output.write_text(json.dumps(state, indent=2) + '\n')
        raise
    output.write_text(json.dumps(state, indent=2) + '\n')
    print(json.dumps({'phase': phase, 'status': state['status'], 'report_path': str(output),
                      'result': state.get('result', state.get('native', {}))}, indent=2))


if __name__ == '__main__':
    run_phase(font, params)
