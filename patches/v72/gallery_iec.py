import sys, json, os, traceback
import FreeCAD as App
sys.path.insert(0, 'C:/DeltaTest/Mod'); sys.path.insert(0, 'C:/DeltaTest/Mod/DeltaEngineering')
sys.path.insert(0, 'C:/DeltaTest/Mod/DeltaEngineering/DeltaEngineering')
OUT = 'C:/seed/gallery72'; os.makedirs(OUT, exist_ok=True)
res = {'done': False}
try:
    from DeltaEngineering import iec_style, term_ends, symbols as S, minipdf
    from DeltaEngineering.symbols import create
    from DeltaEngineering.core import terminal_position
    res['iec_added'] = iec_style.install(); res['term_table'] = term_ends.install()
    d = App.newDocument('IE')
    pairs = ['Contact NO (illustr.)', 'Contact NO (IEC-style)', 'Contact NC (illustr.)', 'Contact NC (IEC-style)', 'Pushbutton NO (illustr.)', 'Pushbutton NO (IEC-style)', 'Pushbutton NC (illustr.)', 'Pushbutton NC (IEC-style)']
    pg = minipdf.Page(1190.55, 841.89); pg.rect(20, 20, 1150, 802, 1.5)
    pg.text(40, 800, 'Existing illustrative symbols (left of each pair) vs IEC-style variants (right). IEC-style = drawing conventions, NOT certified IEC 60617.', 10)
    res['edges'] = {}
    for i, k in enumerate(pairs):
        o = create(d, k, 'T%d' % i, App.Vector(0, 0, 0)); o.touch(); d.recompute()
        res['edges'][k] = len(o.Shape.Edges)
        cx = 150 + (i % 2) * 300 + (i // 2) * 0; cy = 700 - (i // 2) * 170
        cx = 200 + (i % 2) * 250 + ((i // 4) * 500); cy = 700 - ((i // 2) % 2) * 300
        for e in o.Shape.Edges:
            pts = e.discretize(20) if e.Curve.__class__.__name__ != 'Line' else [e.Vertexes[0].Point, e.Vertexes[-1].Point]
            pg.line([(cx + p.x * 2.2, cy + p.y * 2.2) for p in pts], 1.0, (0.08, 0.2, 0.35))
        for t in o.Terminals:
            p = terminal_position(o, t); pg.text(cx + p.x * 2.2 + 6, cy + p.y * 2.2, t, 8)
        pg.text(cx - 60, cy - 120, k, 8)
    pg.save(OUT + '/iec_compare_A3.pdf'); res['pdf_bytes'] = os.path.getsize(OUT + '/iec_compare_A3.pdf')
    res['done'] = True
except Exception:
    res['error'] = traceback.format_exc()
json.dump(res, open(OUT + '/result.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False))
