import sys, json, os, traceback
import FreeCAD as App
sys.path.insert(0, 'C:/DeltaTest/Mod'); sys.path.insert(0, 'C:/DeltaTest/Mod/DeltaEngineering')
sys.path.insert(0, 'C:/DeltaTest/Mod/DeltaEngineering/DeltaEngineering')
OUT = 'C:/seed/elec_iec4'; os.makedirs(OUT, exist_ok=True)
res = {'done': False, 'bad': [], 'symbols': {}}
try:
    from DeltaEngineering import symbols
    from DeltaEngineering.symbols import create, TEMPLATES
    from DeltaEngineering.domain import add_terminal_wire, netlist
    from DeltaEngineering import routecheck
    from DeltaEngineering import elec_lib_iec4
    lib = symbols.V60_LIB
    iec_keys = list(elec_lib_iec4.LIB_IEC)
    res['iec_count'] = len(iec_keys)
    res['registered'] = [k for k in iec_keys if k in lib and k in TEMPLATES]
    res['missing'] = [k for k in iec_keys if k not in lib or k not in TEMPLATES]
    d = App.newDocument('IEC')
    geo = {}
    for i, k in enumerate(iec_keys):
        try:
            o = create(d, k, 'Q%d' % i, App.Vector((i % 5) * 200, -(i // 5) * 160, 0))
            d.recompute()
            sh = o.Shape
            ok = (not sh.isNull()) and len(sh.Edges) > 0 and list(o.Terminals) == list(TEMPLATES[k][1])
            pts = []
            for e in sh.Edges:
                pp = e.discretize(24) if e.Curve.__class__.__name__ != 'Line' else [e.Vertexes[0].Point, e.Vertexes[-1].Point]
                pts.append([[round(p.x, 2), round(p.y, 2)] for p in pp])
            geo[k] = {'tag': 'Q%d' % i, 'terminals': list(o.Terminals), 'edges': pts, 'label': TEMPLATES[k][0]}
            res['symbols'][k] = {'ok': ok, 'edges': len(sh.Edges), 'terminals': len(o.Terminals)}
            if not ok: res['bad'].append(k)
        except Exception:
            res['bad'].append(k); res['symbols'][k] = {'ok': False, 'error': traceback.format_exc()[-300:]}
    json.dump(geo, open(OUT + '/geometry.json', 'w', encoding='utf-8'), ensure_ascii=False)
    # three-phase starter wired with the IEC-style symbols and the ABB-style terminal names
    d2 = App.newDocument('IECSTART')
    Q = create(d2, 'Breaker 3P (IEC)', 'Q1', App.Vector(0, 0, 0))
    K = create(d2, 'Contactor 3P (IEC)', 'KM1', App.Vector(400, 0, 0))
    n = 0
    for a, sa, b, sb in ((Q, '2', K, '1L1'), (Q, '4', K, '3L2'), (Q, '6', K, '5L3')):
        n += 1; add_terminal_wire(d2, a, sa, b, sb, 'W%d' % n)
    # single-phase control loop wired with the two-terminal IEC symbols
    F = create(d2, 'Fuse (IEC)', 'F1', App.Vector(0, -200, 0))
    S = create(d2, 'Switch NO (IEC)', 'S1', App.Vector(200, -200, 0))
    B = create(d2, 'Breaker 1P (IEC)', 'Q2', App.Vector(400, -200, 0))
    C = create(d2, 'Contactor NO contact (IEC)', 'KM1:13', App.Vector(600, -200, 0))
    for a, sa, b, sb in ((F, '2', S, '1'), (S, '2', B, '1'), (B, '2', C, '13')):
        n += 1; add_terminal_wire(d2, a, sa, b, sb, 'W%d' % n)
    d2.recompute()
    res['iec_netlist'] = len(netlist(d2)); res['iec_route'] = routecheck.check(d2)['count']
    res['done'] = True
except Exception:
    res['error'] = traceback.format_exc()
json.dump(res, open(OUT + '/result.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in res.items() if k != 'symbols'}, ensure_ascii=False))
