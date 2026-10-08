"""Render the recorded native midpoint outlines; never generates interpolation."""
import html
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def render():
    data = json.loads((ROOT / 'results/previous-font-native-proof.json').read_text())
    if not data['native_output'] or not data['bound_font_unchanged']:
        raise ValueError('Expected native recorded proof')
    panels = []
    for panel, row in enumerate(data['rows']):
        def point(p):
            return (40 + panel * 420 + p[0] * .88, 370 - p[1] * .88)
        def text_point(p):
            return ','.join(f'{v:.4f}' for v in point(p))
        pts, kinds = row['points'], row['types']
        commands, controls = ['M ' + text_point(pts[0])], []
        for p, kind in zip(pts[1:], kinds[1:]):
            if kind == 65:
                controls.append(p)
            elif kind == 35 and len(controls) == 2:
                commands.append('C ' + ' '.join(text_point(q) for q in [*controls, p]))
                controls = []
            elif kind == 1 and not controls:
                commands.append('L ' + text_point(p))
            else:
                raise ValueError('Unsupported proof path')
        if controls:
            raise ValueError('Unfinished proof segment')
        commands.append('Z')
        a, j, b = pts[row['join'] - 1:row['join'] + 2]
        dx, dy = b[0] - a[0], b[1] - a[1]
        error = abs((j[0] - a[0]) * dy - (j[1] - a[1]) * dx) / math.hypot(dx, dy)
        color = '#b33c32' if row['label'] == 'before' else '#19724f'
        label = 'Before' if row['label'] == 'before' else 'After: one native HOI entry'
        panels.append(f'<text x="{40 + panel * 420}" y="48" class="title">{html.escape(label)}</text>')
        panels.append(f'<text x="{40 + panel * 420}" y="75" class="detail">Midpoint deviation: {error:.7f}u</text>')
        panels.append(f'<path d="{" ".join(commands)}" fill="#e2e6eb" stroke="#273340" stroke-width="1.5"/>')
        panels.append(f'<polyline points="{text_point(a)} {text_point(j)} {text_point(b)}" fill="none" stroke="{color}" stroke-width="2"/>')
        panels.append(f'<line x1="{point(a)[0]}" y1="{point(a)[1]}" x2="{point(b)[0]}" y2="{point(b)[1]}" stroke="{color}" stroke-dasharray="4 4"/>')
        for p in (a, j, b):
            x, y = point(p)
            panels.append(f'<circle cx="{x}" cy="{y}" r="3.5" fill="{color}"/>')
    result = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 880 450" role="img" aria-label="Native midpoint outlines before and after kink correction">' + \
        '<rect width="880" height="450" fill="white"/><style>text{font-family:Arial,sans-serif;fill:#273340}.title{font-size:19px;font-weight:600}.detail{font-size:13px}</style>' + \
        ''.join(panels) + '<text x="40" y="420" class="detail">Actual Glyphs native output at 50%. Masters unchanged; interpolated join trajectory changes.</text></svg>'
    output = ROOT / 'results/previous-font-before-after.svg'
    output.write_text(result + '\n')
    print(output)


if __name__ == '__main__':
    render()
