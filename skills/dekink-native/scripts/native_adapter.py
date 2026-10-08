"""Native Glyphs 4 adapter. Execute through MCP; no Save/Close/export.

Load geometry_source through a SHA256-bound parameter. Scope: one axis,
two ordinary master layers, compatible closed line/cubic paths, no components.
Private HOI selectors require runtime qualification on each new host.
"""
import hashlib
import json
import math
import objc


def call(obj, selector, *args):
    return getattr(obj.pyobjc_instanceMethods, selector)(*args)


def items(value):
    return [value.objectAtIndex_(i) for i in range(value.count())]


def plain(value):
    if value is None:
        return None
    if hasattr(value, 'items'):
        return {str(k): plain(v) for k, v in value.items()}
    if hasattr(value, 'objectAtIndex_'):
        return [plain(v) for v in items(value)]
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    if isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError('Unsupported attribute value: ' + type(value).__name__)


def xy(node):
    p = call(node, 'position')
    return (float(p.x), float(p.y))


def paths(layer):
    return items(call(layer, 'paths'))


def nodes(path):
    return items(call(path, 'nodes'))


def clone(font):
    copy = call(font, 'copy')
    call(copy, 'setParent_', None)
    return copy


def snapshot(font):
    glyphs = {}
    for glyph in items(call(font, 'glyphs')):
        layers = {}
        for layer in items(call(glyph, 'layers').allValues()):
            layers[str(call(layer, 'layerId'))] = {
                'width': float(call(layer, 'width')),
                'shape_count': call(layer, 'shapes').count(),
                'paths': [{'closed': bool(call(p, 'closed')),
                           'nodes': [{'xy': xy(n), 'type': int(call(n, 'type')),
                                      'smooth': bool(call(n, 'isSmooth')),
                                      'attributes': plain(call(n, 'attributes'))} for n in nodes(p)]} for p in paths(layer)]}
        glyphs[str(call(glyph, 'name'))] = layers
    return glyphs


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def context(font):
    axes = items(call(font, 'axes'))
    masters = items(call(font, 'fontMasters'))
    if len(axes) != 1 or len(masters) != 2:
        raise ValueError('Adapter supports exactly one axis and two masters')
    axis_id = call(axes[0], 'axisId')
    ordered = sorted(masters, key=lambda m: float(call(m, 'axisInternalValueValueForId_', axis_id)))
    locations = [float(call(m, 'axisInternalValueValueForId_', axis_id)) for m in ordered]
    if not all(math.isfinite(v) for v in locations) or locations[0] == locations[1]:
        raise ValueError('Invalid or identical internal locations')
    return {'axis': str(call(axes[0], 'axisTag')), 'layers': [str(call(m, 'id')) for m in ordered],
            'locations': locations, 'path': str(font.filepath)}


def pair(font, name, ctx):
    glyph = next(g for g in items(call(font, 'glyphs')) if str(call(g, 'name')) == name)
    layers = call(glyph, 'layers')
    return glyph, [layers.objectForKey_(key) for key in ctx['layers']]


def sample(lower, upper, ctx, factor):
    # A fresh span per call avoids stale HOI caches after an attribute edit.
    window = objc.lookUpClass('HOIWindow').alloc().initWithLayer_axisTag_extraHandles_(lower, ctx['axis'], [])
    span = call(window, 'upper')
    if span is None or call(span, 'upperLayer') != upper:
        raise RuntimeError('Native evaluator selected an unexpected span')
    call(span, 'deriveHOIStack')
    lo, hi = float(call(span, 'originLocation')), float(call(span, 'otherLocation'))
    if abs(lo - ctx['locations'][0]) > 1e-6 or abs(hi - ctx['locations'][1]) > 1e-6:
        raise RuntimeError('Native span locations do not match guarded master locations')
    result = call(lower, 'copy')
    call(result, 'setParent_', None)
    call(objc.lookUpClass('HOI').alloc().init(), 'applyHOISpan_toInstanceLayer_atLocation_', span, result, lo + (hi - lo) * factor)
    return result


def joins(layer):
    found, excluded = [], []
    for pi, path in enumerate(paths(layer)):
        ns = nodes(path)
        if not call(path, 'closed'):
            excluded.append({'path': pi, 'reason': 'open_path'})
            continue
        for ni, node in enumerate(ns):
            kind = int(call(node, 'type'))
            if kind == 65:
                continue
            if not call(node, 'isSmooth'):
                excluded.append({'path': pi, 'node': ni, 'reason': 'intentional_corner'})
                continue
            before, after = (ni - 1) % len(ns), (ni + 1) % len(ns)
            incoming = 'curve' if int(call(ns[before], 'type')) == 65 else 'line'
            outgoing = 'curve' if int(call(ns[after], 'type')) == 65 else 'line'
            # Check complete cubic segment topology, including the far on-curve.
            valid = kind == (35 if incoming == 'curve' else 1)
            if incoming == 'curve':
                valid &= int(call(ns[(ni - 2) % len(ns)], 'type')) == 65 and int(call(ns[(ni - 3) % len(ns)], 'type')) in (1, 35)
            if outgoing == 'curve':
                valid &= int(call(ns[(ni + 2) % len(ns)], 'type')) == 65 and int(call(ns[(ni + 3) % len(ns)], 'type')) == 35
            if not valid:
                excluded.append({'path': pi, 'node': ni, 'reason': 'unsupported_segment_topology'})
                continue
            found.append({'path': pi, 'node': ni, 'indices': [before, ni, after], 'join_type': incoming + '-to-' + outgoing})
    return found, excluded


def compatible(glyph, layers):
    if any(l is None for l in layers) or call(glyph, 'layers').count() != 2:
        return 'missing_or_extra_layers'
    if any(call(l, 'shapes').count() != len(paths(l)) for l in layers):
        return 'components_or_other_shapes'
    a, b = paths(layers[0]), paths(layers[1])
    if len(a) != len(b):
        return 'path_count_mismatch'
    for p, q in zip(a, b):
        x, y = nodes(p), nodes(q)
        if call(p, 'closed') != call(q, 'closed') or len(x) != len(y):
            return 'path_topology_mismatch'
        if any((call(n, 'type'), call(n, 'isSmooth')) != (call(m, 'type'), call(m, 'isSmooth')) for n, m in zip(x, y)):
            return 'node_correspondence_mismatch'
    return None


def triple(layer, join):
    ns = nodes(paths(layer)[join['path']])
    return [xy(ns[i]) for i in join['indices']]


def measurements(layers, ctx, found, factors, geo):
    data = {j['id']: [] for j in found}
    for t in factors:
        output = sample(*layers, ctx, t)
        for j in found:
            data[j['id']].append(dict(geo['metric'](triple(output, j)), factor=t))
        if t in (0, 1):
            source = layers[int(t)]
            if any(math.dist(xy(a), xy(b)) > .001 for p, q in zip(paths(source), paths(output)) for a, b in zip(nodes(p), nodes(q))):
                raise RuntimeError('Native endpoint changed')
    return {key: dict(geo['summarize'](values), samples=values) for key, values in data.items()}


def acceptable(before, after, target, tolerance, target_limit=None):
    row = after[target]
    limit = tolerance if target_limit is None else target_limit
    if row['invalid'] or row['peak'] is None or row['peak']['error_u'] > limit:
        return False
    for key, value in after.items():
        old = before[key]
        if not old['invalid'] and value['invalid']:
            return False
        if old['peak'] and value['peak'] and value['peak']['error_u'] > max(tolerance, old['peak']['error_u']) + 1e-6:
            return False
    return True


def set_ip(node, axis, point):
    old = plain(call(node, 'attributeForKey_', 'hoi')) or {}
    old[axis] = {'ip': point}
    call(node, 'setAttribute_forKey_', old, 'hoi')


def execute(font, params):
    source = params['geometry_source']
    if hashlib.sha256(source.encode()).hexdigest() != params['geometry_sha256']:
        raise ValueError('Geometry source hash mismatch')
    geo = {'__name__': 'dekink_geometry'}
    exec(compile(source, 'geometry.py', 'exec'), geo)
    mode = params.get('mode', 'review')
    threshold, tolerance = float(params.get('threshold_u', 1)), float(params.get('tolerance_u', .001))
    count = params.get('sample_intervals', 100)
    if mode not in ('review', 'apply', 'repair') or not all(math.isfinite(v) and v >= 0 for v in (threshold, tolerance)):
        raise ValueError('Invalid mode or threshold/tolerance')
    if type(count) is not int or count < 2 or count > 2000 or count % 2:
        raise ValueError('sample_intervals must be an even integer from 2 to 2000')
    ctx = context(font)
    if ctx['path'] != params['expected_path']:
        raise ValueError('Bound document path mismatch')
    baseline = snapshot(font)
    fingerprint = digest({'context': ctx, 'snapshot': baseline})
    if mode == 'apply' and params.get('expected_fingerprint') != fingerprint:
        raise ValueError('Stale or missing review fingerprint')
    names = sorted(baseline) if params.get('glyphs') is None else params['glyphs']
    if mode == 'repair' and params.get('glyphs') is None:
        raise ValueError('Repair requires an explicit glyph scope')
    if not isinstance(names, list) or not all(isinstance(n, str) for n in names) or len(set(names)) != len(names) or any(n not in baseline for n in names):
        raise ValueError('Unknown or duplicate glyph scope')
    selected = params.get('selected_ids')
    if selected is not None and (not isinstance(selected, list) or not all(isinstance(v, str) for v in selected) or len(set(selected)) != len(selected)):
        raise ValueError('Invalid selected_ids')
    factors = [i / count for i in range(count + 1)]
    working = clone(font)
    report = {'mode': mode, 'fingerprint': fingerprint, 'context': ctx,
              'host': {'version': str(Glyphs.versionString), 'build': int(Glyphs.buildNumber)},
              'threshold_u': threshold, 'tolerance_u': tolerance, 'factors': factors,
              'issues': [], 'excluded': [], 'plans': [], 'measurements': [], 'applied_entries': 0,
              'sampled_only': True, 'proof_layers_added': 0}
    final_checks = []
    recognized = set()
    for name in names:
        glyph, live_layers = pair(font, name, ctx)
        reason = compatible(glyph, live_layers)
        if reason:
            report['excluded'].append({'glyph': name, 'reason': reason})
            continue
        found, excluded = joins(live_layers[0])
        for j in found:
            j['id'] = f"{name}/{j['path']}/{j['node']}"
            recognized.add(j['id'])
        report['excluded'].extend(dict(row, glyph=name) for row in excluded)
        usable = []
        limits = {}
        source_by_join = {}
        for j in found:
            source_metrics = [geo['metric'](triple(l, j)) for l in live_layers]
            if any(m['degenerate'] or m['folded'] for m in source_metrics):
                report['excluded'].append({'glyph': name, 'id': j['id'], 'reason': 'folded_or_degenerate_source', 'source_metrics': source_metrics})
            else:
                usable.append(j)
                source_by_join[j['id']] = source_metrics
                limits[j['id']] = geo['verification_limit'](source_metrics, tolerance)
        if not usable:
            continue
        before = measurements(live_layers, ctx, usable, factors, geo)
        for j in usable:
            original = before[j['id']]
            limit = limits[j['id']]
            source_metrics = source_by_join[j['id']]
            report['measurements'].append({'glyph': name, 'id': j['id'], 'source_metrics': source_metrics,
                                           'verification_limit_u': limit, 'before': original})
            if original['invalid']:
                report['excluded'].append({'glyph': name, 'id': j['id'], 'reason': 'folded_or_degenerate_native_span', 'before': original})
                continue
            if original['peak']['error_u'] <= threshold:
                continue
            issue = dict(j, glyph=name, axis=ctx['axis'], layers=ctx['layers'], before=original,
                         source_metrics=source_metrics, verification_limit_u=limit)
            report['issues'].append(issue)
            if selected is not None and j['id'] not in selected:
                issue['status'] = 'not_selected'
                continue
            _, current = pair(working, name, ctx)
            current_before = measurements(current, ctx, usable, factors, geo)
            if not current_before[j['id']]['invalid'] and current_before[j['id']]['peak']['error_u'] <= min(limit, threshold):
                issue['status'] = 'fixed_by_shared_entry'
                continue
            existing = [plain(call(nodes(paths(l)[j['path']])[i], 'attributeForKey_', 'hoi')) or {} for l in current for i in j['indices']]
            issue['existing_hoi'] = existing
            if any(ctx['axis'] in h for h in existing):
                issue['status'] = 'existing_local_hoi_requires_specialist_review'
                continue
            attempts = []
            for proposal in geo['candidates'](*[triple(l, j) for l in current], tolerance):
                trial = clone(working)
                _, trial_layers = pair(trial, name, ctx)
                entries = []
                converged = True
                for local, target in proposal['targets'].items():
                    index = j['indices'][local]
                    node = nodes(paths(trial_layers[0])[j['path']])[index]
                    # Native float precision can exceed 1e-6u even for a valid
                    # correction. Coordinate calibration remains ten times
                    # tighter than the requested span tolerance, capped at 1e-4u.
                    calibrated = geo['calibrate_midpoint'](
                        target, lambda value: set_ip(node, ctx['axis'], value),
                        lambda: xy(nodes(paths(sample(*trial_layers, ctx, .5))[j['path']])[index]),
                        min(1e-4, tolerance / 10))
                    requested, actual = calibrated['ip'], calibrated['actual']
                    converged = converged and calibrated['converged']
                    entries.append({'glyph': name, 'layer': ctx['layers'][0], 'path': j['path'], 'node': index,
                                    'axis': ctx['axis'], 'ip': requested, 'midpoint_target': target,
                                    'midpoint_actual': actual, 'calibration': calibrated,
                                    'old_hoi': plain(call(nodes(paths(current[0])[j['path']])[index], 'attributeForKey_', 'hoi'))})
                after = measurements(trial_layers, ctx, usable, factors, geo)
                ok = (converged and acceptable(current_before, after, j['id'], tolerance, limit)
                      and after[j['id']]['peak']['error_u'] <= threshold)
                attempts.append({'strategy': proposal['strategy'], 'entry_count': len(entries), 'accepted': ok,
                                 'after': after[j['id']]})
                if ok:
                    working = trial
                    report['plans'].append({'id': j['id'], 'strategy': proposal['strategy'], 'entries': entries,
                                            'movement_u': proposal['movement_u'], 'native_verified': True,
                                            'source_metrics': source_metrics, 'verification_limit_u': limit,
                                            'absolute_tolerance_met': after[j['id']]['peak']['error_u'] <= tolerance,
                                            'after': after[j['id']], 'affected_joins': sorted(after)})
                    issue['status'] = 'verified_proposal'
                    break
            else:
                issue['status'] = 'no_verified_candidate'
            issue['attempts'] = attempts
        _, current = pair(working, name, ctx)
        final = measurements(current, ctx, usable, factors, geo)
        for plan in [p for p in report['plans'] if p['entries'][0]['glyph'] == name]:
            if not acceptable(before, final, plan['id'], tolerance, plan['verification_limit_u']) or final[plan['id']]['peak']['error_u'] > threshold:
                raise RuntimeError('Combined proposals failed verification; live font unchanged')
        final_checks.append((name, usable, before))
    if selected is not None and any(key not in recognized for key in selected):
        raise ValueError('Unknown or unsupported selected join ID')
    if snapshot(font) != baseline:
        raise RuntimeError('Live document changed during planning')
    if mode in ('apply', 'repair'):
        written = []
        try:
            for plan in report['plans']:
                for entry in plan['entries']:
                    _, layers = pair(font, entry['glyph'], ctx)
                    node = nodes(paths(layers[0])[entry['path']])[entry['node']]
                    if plain(call(node, 'attributeForKey_', 'hoi')) != entry['old_hoi']:
                        raise RuntimeError('Target HOI guard changed')
                    written.append((node, entry['old_hoi']))
                    set_ip(node, ctx['axis'], tuple(entry['ip']))
                    stored = plain(call(node, 'attributeForKey_', 'hoi'))
                    if stored[ctx['axis']] != {'ip': list(entry['ip'])}:
                        raise RuntimeError('HOI readback mismatch')
            if snapshot(font) != snapshot(working):
                raise RuntimeError('Unexpected master or attribute change')
            for name, usable, before in final_checks:
                _, layers = pair(font, name, ctx)
                final = measurements(layers, ctx, usable, factors, geo)
                # Additional interleaved samples independently exercise committed output.
                interleaved = measurements(layers, ctx, usable, [(i + .5) / count for i in range(count)], geo)
                for plan in [p for p in report['plans'] if p['entries'][0]['glyph'] == name]:
                    if not acceptable(before, final, plan['id'], tolerance, plan['verification_limit_u']) or final[plan['id']]['peak']['error_u'] > threshold or interleaved[plan['id']]['invalid'] or interleaved[plan['id']]['peak']['error_u'] > min(plan['verification_limit_u'], threshold):
                        raise RuntimeError('Live commit verification failed')
                    plan['committed_peak'] = final[plan['id']]['peak']
                    plan['interleaved_peak'] = interleaved[plan['id']]['peak']
            report['applied_entries'] = len(written)
        except Exception:
            for node, old in reversed(written):
                call(node, 'setAttribute_forKey_', old, 'hoi')
            if snapshot(font) != baseline:
                raise RuntimeError('Rollback did not restore invocation baseline')
            raise
    report['live_unchanged'] = snapshot(font) == baseline
    report['final_fingerprint'] = digest({'context': ctx, 'snapshot': snapshot(font)})
    return report


def compact_report(value):
    """Keep evidence readable within MCP's output limit; retain sample summaries."""
    if isinstance(value, dict):
        return {key: compact_report(item) for key, item in value.items() if key != 'samples'}
    if isinstance(value, list):
        return [compact_report(item) for item in value]
    return value


if __name__ == '__main__':
    result = execute(font, params)
    print(json.dumps(result if params.get('full_report', False) else compact_report(result), indent=2))
