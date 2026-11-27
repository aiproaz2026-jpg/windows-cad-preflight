import sys, json, os, traceback
import FreeCAD as App
sys.path.insert(0, 'C:/DeltaTest/Mod'); sys.path.insert(0, 'C:/DeltaTest/Mod/DeltaEngineering')
OUT = 'C:/seed/net68'; os.makedirs(OUT, exist_ok=True)
res = {'done': False}
try:
    from DeltaEngineering import network as N, net_commands as NC, net_export as X
    doc = App.newDocument('NX')
    nodes = {k: App.Vector(*v) for k, v in NC.DEMO_NODES.items()}
    r = N.build(doc, nodes, NC.DEMO_EDGES, '4', 'SCH 40')
    res['remembered'] = bool(X.LAST) if getattr(N, '_remember_patched', False) else 'register not run'
    if not X.LAST:
        X.remember(nodes, NC.DEMO_EDGES, r, '4', 'SCH 40')
    out = X.export_last(OUT + '/demo')
    res['files'] = [os.path.basename(out[0]), os.path.basename(out[1])]; res['pdf_bytes'] = out[2]; res['csv_bytes'] = out[3]
    txt = open(out[1], encoding='utf-8-sig').read().splitlines()
    res['csv_head'] = txt[:3]; res['csv_lines'] = len(txt)
    res['done'] = True
except Exception:
    res['error'] = traceback.format_exc()
json.dump(res, open(OUT + '/result.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False))
