"""Capture actual native midpoint outlines before/after the prior-font repair.

MCP only, on the repaired working copy. No font changes or proof layers.
"""
import hashlib
import json
from pathlib import Path
import objc
from Foundation import NSURL


def capture(font, params):
    output = Path(params['report_path'])
    if output.exists() or str(font.filepath) != params['expected_path']:
        raise ValueError('Wrong document or existing proof output')
    original_path = Path(params['original_path'])
    if hashlib.sha256(original_path.read_bytes()).hexdigest() != params['original_sha256']:
        raise ValueError('Original fixture fingerprint mismatch')
    module = {'__name__': 'native_proof_adapter', 'Glyphs': Glyphs}
    source = params['adapter_source']
    if hashlib.sha256(source.encode()).hexdigest() != params['adapter_sha256']:
        raise ValueError('Adapter fingerprint mismatch')
    exec(compile(source, 'native_adapter.py', 'exec'), module)
    baseline = module['snapshot'](font)
    loaded = objc.lookUpClass('GSFont').alloc().initWithURL_error_(NSURL.fileURLWithPath_(str(original_path)), None)
    if isinstance(loaded, tuple):
        loaded, error = loaded
    if loaded is None or module['call'](loaded, 'parent') is not None:
        raise ValueError('Native original fixture load failed')
    rows = []
    for label, subject in [('before', loaded), ('after', font)]:
        ctx = module['context'](subject)
        glyph, layers = module['pair'](subject, 'kink.test', ctx)
        sampled = module['sample'](*layers, ctx, .5)
        path = module['paths'](sampled)[0]
        rows.append({'label': label, 'factor': .5, 'glyph': 'kink.test',
                     'points': [module['xy'](n) for n in module['nodes'](path)],
                     'types': [int(module['call'](n, 'type')) for n in module['nodes'](path)],
                     'join': 3})
    if module['snapshot'](font) != baseline:
        raise RuntimeError('Proof capture changed bound font')
    result = {'native_output': True, 'bound_font_unchanged': True, 'original_sha256': params['original_sha256'],
              'repaired_sha256': hashlib.sha256(Path(params['expected_path']).read_bytes()).hexdigest(),
              'adapter_sha256': params['adapter_sha256'],
              'host': {'version': str(Glyphs.versionString), 'build': int(Glyphs.buildNumber)}, 'rows': rows}
    output.write_text(json.dumps(result, indent=2) + '\n')
    tab = font.newTab('/kink.test/smooth.control')
    tab.previewInstances = next(i for i in font.instances if i.name == 'Regular')
    print(json.dumps({'report_path': str(output), 'native_output': True, 'bound_font_unchanged': True, 'midpoint_tab_opened': True}))


if __name__ == '__main__':
    capture(font, params)
