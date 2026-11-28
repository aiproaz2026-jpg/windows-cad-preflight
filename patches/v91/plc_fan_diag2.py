# CI diagnostic 2: which wire_route runs on the PLC sheet, and what it does to A1.
import sys, json, os, hashlib
src = open('C:/gallery_elec7.py', encoding='utf-8').read()
src = src.replace("OUT = 'C:/seed/gallery72'", "OUT = 'C:/seed/plcfan2'")
ns = {'__name__': 'diag'}
exec(compile(src, 'gallery_elec7', 'exec'), ns)
out = {'done': False}
try:
    from DeltaEngineering import wire_route as R
    from DeltaEngineering import core
    f = R.__file__
    out['module_file'] = f
    out['module_sha256'] = hashlib.sha256(open(f, 'rb').read()).hexdigest()
    out['consts'] = {k: getattr(R, k, None) for k in ('FAN', 'FAN_MAX', 'FAN_MIN_TERMS', 'FAN_COUNT_WHOLE_DEVICE', 'FAN_STEP_MIN', 'FAN_STEP_MAX', 'FAN_STEP_FACTOR', 'FAN_DENSE_PITCH', 'LANE', 'STUB', 'SHADOW_MIN', 'STUB_CROSS')}
    out['has_fan_step'] = hasattr(R, '_fan_step')
    d = ns['d']; plc = ns['PLC']
    R.clear_cache() if hasattr(R, 'clear_cache') else None
    rect = [r for o, r in R.boxes(d) if o is plc][0]
    out['rect'] = list(rect)
    pos = {}
    for t in list(plc.Terminals):
        p = core.terminal_position(plc, t); pos[t] = [round(p.x, 2), round(p.y, 2)]
    out['terminal_pos'] = pos
    out['exit_dirs'] = {t: list(R.exit_dir(rect, tuple(pos[t]))) for t in pos}
    out['fan_lengths'] = R.fan_lengths(plc, rect)
    wires = []
    for o in d.Objects:
        if hasattr(o, 'SourceDevice') and (o.SourceDevice is plc or o.TargetDevice is plc):
            pts = [[round(v.Point.x, 1), round(v.Point.y, 1)] for e in o.Shape.Edges for v in e.Vertexes[:1]]
            try:
                last = o.Shape.Edges[-1].Vertexes[-1].Point; pts.append([round(last.x, 1), round(last.y, 1)])
            except Exception:
                pass
            wires.append({'from': '%s.%s' % (o.SourceDevice.Tag, o.SourceTerminal), 'to': '%s.%s' % (o.TargetDevice.Tag, o.TargetTerminal), 'pts': pts})
    out['wires_at_A1'] = wires
    out['done'] = True
except Exception:
    import traceback; out['error'] = traceback.format_exc()
os.makedirs('C:/seed/plcfan2', exist_ok=True)
json.dump(out, open('C:/seed/plcfan2/plcfan2.json', 'w'), indent=1)
print(json.dumps(out)[:2000])
