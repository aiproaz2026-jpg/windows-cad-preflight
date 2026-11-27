import sys, json, os, traceback
import FreeCAD as App
sys.path.insert(0, 'C:/DeltaTest/Mod'); sys.path.insert(0, 'C:/DeltaTest/Mod/DeltaEngineering')
OUT = 'C:/seed/piperefA'; os.makedirs(OUT, exist_ok=True)
res = {'done': False}
try:
    from DeltaEngineering import network as N, pipe_refine as R
    import Part
    doc = App.newDocument('PRA')
    # two pump trains on a suction header and a discharge header; the discharge outlet jogs off the header axis
    NODES = {'S0': (0, 0, 0), 'S1': (2400, 0, 0), 'S2': (4800, 0, 0), 'S3': (7200, 0, 0),
             'P1s': (2400, -1200, 0), 'P1d': (2400, -2200, 0),
             'P2s': (4800, -1200, 0), 'P2d': (4800, -2200, 0),
             'D0': (0, -4000, 0), 'D1': (2400, -4000, 0), 'D2': (4800, -4000, 0), 'D3': (7200, -4000, 0),
             'D4': (9600, -4000, 0), 'OUT': (11400, -5200, 0)}
    EDGES = [('S0', 'S1'), ('S1', 'S2'), ('S2', 'S3'),
             ('S1', 'P1s'), ('S2', 'P2s'),
             ('P1d', 'D1'), ('P2d', 'D2'),
             ('D0', 'D1'), ('D1', 'D2'), ('D2', 'D3'), ('D3', 'D4'), ('D4', 'OUT')]
    nodes = {k: App.Vector(*v) for k, v in NODES.items()}
    nodes, EDGES2, ins = R.route(nodes, EDGES, first={('D4', 'OUT'): 'y'})
    res['inserted'] = sorted(ins.keys())
    res['route_bad'] = R.route_report(nodes, EDGES2)
    NPS, SCH = '4', 'SCH 40'
    r = N.build(doc, nodes, EDGES2, NPS, SCH)
    chk = N.check(doc, r, nodes)
    rows, cnt, tot = N.schedule_rows(r, NPS, SCH)
    fitrows = R.fitting_report(r, NPS)
    res.update({'pipes': len(r['pipes']), 'fittings': cnt, 'total_pipe_mm': tot,
                'max_joint_gap_mm': chk['max_joint_gap_mm'], 'bad': chk['bad'],
                'fitting_rows': len(fitrows), 'fitting_kinds': sorted(set(x['kind'] for x in fitrows)),
                'short_segments': R.tangent_report(r, None)})
    objs = list(r['pipes']) + list(r['fittings'].values())
    Part.export(objs, OUT + '/pump_station_trains_piping.step')
    res['step_bytes'] = os.path.getsize(OUT + '/pump_station_trains_piping.step')
    doc.saveAs(OUT + '/pump_station_trains_piping.FCStd')
    res['fcstd_bytes'] = os.path.getsize(OUT + '/pump_station_trains_piping.FCStd')
    sym = [(2100, -2200, 600, 1000, 'P-101'), (4500, -2200, 600, 1000, 'P-102')]
    info = R.plan_pdf(OUT + '/pump_station_trains_plan_A3.pdf', nodes, EDGES2, r, NPS, SCH, rows, cnt, tot,
                      title='Two-train pump station, dogleg outlet', symbols=sym,
                      note='Pumps drawn as symbols only. Not a hydraulic design.')
    res.update({'pdf_bytes': info['pdf_bytes'], 'segments_labeled': info['segments_labeled'],
                'segments': info['segments'], 'nodes': info['nodes']})
    res['done'] = True
except Exception:
    res['error'] = traceback.format_exc()
json.dump(res, open(OUT + '/result.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False))
