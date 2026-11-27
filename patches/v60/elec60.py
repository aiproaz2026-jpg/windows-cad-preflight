import sys, json, os, traceback
import FreeCAD as App
sys.path.insert(0, 'C:/DeltaTest/Mod'); sys.path.insert(0, 'C:/DeltaTest/Mod/DeltaEngineering')
OUT = 'C:/seed/elec60'; os.makedirs(OUT, exist_ok=True)
res = {'done': False, 'bad': [], 'symbols': {}}
try:
    from DeltaEngineering import symbols
    from DeltaEngineering.symbols import create, TEMPLATES
    from DeltaEngineering.domain import add_terminal_wire, netlist
    from DeltaEngineering.electrical import terminal_layout
    from DeltaEngineering import routecheck
    lib = symbols.V60_LIB
    res['lib_count'] = len(lib)
    d = App.newDocument('E60')
    geo = {}
    for i, k in enumerate(lib):
        try:
            o = create(d, k, 'S%d' % i, App.Vector((i % 7) * 200, -(i // 7) * 160, 0))
            d.recompute()
            sh = o.Shape
            ok = (not sh.isNull()) and len(sh.Edges) > 0 and list(o.Terminals) == list(TEMPLATES[k][1])
            pts = []
            for e in sh.Edges:
                pp = e.discretize(24) if e.Curve.__class__.__name__ != 'Line' else [e.Vertexes[0].Point, e.Vertexes[-1].Point]
                pts.append([[round(p.x, 2), round(p.y, 2)] for p in pp])
            geo[k] = {'tag': 'S%d' % i, 'terminals': list(o.Terminals), 'edges': pts, 'label': TEMPLATES[k][0]}
            res['symbols'][k] = {'ok': ok, 'edges': len(sh.Edges), 'terminals': len(o.Terminals)}
            if not ok: res['bad'].append(k)
        except Exception:
            res['bad'].append(k); res['symbols'][k] = {'ok': False, 'error': traceback.format_exc()[-300:]}
    json.dump(geo, open(OUT + '/geometry.json', 'w', encoding='utf-8'), ensure_ascii=False)
    # motor starter wiring with the ABB-style terminal names
    d2 = App.newDocument('E60S')
    Q = create(d2, 'Breaker 3P (illustr.)', 'Q1', App.Vector(0, 0, 0)); K = create(d2, 'Contactor 3P (illustr.)', 'KM1', App.Vector(400, 0, 0))
    F = create(d2, 'Overload relay (illustr.)', 'F1', App.Vector(800, 0, 0)); M = create(d2, 'Motor 3-phase (illustr.)', 'M1', App.Vector(1200, 0, 0))
    n = 0
    for a, sa, b, sb in ((Q, '2', K, '1L1'), (Q, '4', K, '3L2'), (Q, '6', K, '5L3'), (K, '2T1', F, '1L1'), (K, '4T2', F, '3L2'), (K, '6T3', F, '5L3'), (F, '2T1', M, 'U1'), (F, '4T2', M, 'V1'), (F, '6T3', M, 'W1')):
        n += 1; add_terminal_wire(d2, a, sa, b, sb, 'W%d' % n)
    d2.recompute()
    res['starter_netlist'] = len(netlist(d2)); res['starter_route'] = routecheck.check(d2)['count']
    res['done'] = True
except Exception:
    res['error'] = traceback.format_exc()
json.dump(res, open(OUT + '/result.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in res.items() if k != 'symbols'}, ensure_ascii=False))
