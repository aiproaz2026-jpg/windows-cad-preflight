# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""CI check for the v69 IEC-style signalling/measuring symbols. Runs inside FreeCAD on CI
(same pattern as elec60/elec66). Writes C:/seed/elec69/result.json."""
import sys, json, os, traceback
import FreeCAD as App
sys.path.insert(0, 'C:/DeltaTest/Mod'); sys.path.insert(0, 'C:/DeltaTest/Mod/DeltaEngineering')
OUT = 'C:/seed/elec69'; os.makedirs(OUT, exist_ok=True)
res = {'done': False, 'bad': [], 'symbols': {}}
try:
    App.getUserAppDataDir = lambda: OUT + '/'
    from DeltaEngineering import symbols
    from DeltaEngineering.symbols import create, TEMPLATES
    from DeltaEngineering import elec_sig_meter as SM
    from DeltaEngineering import elec_libedit as L
    data = {}
    for k, v in SM.LIB.items():
        data[k] = {'label': v[0], 'terminals': list(v[1]),
                   'prims': [(list(p) if p[0] != 'L' else ['L', [list(q) for q in p[1]]]) for p in v[2]]}
    res['validate_errors'] = L.validate(data)
    res['missing_registration'] = [k for k in SM.LIB if k not in TEMPLATES or k not in symbols.V60_LIB]
    d = App.newDocument('E69')
    geo = {}
    for i, k in enumerate(SM.LIB):
        try:
            o = create(d, k, 'G%d' % i, App.Vector((i % 6) * 200, -(i // 6) * 180, 0))
            d.recompute()
            sh = o.Shape
            ok = (not sh.isNull()) and len(sh.Edges) > 0 and list(o.Terminals) == list(TEMPLATES[k][1])
            pts = []
            for e in sh.Edges:
                pp = e.discretize(24) if e.Curve.__class__.__name__ != 'Line' else [e.Vertexes[0].Point, e.Vertexes[-1].Point]
                pts.append([[round(p.x, 2), round(p.y, 2)] for p in pp])
            geo[k] = {'edges': pts, 'terminals': list(o.Terminals)}
            res['symbols'][k] = {'ok': ok, 'edges': len(sh.Edges), 'terminals': len(o.Terminals)}
            if not ok:
                res['bad'].append(k)
        except Exception:
            res['bad'].append(k); res['symbols'][k] = {'ok': False, 'error': traceback.format_exc()[-300:]}
    json.dump(geo, open(OUT + '/geometry.json', 'w', encoding='utf-8'), ensure_ascii=False)
    res['count'] = len(SM.LIB)
    res['done'] = not res['bad'] and not res['missing_registration'] and not res['validate_errors']
except Exception:
    res['error'] = traceback.format_exc()
json.dump(res, open(OUT + '/result.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False))
