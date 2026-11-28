# CI diagnostic: control panel, which wires fall back to the loose pass, which pairs still overlap.
import sys, json, os, hashlib
src = open('C:/demo_control_panel.py', encoding='utf-8').read()
src = src.replace("OUT = 'C:/seed/demo72cp'", "OUT = 'C:/seed/cpwire'")
ns = {'__name__': 'diag'}
exec(compile(src, 'demo_control_panel', 'exec'), ns)
out = {'done': False}
try:
    from DeltaEngineering import wire_route as R
    f = R.__file__
    out['module_file'] = f
    out['module_sha256'] = hashlib.sha256(open(f, 'rb').read()).hexdigest()
    d = ns['d']
    rows = R.reroute(d)
    out['rows'] = [{k: r.get(k) for k in ('wire', 'points', 'routed', 'reason', 'segments_in_foreign_box', 'ms', 'strict')} for r in rows]
    out['paths'] = {r['wire']: r.get('path') for r in rows}
    try:
        from DeltaEngineering import core as _core
        tp = {}
        for o in d.Objects:
            if hasattr(o, 'SourceDevice') and hasattr(o, 'WireId'):
                a = _core.terminal_position(o.SourceDevice, o.SourceTerminal)
                b = _core.terminal_position(o.TargetDevice, o.TargetTerminal)
                tp[o.WireId] = {'from': '%s.%s' % (o.SourceDevice.Tag, o.SourceTerminal), 'a': [round(a.x, 1), round(a.y, 1)],
                                'to': '%s.%s' % (o.TargetDevice.Tag, o.TargetTerminal), 'b': [round(b.x, 1), round(b.y, 1)]}
        out['wire_terminals'] = tp
    except Exception as e:
        out['wire_terminals_error'] = repr(e)
    out['loose_pass_wires'] = [r['wire'] for r in rows if r.get('strict') is False]
    out['unrouted_wires'] = [r['wire'] for r in rows if not r.get('routed')]
    out['paths_of_loose'] = {r['wire']: r.get('path') for r in rows if r.get('strict') is False}
    try:
        out['overlaps'] = [list(o) for o in R.overlaps(d)]
    except Exception as e:
        out['overlaps_error'] = repr(e)
    try:
        out['clearance_pairs'] = R.clearance_pairs(d)
    except Exception as e:
        out['clearance_pairs_error'] = repr(e)
    out['done'] = True
except Exception:
    import traceback; out['error'] = traceback.format_exc()
os.makedirs('C:/seed/cpwire', exist_ok=True)
json.dump(out, open('C:/seed/cpwire/cpwire.json', 'w'), indent=1, default=str)
print(json.dumps(out, default=str)[:3000])
