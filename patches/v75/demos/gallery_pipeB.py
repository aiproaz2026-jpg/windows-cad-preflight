import sys, json, os, traceback
import FreeCAD as App
sys.path.insert(0, 'C:/DeltaTest/Mod'); sys.path.insert(0, 'C:/DeltaTest/Mod/DeltaEngineering')
OUT = 'C:/seed/piperefB'; os.makedirs(OUT, exist_ok=True)
res = {'done': False}
try:
    from DeltaEngineering import network as N, pipe_refine as R
    import Part
    doc = App.newDocument('PRB')
    # manifold header: a tee take-off, then a 45 degree offset up and a 45 degree offset back down to the same axis
    NODES = {'A': (0, 0, 0), 'T': (1200, 0, 0), 'B': (2400, 0, 0), 'C': (3300, 900, 0), 'D': (4500, 900, 0),
             'E': (6000, 900, 0), 'F': (6900, 0, 0), 'G': (8400, 0, 0), 'T1': (1200, -1500, 0)}
    EDGES = [('A', 'T'), ('T', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'E'), ('E', 'F'), ('F', 'G'), ('T', 'T1')]
    nodes = {k: App.Vector(*v) for k, v in NODES.items()}
    # route() must leave an axis-aligned graph alone; run it on the straight legs only
    _n2, _e2, _ins = R.route(nodes, [('A', 'T'), ('T', 'B'), ('T', 'T1'), ('D', 'E'), ('F', 'G')])
    res['route_noop'] = (len(_ins) == 0)
    NPS, SCH = '4', 'SCH 40'
    r = N.build(doc, nodes, EDGES, NPS, SCH)
    chk = N.check(doc, r, nodes)
    rows, cnt, tot = N.schedule_rows(r, NPS, SCH)
    fitrows = R.fitting_report(r, NPS)
    res.update({'pipes': len(r['pipes']), 'fittings': cnt, 'total_pipe_mm': tot,
                'max_joint_gap_mm': chk['max_joint_gap_mm'], 'bad': chk['bad'],
                'fitting_rows': len(fitrows), 'fitting_kinds': sorted(set(x['kind'] for x in fitrows)),
                'short_segments': R.tangent_report(r, None)})
    objs = list(r['pipes']) + list(r['fittings'].values())
    Part.export(objs, OUT + '/manifold_offset_piping.step')
    res['step_bytes'] = os.path.getsize(OUT + '/manifold_offset_piping.step')
    doc.saveAs(OUT + '/manifold_offset_piping.FCStd')
    res['fcstd_bytes'] = os.path.getsize(OUT + '/manifold_offset_piping.FCStd')
    info = R.plan_pdf(OUT + '/manifold_offset_plan_A3.pdf', nodes, EDGES, r, NPS, SCH, rows, cnt, tot,
                      title='Manifold header with 45 degree offsets',
                      note='45 degree offsets use two 45 elbows, as the fitting tables allow.')
    res.update({'pdf_bytes': info['pdf_bytes'], 'segments_labeled': info['segments_labeled'],
                'segments': info['segments'], 'nodes': info['nodes']})
    res['done'] = True
except Exception:
    res['error'] = traceback.format_exc()
json.dump(res, open(OUT + '/result.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False))
