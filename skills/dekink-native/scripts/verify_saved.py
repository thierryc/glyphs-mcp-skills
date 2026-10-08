"""Native saved-file read/verification; never edits, saves or closes a font."""
import hashlib
import json
import math
from pathlib import Path
import objc
from Foundation import NSURL


def verify(font, params):
    output = Path(params['report_path'])
    if output.exists() or str(font.filepath) != params['expected_path']:
        raise ValueError('Wrong document or existing output')
    module = {'__name__': 'dekink_saved_adapter', 'Glyphs': Glyphs}
    source = params['adapter_source']
    if hashlib.sha256(source.encode()).hexdigest() != params['adapter_sha256']:
        raise ValueError('Adapter hash mismatch')
    exec(compile(source, 'native_adapter.py', 'exec'), module)
    geo_source = params['geometry_source']
    if hashlib.sha256(geo_source.encode()).hexdigest() != params['geometry_sha256']:
        raise ValueError('Geometry hash mismatch')
    geo = {'__name__': 'dekink_saved_geometry'}
    exec(compile(geo_source, 'geometry.py', 'exec'), geo)
    snapshot, call = module['snapshot'], module['call']
    original = snapshot(font)
    source_hash = hashlib.sha256(Path(params['expected_path']).read_bytes()).hexdigest()
    loaded = objc.lookUpClass('GSFont').alloc().initWithURL_error_(NSURL.fileURLWithPath_(params['expected_path']), None)
    if isinstance(loaded, tuple):
        loaded, error = loaded
    if loaded is None or call(loaded, 'parent') is not None:
        raise RuntimeError('Native saved-font load failed')
    saved = snapshot(loaded)
    assert set(saved) == set(original)
    ctx = module['context'](loaded)
    rows = []
    for name in sorted(saved):
        glyph, layers = module['pair'](loaded, name, ctx)
        assert module['compatible'](glyph, layers) is None
        for key in original[name]:
            a, b = original[name][key], saved[name][key]
            assert a['width'] == b['width'] and a['shape_count'] == b['shape_count']
            assert len(a['paths']) == len(b['paths'])
            for p, q in zip(a['paths'], b['paths']):
                assert p['closed'] == q['closed'] and len(p['nodes']) == len(q['nodes'])
                for n, m in zip(p['nodes'], q['nodes']):
                    assert n['type'] == m['type'] and n['smooth'] == m['smooth']
                    assert math.dist(n['xy'], m['xy']) <= .001
                    # Stored HOI coordinate serialization can change within 0.001u.
                    old, new = n['attributes'] or {}, m['attributes'] or {}
                    assert set(old) == set(new)
                    for attr in old:
                        if attr != 'hoi':
                            assert old[attr] == new[attr]
                        else:
                            assert set(old[attr]) == set(new[attr])
                            for axis in old[attr]:
                                assert set(old[attr][axis]) == set(new[attr][axis])
                                for kind, value in old[attr][axis].items():
                                    if kind == 'ip':
                                        assert math.dist(value, new[attr][axis][kind]) <= .001
                                    else:
                                        assert value == new[attr][axis][kind]
        found, excluded = module['joins'](layers[0])
        for j in found:
            j['id'] = f"{name}/{j['path']}/{j['node']}"
        measured = module['measurements'](layers, ctx, found, [i / 1000 for i in range(1001)], geo)
        for key, value in measured.items():
            assert not value['invalid'] and value['peak']['error_u'] <= .001
            rows.append({'id': key, 'peak': value['peak'], 'sample_count': value['sample_count']})
    assert snapshot(font) == original
    assert hashlib.sha256(Path(params['expected_path']).read_bytes()).hexdigest() == source_hash
    result = {'source_sha256': source_hash, 'adapter_sha256': params['adapter_sha256'],
              'geometry_sha256': params['geometry_sha256'],
              'host': {'version': str(Glyphs.versionString), 'build': int(Glyphs.buildNumber)},
              'loaded_saved_font_natively': True, 'bound_font_unchanged': True,
              'tolerance_u': .001, 'sample_count': sum(r['sample_count'] for r in rows),
              'passed': len(rows), 'failed': 0, 'rows': rows, 'sampled_only': True}
    with output.open('x') as handle:
        json.dump(result, handle, indent=2)
        handle.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    verify(font, params)
