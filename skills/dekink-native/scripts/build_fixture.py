"""Populate ONLY a bound empty disposable document; no Save or Close."""
import json
import math
import objc
from Foundation import NSPoint


def call(obj, selector, *args):
    return getattr(obj.pyobjc_instanceMethods, selector)(*args)


def definitions():
    cubic = [[[80, 40], [30, 110], [60, 200], [200, 200], [240, 200], [330, 130], [320, 50]],
             [[80, 40], [300, 40], [300, 120], [300, 200], [300, 400], [440, 390], [440, 50]]]
    angle = math.radians(-27)
    def rotated(p):
        x, y = p[0] - 250, p[1] - 200
        return [250 + x * math.cos(angle) - y * math.sin(angle), 200 + x * math.sin(angle) + y * math.cos(angle)]
    line = [[[80, 40], [80, 200], [200, 200], [440, 200], [440, 40]],
            [[80, 40], [300, 80], [300, 200], [300, 300], [440, 40]]]
    mixed_in = [[row[i] for i in (0, 2, 3, 4, 5, 6)] for row in cubic]
    mixed_out = [cubic[0][:4] + [[440, 200]], cubic[1][:4] + [[300, 400]]]
    return [
        {'name': 'cubic.asymmetric', 'points': cubic, 'types': [1, 65, 65, 35, 65, 65, 35], 'join': 3},
        {'name': 'cubic.rotated', 'points': [[rotated(p) for p in row] for row in cubic], 'types': [1, 65, 65, 35, 65, 65, 35], 'join': 3},
        {'name': 'line.middle', 'points': line, 'types': [1] * 5, 'join': 2},
        {'name': 'line.to.curve', 'points': mixed_in, 'types': [1, 1, 1, 65, 65, 35], 'join': 2},
        {'name': 'curve.to.line', 'points': mixed_out, 'types': [1, 65, 65, 35, 1], 'join': 3},
        {'name': 'smooth.control', 'points': [line[0], [[p[0] + 20, p[1] + 30] for p in line[0]]], 'types': [1] * 5, 'join': 2},
    ]


def build(font, params):
    if str(font.filepath) != params['expected_path'] or call(font, 'fontName') != 'Dekink Rebuild Regression':
        raise ValueError('Wrong disposable document')
    if call(font, 'countOfGlyphs') != 0 or call(font, 'countOfFontMasters') != 1:
        raise ValueError('Builder requires an empty one-master font')
    first = call(font, 'fontMasters').objectAtIndex_(0)
    if str(call(first, 'id')) != params['expected_initial_master']:
        raise ValueError('Initial master guard mismatch')
    Axis, Master, Glyph, Layer, Path, Node = [objc.lookUpClass(n) for n in ('GSAxis', 'GSFontMaster', 'GSGlyph', 'GSLayer', 'GSPath', 'GSNode')]
    axis = Axis.alloc().initWithName_tag_('Weight', 'wght')
    call(font, 'setAxes_', [axis])
    second = Master.alloc().init()
    call(font, 'addFontMaster_', second)
    masters = [first, second]
    for master, name, value in zip(masters, ['Light', 'Bold'], [100, 900]):
        call(master, 'setName_', name)
        call(master, 'setAxisInternalValueValue_forId_', value, call(axis, 'axisId'))
    cases = definitions()
    for case in cases:
        glyph = Glyph.alloc().initWithName_(case['name'])
        call(font, 'addGlyph_', glyph)
        for master, positions in zip(masters, case['points']):
            layer = Layer.alloc().init()
            mid = call(master, 'id')
            call(layer, 'setLayerId_', mid)
            call(layer, 'setAssociatedMasterId_', mid)
            call(layer, 'setWidth_', 700)
            call(glyph, 'setLayer_forId_', layer, mid)
            old = bool(call(layer, 'temporarilyDisableRounding'))
            call(layer, 'setTemporarilyDisableRounding_', True)
            try:
                path = Path.alloc().init()
                call(path, 'setClosed_', True)
                for i, (p, kind) in enumerate(zip(positions, case['types'])):
                    node = Node.alloc().initWithPosition_type_connection_(NSPoint(*p), kind, 100 if i == case['join'] else 0)
                    call(path, 'addNode_', node)
                call(layer, 'addShape_', path)
            finally:
                call(layer, 'setTemporarilyDisableRounding_', old)
    instance = call(font, 'instances').objectAtIndex_(0)
    call(instance, 'setAxisInternalValueValue_forId_', 500, call(axis, 'axisId'))
    call(font, 'setUserData_forKey_', 'dekink-native-rebuild-v1', 'dekink.rebuild.fixture')
    return {'cases': cases, 'masters': [str(call(m, 'id')) for m in masters], 'glyph_count': len(cases)}


if __name__ == '__main__':
    print(json.dumps(build(font, params), indent=2))
