import sys, json, os, traceback
import FreeCAD as App
sys.path.insert(0, 'C:/DeltaTest/Mod'); sys.path.insert(0, 'C:/DeltaTest/Mod/DeltaEngineering')
OUT = 'C:/seed/net63'; os.makedirs(OUT, exist_ok=True)
res = {'done': False}
try:
    from DeltaEngineering import network as N, net_commands as NC, minipdf
    import Part
    doc = App.newDocument('NET')
    nodes = {k: App.Vector(*v) for k, v in NC.DEMO_NODES.items()}
    r = N.build(doc, nodes, NC.DEMO_EDGES, '4', 'SCH 40')
    chk = N.check(doc, r, nodes)
    rows, cnt, tot = N.schedule_rows(r, '4', 'SCH 40')
    res.update({'pipes': len(r['pipes']), 'fittings': cnt, 'total_pipe_mm': tot, 'max_joint_gap_mm': chk['max_joint_gap_mm'], 'bad': chk['bad']})
    # text-parse round trip and an error case
    n2, e2 = NC.parse('A 0 0 0\nB 1000 0 0\nC 1000 1000 0\nA-B\nB-C')
    d2 = App.newDocument('NET2'); r2 = N.build(d2, n2, e2, '2', 'SCH 40'); res['text_net'] = [len(r2['pipes']), list(r2['fittings'])]
    try:
        N.plan({'A': App.Vector(0, 0, 0), 'B': App.Vector(1000, 0, 0), 'C': App.Vector(1500, 866, 0)}, [('A', 'B'), ('B', 'C')], '4'); res['bad_bend_rejected'] = False
    except ValueError:
        res['bad_bend_rejected'] = True
    # edit test: change one pipe length, volume changes
    v0 = r['pipes'][0].Shape.Volume; r['pipes'][0].Length = r['pipes'][0].Length.Value + 100; doc.recompute()
    res['edit_changes_volume'] = r['pipes'][0].Shape.Volume > v0 * 1.04
    # STEP export of the whole network
    objs = list(r['pipes']) + list(r['fittings'].values())
    Part.export(objs, OUT + '/network.step'); res['step_bytes'] = os.path.getsize(OUT + '/network.step')
    doc.saveAs(OUT + '/net.FCStd')
    # plan PDF with schedule
    pw, ph = 1190.55, 841.89
    xs = [v.x for v in nodes.values()]; ys = [v.y for v in nodes.values()]
    x0, x1, y0, y1 = min(xs) - 500, max(xs) + 500, min(ys) - 500, max(ys) + 500
    sc = min((pw - 440) / (x1 - x0), (ph - 140) / (y1 - y0)); ox, oy = 40, 80
    X = lambda x: ox + (x - x0) * sc; Y = lambda y: oy + (y - y0) * sc
    pg = minipdf.Page(pw, ph); pg.rect(20, 20, pw - 40, ph - 40, 1.5)
    for s in r['plan']['segments']:
        a = s['start']; b = a + s['dir'] * s['length']
        pg.line([(X(a.x), Y(a.y)), (X(b.x), Y(b.y))], 2.2, (0.1, 0.25, 0.5))
    for n, f in r['plan']['fittings'].items():
        pg.line([(X(nodes[n].x) - 4, Y(nodes[n].y) - 4), (X(nodes[n].x) + 4, Y(nodes[n].y) + 4)], 1.5, (0.8, 0.2, 0.1))
        pg.line([(X(nodes[n].x) - 4, Y(nodes[n].y) + 4), (X(nodes[n].x) + 4, Y(nodes[n].y) - 4)], 1.5, (0.8, 0.2, 0.1))
    import math as _m
    def _lblpos(n, edges_):
        dirs = []
        for a_, b_ in edges_:
            if n in (a_, b_):
                o_ = b_ if a_ == n else a_
                dx_ = nodes[o_].x - nodes[n].x; dy_ = nodes[o_].y - nodes[n].y
                dirs.append(_m.atan2(dy_, dx_))
        best_ = (6, 6); bs_ = -1
        for ox_, oy_ in ((6, 6), (-62, 6), (6, -12), (-62, -12), (6, 0), (-62, 0)):
            ang_ = _m.atan2(oy_ + 4, ox_ + 12 if ox_ > 0 else -20)
            s_ = min([abs(_m.atan2(_m.sin(ang_ - d_), _m.cos(ang_ - d_))) for d_ in dirs] or [3.0])
            if s_ > bs_ + 1e-9:
                bs_, best_ = s_, (ox_, oy_)
        return best_
    for n, p in nodes.items():
        _o = _lblpos(n, NC.DEMO_EDGES)
        pg.text(X(p.x) + _o[0], Y(p.y) + _o[1], n + (' [' + r['plan']['fittings'][n]['kind'] + ']' if n in r['plan']['fittings'] else ''), 8)
    tx = pw - 400; ty = ph - 60
    pg.text(tx, ty, 'Pipe schedule, NPS 4, SCH 40 (ILLUSTRATIVE, generic)', 9); ty -= 16
    for row in rows:
        pg.text(tx, ty, '%s  %s  %s  %.1f mm' % row, 8); ty -= 12
    ty -= 8; pg.text(tx, ty, 'Fittings: ' + ', '.join('%s x%d' % kv for kv in cnt.items()), 8); ty -= 12
    pg.text(tx, ty, 'Total straight pipe: %.1f mm' % tot, 8); ty -= 12
    pg.text(tx, ty, 'Max joint gap on solids: %.3f mm' % chk['max_joint_gap_mm'], 8); ty -= 12
    pg.text(tx, ty, 'Fitting dims: ASME B16.9 tables as published, see fittings_library.', 6.5)
    pg.save(OUT + '/network_plan_A3.pdf'); res['pdf_bytes'] = os.path.getsize(OUT + '/network_plan_A3.pdf')
    res['done'] = True
except Exception:
    res['error'] = traceback.format_exc()
json.dump(res, open(OUT + '/result.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False))
