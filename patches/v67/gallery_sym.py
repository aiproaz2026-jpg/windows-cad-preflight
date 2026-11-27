import sys, json, os, traceback
import FreeCAD as App
sys.path.insert(0, 'C:/DeltaTest/Mod'); sys.path.insert(0, 'C:/DeltaTest/Mod/DeltaEngineering')
sys.path.insert(0, 'C:/DeltaTest/Mod/DeltaEngineering/DeltaEngineering')
OUT = 'C:/seed/gallery67'; os.makedirs(OUT, exist_ok=True)
res = {'done': False}
try:
    from DeltaEngineering import term_ends, symbols as S, minipdf
    from DeltaEngineering.symbols import create
    from DeltaEngineering.core import terminal_position
    res['table'] = term_ends.install()
    d = App.newDocument('SY')
    kinds = list(S.V60_LIB.keys())
    pg = minipdf.Page(1190.55, 841.89); pg.rect(20, 20, 1150, 802, 1.5)
    pg.text(40, 800, 'Electrical symbol library (ILLUSTRATIVE, original shapes): terminal dots at lead ends for two-terminal symbols', 10)
    cols = 6; sc = 0.9; moved = 0; checked = []
    for i, k in enumerate(kinds):
        o = create(d, k, 'T%d' % i, App.Vector(0, 0, 0)); d.recompute()
        cx = 120 + (i % cols) * 190; cy = 740 - (i // cols) * 105
        for e in o.Shape.Edges:
            pts = e.discretize(20) if e.Curve.__class__.__name__ != 'Line' else [e.Vertexes[0].Point, e.Vertexes[-1].Point]
            pg.line([(cx + p.x * sc, cy + p.y * sc) for p in pts], 0.8, (0.08, 0.2, 0.35))
        for t in o.Terminals:
            p = terminal_position(o, t); pg.text(cx + p.x * sc + 3, cy + p.y * sc + 3, t, 5)
        if k in term_ends._TABLE:
            moved += 1; checked.append([k, [list(map(float, tuple(terminal_position(o, t)))) for t in o.Terminals]])
        pg.text(cx - 40, cy - 40, k.replace(' (illustr.)', ''), 6.5)
    res['two_terminal_at_leads'] = moved; res['sample'] = checked[:4]; res['symbols'] = len(kinds)
    pg.save(OUT + '/symbols_grid_A3.pdf'); res['pdf_bytes'] = os.path.getsize(OUT + '/symbols_grid_A3.pdf')
    res['done'] = True
except Exception:
    res['error'] = traceback.format_exc()
json.dump(res, open(OUT + '/result.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False))
