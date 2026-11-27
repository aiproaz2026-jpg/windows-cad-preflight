# -*- coding: utf-8 -*-
"""CI check for wire_route: build a DOL starter and a reversing starter, measure the stock
wiring, install the router, measure again, and write one A3 sheet per demo.
Headless FreeCAD, CI only. Not a design and not checked for rating or safety. GPL-3.0-or-later."""
import sys, json, os, math, traceback
import FreeCAD as App
sys.path.insert(0, 'C:/DeltaTest/Mod'); sys.path.insert(0, 'C:/DeltaTest/Mod/DeltaEngineering')
sys.path.insert(0, 'C:/DeltaTest/Mod/DeltaEngineering/DeltaEngineering')
OUT = 'C:/seed/route84'; os.makedirs(OUT, exist_ok=True)
res = {'done': False}
try:
    from DeltaEngineering.symbols import create
    from DeltaEngineering.domain import add_terminal_wire, netlist
    from DeltaEngineering.core import terminal_position
    from DeltaEngineering import minipdf
    from DeltaEngineering import wire_route as R
    try:
        from DeltaEngineering import term_ends2 as TE
        res['term_table'] = TE.install()
    except Exception:
        res['term_table'] = 'term_ends2 not present'

    def wire(d, a, sa, b, sb, n):
        return add_terminal_wire(d, a, sa, b, sb, 'W%d' % n)

    def dol():
        d = App.newDocument('DOL')
        V = App.Vector
        T = [create(d, 'Terminal (illustr.)', 'L%d' % (i + 1), V(3800 + 200 * i, 900, 0)) for i in range(3)]
        Q = create(d, 'Breaker 3P (illustr.)', 'Q1', V(4000, 600, 0))
        K = create(d, 'Contactor 3P (illustr.)', 'K1', V(4000, 200, 0))
        F = create(d, 'Overload relay (illustr.)', 'F1', V(4000, -200, 0))
        M = create(d, 'Motor 3-phase (illustr.)', 'M1', V(4000, -700, 0))
        Lc = create(d, 'Terminal (illustr.)', 'L1c', V(3300, -1200, 0))
        F2 = create(d, 'Fuse (illustr.)', 'F2', V(3650, -1200, 0))
        S1 = create(d, 'Pushbutton NC (illustr.)', 'S1', V(4000, -1200, 0))
        S2 = create(d, 'Pushbutton NO (illustr.)', 'S2', V(4000, -1500, 0))
        KC = create(d, 'Contactor coil (illustr.)', 'K1-coil', V(4400, -1200, 0))
        Nc = create(d, 'Terminal (illustr.)', 'Nc', V(4750, -1200, 0))
        n = 0
        for i, pin in enumerate(('1', '3', '5')):
            n += 1; wire(d, T[i], '1', Q, pin, n)
        for src, dst in (('2', '1L1'), ('4', '3L2'), ('6', '5L3')):
            n += 1; wire(d, Q, src, K, dst, n)
        for src, dst in (('2T1', '1L1'), ('4T2', '3L2'), ('6T3', '5L3')):
            n += 1; wire(d, K, src, F, dst, n)
        for src, dst in (('2T1', 'U1'), ('4T2', 'V1'), ('6T3', 'W1')):
            n += 1; wire(d, F, src, M, dst, n)
        n += 1; wire(d, Lc, '1', F2, '1', n)
        n += 1; wire(d, F2, '2', S1, '21', n)
        n += 1; wire(d, S1, '22', S2, '13', n)
        n += 1; wire(d, S2, '14', KC, 'A1', n)
        n += 1; wire(d, S1, '22', KC, 'A1', n)
        n += 1; wire(d, KC, 'A2', Nc, '1', n)
        return d, n

    def reversing():
        d = App.newDocument('REV')
        V = App.Vector
        Q = create(d, 'Breaker 3P (illustr.)', 'Q1', V(4000, 700, 0))
        K1 = create(d, 'Contactor 3P (illustr.)', 'K1F', V(3800, 300, 0))
        K2 = create(d, 'Contactor 3P (illustr.)', 'K1R', V(4200, 300, 0))
        F = create(d, 'Overload relay (illustr.)', 'F1', V(3800, -150, 0))
        M = create(d, 'Motor 3-phase (illustr.)', 'M1', V(3800, -650, 0))
        Lc = create(d, 'Terminal (illustr.)', 'L1c', V(3300, -1100, 0))
        F2 = create(d, 'Fuse (illustr.)', 'F2', V(3650, -1100, 0))
        S1 = create(d, 'Pushbutton NC (illustr.)', 'S1', V(4000, -1100, 0))
        S2 = create(d, 'Pushbutton NO (illustr.)', 'S2F', V(4350, -1100, 0))
        S3 = create(d, 'Pushbutton NO (illustr.)', 'S2R', V(4700, -1100, 0))
        C1 = create(d, 'Contactor coil (illustr.)', 'K1F-coil', V(4350, -1450, 0))
        C2 = create(d, 'Contactor coil (illustr.)', 'K1R-coil', V(4700, -1450, 0))
        Nc = create(d, 'Terminal (illustr.)', 'Nc', V(5050, -1450, 0))
        n = 0
        for pin in ('2', '4', '6'):
            for k in (K1, K2):
                n += 1; wire(d, Q, pin, k, {'2': '1L1', '4': '3L2', '6': '5L3'}[pin], n)
        for src, dst in (('2T1', '1L1'), ('4T2', '3L2'), ('6T3', '5L3')):
            for k in (K1, K2):
                n += 1; wire(d, k, src, F, dst, n)
        for src, dst in (('2T1', 'U1'), ('4T2', 'V1'), ('6T3', 'W1')):
            n += 1; wire(d, F, src, M, dst, n)
        n += 1; wire(d, Lc, '1', F2, '1', n)
        n += 1; wire(d, F2, '2', S1, '21', n)
        n += 1; wire(d, S1, '22', S2, '13', n)
        n += 1; wire(d, S1, '22', S3, '13', n)
        n += 1; wire(d, S2, '14', C1, 'A1', n)
        n += 1; wire(d, S3, '14', C2, 'A1', n)
        n += 1; wire(d, C1, 'A2', Nc, '1', n)
        n += 1; wire(d, C2, 'A2', Nc, '1', n)
        return d, n

    def gap(seg, r):
        (x1, y1), (x2, y2) = seg
        ax0, ax1 = min(x1, x2), max(x1, x2)
        ay0, ay1 = min(y1, y2), max(y1, y2)
        dx = max(r[0] - ax1, ax0 - r[2], 0.0)
        dy = max(r[1] - ay1, ay0 - r[3], 0.0)
        return math.hypot(dx, dy)

    def min_clearance(d):
        found = R.boxes(d)
        rects = [r for _o, r in found]
        index = {id(o): i for i, (o, _r) in enumerate(found)}
        worst = None
        for o in d.Objects:
            if not hasattr(o, 'SourceTerminal') or o.Shape.isNull():
                continue
            own = set()
            for name in ('SourceDevice', 'TargetDevice'):
                dev = getattr(o, name, None)
                if dev is not None and id(dev) in index:
                    own.add(index[id(dev)])
            for seg in R.segments(o.Shape):
                for i, r in enumerate(rects):
                    if i in own:
                        continue
                    g = gap(seg, r)
                    worst = g if worst is None else min(worst, g)
        return None if worst is None else round(worst, 2)

    def label_hits(d):
        labs = R.text_boxes(d)
        n = 0
        for o in d.Objects:
            if not hasattr(o, 'SourceTerminal') or o.Shape.isNull():
                continue
            sg = R.segments(o.Shape)
            if not sg:
                continue
            a, b = sg[0][0], sg[-1][1]
            for seg in sg:
                for r in labs:
                    if R._near_box(a, r, 2 * R.STUB) or R._near_box(b, r, 2 * R.STUB):
                        continue
                    if R._hits_rect(seg[0], seg[1], r):
                        n += 1
                        break
        return n

    def wire_paths(d):
        out = {}
        for o in d.Objects:
            if not hasattr(o, 'SourceTerminal') or o.Shape.isNull():
                continue
            sg = R.segments(o.Shape)
            if not sg:
                continue
            pts = [[round(sg[0][0][0], 1), round(sg[0][0][1], 1)]]
            pts += [[round(s[1][0], 1), round(s[1][1], 1)] for s in sg]
            out[o.WireId] = pts
        return out

    def measure(d):
        hits = R.overlaps(d)
        junction = [h for h in hits if h[3]]
        return {'overlaps': len(hits) - len(junction), 'junction_overlaps': len(junction),
                'overlap_mm': round(sum(h[2] for h in hits if not h[3]), 1),
                'junction_mm': round(sum(h[2] for h in junction), 1),
                'crossings': len(R.crossings(d)),
                'min_clearance_mm': min_clearance(d),
                'overlap_detail': [h for h in hits if not h[3]],
                'crossing_detail': R.crossings(d),
                'boxes': len(R.boxes(d)),
                'label_boxes': len(R.text_boxes(d)),
                'segments_through_labels': label_hits(d),
                'wires': len([o for o in d.Objects if hasattr(o, 'SourceTerminal')])}

    def sheet(d, path, title):
        segs = []; texts = []; xs = []; ys = []
        def add(shape, w, rgb):
            for e in shape.Edges:
                if e.Curve.__class__.__name__ != 'Line':
                    pp = [e.valueAt(e.FirstParameter + (e.LastParameter - e.FirstParameter) * j / 20.0) for j in range(21)]
                else:
                    pp = [e.Vertexes[0].Point, e.Vertexes[-1].Point]
                segs.append(([(p.x, p.y) for p in pp], w, rgb))
                for p in pp:
                    xs.append(p.x); ys.append(p.y)
        for o in d.Objects:
            if hasattr(o, 'DeviceType') and not o.Shape.isNull():
                add(o.Shape, 0.9, (0.08, 0.2, 0.35))
                texts.append((o.Position.x - 30, o.Position.y + 50, o.Tag))
                for t in o.Terminals:
                    p = terminal_position(o, t); texts.append((p.x + 4, p.y + 3, t, 5))
        for o in d.Objects:
            if hasattr(o, 'SourceTerminal') and not o.Shape.isNull():
                add(o.Shape, 1.1, (0.75, 0.22, 0.17))
        pw, ph = 1190.55, 841.89
        x0, x1, y0, y1 = min(xs) - 60, max(xs) + 60, min(ys) - 80, max(ys) + 120
        mx, top, bot = 40, 70, 90
        sc = min((pw - 2 * mx) / (x1 - x0), (ph - top - bot) / (y1 - y0))
        X = lambda x: mx + (x - x0) * sc
        Y = lambda y: bot + (y - y0) * sc
        pg = minipdf.Page(pw, ph)
        pg.rect(20, 20, pw - 40, ph - 40, 1.5)
        for pts, w, rgb in segs:
            pg.line([(X(a), Y(b)) for a, b in pts], w, rgb)
        for t in texts:
            pg.text(X(t[0]), Y(t[1]), t[2], t[3] if len(t) > 3 else 8)
        pg.rect(pw - 470, 20, 450, 62, 1.0)
        pg.text(pw - 460, 62, title, 9)
        pg.text(pw - 460, 48, 'Wires routed by wire_route: orthogonal, out of every symbol box, parallel runs separated.', 6.5)
        pg.text(pw - 460, 36, 'Generated by the CAD program in CI. Not a design, not checked for rating or safety.', 6.5)
        pg.save(path)
        return os.path.getsize(path)

    out = {}
    for name, builder, title in (('dol', dol, 'DOL starter, 3-phase (ILLUSTRATIVE)'),
                                 ('reversing', reversing, 'Reversing starter, 3-phase (ILLUSTRATIVE)')):
        R.uninstall()
        _orig_plan = R.plan
        _orig_apply = R.apply
        R.apply = lambda obj: False      # call site disabled: stock drawing
        d0, n = builder()
        d0.recompute()
        if not R.boxes(d0):
            d0.recompute()
        before = measure(d0)
        before_paths = wire_paths(d0)
        R.plan = _orig_plan                       # call site live (core.py patched by CI step)
        calls = {'n': 0}
        def _counting(obj, _o=_orig_apply):
            calls['n'] += 1
            return _o(obj)
        R.apply = _counting
        d, n = builder()
        d.recompute()
        if not R.boxes(d):
            d.recompute()
        R.apply = _orig_apply
        diag = {}
        ws = [o for o in d.Objects if hasattr(o, 'SourceTerminal')]
        diag['after_first_recompute'] = [[o.WireId, bool(o.Shape.isNull()), round(o.Shape.Length, 1) if not o.Shape.isNull() else None, str(o.Validation)] for o in ws]
        hooked = measure(d)
        hooked_paths = wire_paths(d)
        R.apply = _counting
        for o in ws:
            try:
                o.touch()
            except Exception:
                pass
        d.recompute()
        R.apply = _orig_apply
        diag['calls_after_touch'] = calls['n']
        diag['after_touch'] = [[o.WireId, bool(o.Shape.isNull()), round(o.Shape.Length, 1) if not o.Shape.isNull() else None, str(o.Validation)] for o in ws]
        res.setdefault('diag', {})[name] = diag
        res.setdefault('callsite_after_touch', {})[name] = measure(d)
        res.setdefault('paths_callsite_after_touch', {})[name] = wire_paths(d)
        res.setdefault('plan_calls', {})[name] = calls['n']
        rows = R.reroute(d)
        after = measure(d)
        after_paths = wire_paths(d)
        installed = 0
        row = {'wires_built': n, 'before': before, 'callsite': hooked, 'after': after,
               'installed': installed,
               'hook_active': bool(getattr(__import__('DeltaEngineering.core', fromlist=['x']).Connection,
                                           '_wire_route_installed', False)),
               'wires_changed_by_hook': sum(1 for w in before_paths if hooked_paths.get(w) != before_paths[w]),
               'wires_changed_by_reroute': sum(1 for w in before_paths if after_paths.get(w) != before_paths[w]),
               'plan_matches_shape': sum(1 for r in rows if [list(q) for q in r['path']] == after_paths.get(r['wire'])),
               'paths_after': after_paths,
               'routed': sum(1 for r in rows if r['routed']),
               'fallback': [r['wire'] for r in rows if not r['routed']],
               'segments_in_foreign_box': sum(r['segments_in_foreign_box'] for r in rows),
               'per_wire': rows}
        row['pdf_bytes'] = sheet(d, OUT + '/%s_A3.pdf' % name, title)
        d.saveAs(OUT + '/%s.FCStd' % name)
        out[name] = row
    res.update(out)
    res['done'] = True
except Exception:
    res['error'] = traceback.format_exc()
json.dump(res, open(OUT + '/result.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({k: (v if not isinstance(v, dict) else
                      {kk: vv for kk, vv in v.items() if kk != 'per_wire'})
                  for k, v in res.items()}, ensure_ascii=False))
