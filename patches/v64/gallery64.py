import sys, json, os, traceback
import FreeCAD as App
sys.path.insert(0, 'C:/DeltaTest/Mod'); sys.path.insert(0, 'C:/DeltaTest/Mod/DeltaEngineering')
OUT = 'C:/seed/gallery64'; os.makedirs(OUT, exist_ok=True)
res = {'done': False}
try:
    from DeltaEngineering import network as N, net_commands as NC, minipdf
    import Part
    doc = App.newDocument('PS')
    NODES = {'S0': (0, 0, 0), 'S1': (3000, 0, 0), 'S2': (6000, 0, 0), 'S3': (9000, 0, 0), 'P1s': (3000, -1800, 0), 'P2s': (6000, -1800, 0),
             'P1d': (3000, -3800, 0), 'P2d': (6000, -3800, 0), 'H0': (0, -5600, 0), 'H1': (3000, -5600, 0), 'H2': (6000, -5600, 0), 'H3': (9000, -5600, 0)}
    EDGES = [('S0', 'S1'), ('S1', 'S2'), ('S2', 'S3'), ('S1', 'P1s'), ('S2', 'P2s'), ('P1d', 'H1'), ('P2d', 'H2'), ('H0', 'H1'), ('H1', 'H2'), ('H2', 'H3')]
    nodes = {k: App.Vector(*v) for k, v in NODES.items()}
    NPS = '4'
    r = N.build(doc, nodes, EDGES, NPS, 'SCH 40')
    chk = N.check(doc, r, nodes)
    rows, cnt, tot = N.schedule_rows(r, NPS, 'SCH 40')
    res.update({'pipes': len(r['pipes']), 'fittings': cnt, 'total_pipe_mm': tot, 'max_joint_gap_mm': chk['max_joint_gap_mm'], 'bad': chk['bad']})
    objs = list(r['pipes']) + list(r['fittings'].values())
    Part.export(objs, OUT + '/pump_station_piping.step'); res['step_bytes'] = os.path.getsize(OUT + '/pump_station_piping.step')
    doc.saveAs(OUT + '/pump_station_piping.FCStd')
    pw, ph = 1190.55, 841.89
    xs = [v.x for v in nodes.values()]; ys = [v.y for v in nodes.values()]
    x0, x1, y0, y1 = min(xs) - 600, max(xs) + 600, min(ys) - 600, max(ys) + 600
    sc = min((pw - 440) / (x1 - x0), (ph - 140) / (y1 - y0)); ox, oy = 40, 80
    X = lambda x: ox + (x - x0) * sc; Y = lambda y: oy + (y - y0) * sc
    pg = minipdf.Page(pw, ph); pg.rect(20, 20, pw - 40, ph - 40, 1.5)
    for s in r['plan']['segments']:
        a = s['start']; b = a + s['dir'] * s['length']
        pg.line([(X(a.x), Y(a.y)), (X(b.x), Y(b.y))], 2.4, (0.1, 0.25, 0.5))
    for n in r['plan']['fittings']:
        pg.line([(X(nodes[n].x) - 4, Y(nodes[n].y) - 4), (X(nodes[n].x) + 4, Y(nodes[n].y) + 4)], 1.5, (0.8, 0.2, 0.1))
        pg.line([(X(nodes[n].x) - 4, Y(nodes[n].y) + 4), (X(nodes[n].x) + 4, Y(nodes[n].y) - 4)], 1.5, (0.8, 0.2, 0.1))
    for k in ('1', '2'):
        a = nodes['P' + k + 's']; b = nodes['P' + k + 'd']
        pg.rect(X(a.x) - 28, Y(b.y), 56, Y(a.y) - Y(b.y), 1.2)
        pg.text(X(a.x) - 24, (Y(a.y) + Y(b.y)) / 2, 'Pump P' + k, 8)
        pg.text(X(a.x) + 32, (Y(a.y) + Y(b.y)) / 2 - 10, '(symbol only)', 6.5)
    pg.text(X(0), Y(0) + 8, 'Suction header (in)', 8); pg.text(X(0), Y(-5600) - 12, 'Discharge header (out)', 8)
    for n, p in nodes.items():
        pg.text(X(p.x) + 6, Y(p.y) + 6, n + (' [' + r['plan']['fittings'][n]['kind'] + ']' if n in r['plan']['fittings'] else ''), 7)
    tx = pw - 400; ty = ph - 60
    pg.text(tx, ty, 'Two-pump station piping, NPS 4, SCH 40 (ILLUSTRATIVE, generic)', 9); ty -= 16
    for row in rows:
        pg.text(tx, ty, '%s  %s  %s  %.1f mm' % row, 8); ty -= 12
    ty -= 8; pg.text(tx, ty, 'Fittings: ' + ', '.join('%s x%d' % kv for kv in cnt.items()), 8); ty -= 12
    pg.text(tx, ty, 'Total straight pipe: %.1f mm' % tot, 8); ty -= 12
    pg.text(tx, ty, 'Pumps are drawn as symbols only. Not a hydraulic design.', 6.5)
    pg.save(OUT + '/pump_station_plan_A3.pdf'); res['pdf_bytes'] = os.path.getsize(OUT + '/pump_station_plan_A3.pdf')
    res['done'] = True
except Exception:
    res['error'] = traceback.format_exc()
json.dump(res, open(OUT + '/result.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False))
