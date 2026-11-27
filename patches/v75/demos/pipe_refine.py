# -*- coding: utf-8 -*-
"""Piping refinements layered on top of network.py, without editing network.py:
- route(): turn a diagonal run into axis-aligned legs (a dogleg) so every bend lands on a real 90 degree fitting;
- fitting_report(): one row per fitting (kind, table dimension, setback actually used);
- tangent_report(): segments shorter than a caller-given limit, for review (no limit is invented here);
- plan_pdf(): A3 plan sheet with numbered node balloons, segment labels placed clear of each other,
  a distinct symbol per fitting kind and a legend.
Generic model, illustrative only: not a hydraulic design and not a code design. GPL-3.0-or-later.
"""
import math
import os
import FreeCAD as App
from . import network as N

EPS = 1e-6


def _pick(first, a, b):
    if callable(first):
        return first(a, b)
    if isinstance(first, dict):
        return first.get((a, b), first.get((b, a), 'x'))
    return first


def route(nodes, edges, first='x', tol=1e-6):
    """Return (nodes, edges, inserted) with every planar edge axis aligned.

    An edge a-b whose x and y both differ gets one extra node: at (b.x, a.y) when first == 'x',
    else at (a.x, b.y). The extra node has degree 2, so it becomes a 90 degree elbow and the two
    endpoints keep a straight leg in the axis that was chosen. Edges already axis aligned, or that
    differ only in Z (a riser), are left alone. 'first' may be 'x'/'y', a {(a, b): 'x'|'y'} dict,
    or a callable(a, b).
    """
    out = dict(nodes)
    ins = {}
    new_edges = []
    for a, b in edges:
        if a not in out or b not in out:
            raise ValueError('Edge %s-%s names a node that does not exist' % (a, b))
        pa, pb = out[a], out[b]
        dx, dy = pb.x - pa.x, pb.y - pa.y
        if abs(dx) < tol or abs(dy) < tol:
            new_edges.append((a, b))
            continue
        name = '%s~%s' % (a, b)
        k = 2
        while name in out:
            name = '%s~%s_%d' % (a, b, k)
            k += 1
        p = App.Vector(pb.x, pa.y, pa.z) if _pick(first, a, b) == 'x' else App.Vector(pa.x, pb.y, pa.z)
        for other, q in out.items():
            if (p - q).Length < tol:
                raise ValueError('Dogleg for %s-%s would land on node %s' % (a, b, other))
        out[name] = p
        ins[name] = (a, b)
        new_edges += [(a, name), (name, b)]
    return out, new_edges, ins


def route_report(nodes, edges, tol=1e-6):
    """Check the routed graph: every edge axis aligned in the XY plane, no zero length, no duplicate."""
    bad = []
    seen = set()
    for a, b in edges:
        if a not in nodes or b not in nodes:
            bad.append('%s-%s: missing node' % (a, b))
            continue
        key = tuple(sorted((a, b)))
        if key in seen:
            bad.append('%s-%s: duplicate edge' % (a, b))
        seen.add(key)
        d = nodes[b] - nodes[a]
        if d.Length < tol:
            bad.append('%s-%s: zero length' % (a, b))
        elif abs(d.x) > tol and abs(d.y) > tol:
            bad.append('%s-%s: still diagonal in plan (%.0f, %.0f)' % (a, b, d.x, d.y))
    return bad


def fitting_report(res, nps):
    """Per-fitting rows: kind, the B16.9 table value used, and the setback the builder applied."""
    from . import fittings_library as FL
    rows = []
    for n in sorted(res['plan']['fittings']):
        f = res['plan']['fittings'][n]
        k = f['kind']
        if k == 'tee_eq':
            c, m = FL.TEE_EQ_CM[nps]
            rows.append({'node': n, 'kind': k, 'table': 'TEE_EQ_CM', 'run_c_mm': float(c), 'branch_m_mm': float(m),
                         'setback_mm': float(f['c'])})
        elif k == 'elbow90lr':
            v = float(FL.ELBOW_90_LR_A[nps])
            rows.append({'node': n, 'kind': k, 'table': 'ELBOW_90_LR_A', 'run_c_mm': v, 'branch_m_mm': None,
                         'setback_mm': float(f['setback'])})
        elif k == 'elbow45':
            v = float(FL.ELBOW_45_LR_B[nps])
            rows.append({'node': n, 'kind': k, 'table': 'ELBOW_45_LR_B', 'run_c_mm': v, 'branch_m_mm': None,
                         'setback_mm': float(f['setback'])})
        else:
            rows.append({'node': n, 'kind': k, 'table': '?', 'run_c_mm': None, 'branch_m_mm': None,
                         'setback_mm': None})
    return rows


def tangent_report(res, min_mm=None):
    """Segments shorter than min_mm, for review. No limit is chosen here; pass one or get an empty list."""
    if min_mm is None:
        return []
    out = []
    for i, s in enumerate(res['plan']['segments'], 1):
        if s['length'] < min_mm:
            out.append({'segment': 'P%d' % i, 'edge': '%s-%s' % (s['a'], s['b']), 'length_mm': round(s['length'], 1)})
    return out


class _Labels(object):
    """Keeps the boxes already used on the sheet so the next label can pick a free slot."""

    def __init__(self):
        self.boxes = []

    def add(self, x, y, w, h):
        self.boxes.append((x, y, w, h))

    def free(self, x, y, w, h, pad=1.0):
        for bx, by, bw, bh in self.boxes:
            if x < bx + bw + pad and bx < x + w + pad and y < by + bh + pad and by < y + h + pad:
                return False
        return True


def _tw(s, size):
    return 0.52 * size * len(s)


def _circle(pg, cx, cy, r, width=1.0, rgb=(0.2, 0.2, 0.2), n=16):
    pts = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n + 1)]
    pg.line(pts, width, rgb)


def _dirs(nodes, edges, n):
    out = []
    for a, b in edges:
        if n in (a, b):
            o = b if a == n else a
            out.append(math.atan2(nodes[o].y - nodes[n].y, nodes[o].x - nodes[n].x))
    return out


def _free_angle(dirs, ox, oy):
    ang = math.atan2(oy, ox)
    if not dirs:
        return 3.0
    return min(abs(math.atan2(math.sin(ang - d), math.cos(ang - d))) for d in dirs)


def plan_pdf(path, nodes, edges, res, nps, sch, rows, cnt, tot, title='Pipe network plan',
             symbols=None, note='Generic model, illustrative only: not a hydraulic design.'):
    """A3 plan sheet: centre lines, one symbol per fitting kind, numbered node balloons with a tag legend,
    segment labels placed in free slots, schedule table. symbols: [(x, y, w, h, label)] in model mm."""
    from . import minipdf
    pw, ph = 1190.55, 841.89
    xs = [v.x for v in nodes.values()]
    ys = [v.y for v in nodes.values()]
    x0, x1, y0, y1 = min(xs) - 900.0, max(xs) + 900.0, min(ys) - 700.0, max(ys) + 700.0
    aw, ah = pw - 470.0 - 60.0, ph - 60.0 - 80.0
    sc = min(aw / max(x1 - x0, 1.0), ah / max(y1 - y0, 1.0))
    ox = 30.0 + (aw - (x1 - x0) * sc) / 2.0
    oy = 60.0 + (ah - (y1 - y0) * sc) / 2.0
    X = lambda x: ox + (x - x0) * sc
    Y = lambda y: oy + (y - y0) * sc
    pg = minipdf.Page(pw, ph)
    pg.rect(20, 20, pw - 40, ph - 40, 1.5)
    for s in res['plan']['segments']:
        a = s['start']
        b = a + s['dir'] * s['length']
        pg.line([(X(a.x), Y(a.y)), (X(b.x), Y(b.y))], 2.2, (0.1, 0.25, 0.5))
    lab = _Labels()
    for x, y, w, h, label in (symbols or []):
        pg.rect(X(x), Y(y), w * sc, h * sc, 1.2)
        pg.text(X(x) + 3, Y(y) + h * sc / 2 - 2, label, 7)
        lab.add(X(x), Y(y), w * sc, h * sc)
    for n, f in res['plan']['fittings'].items():
        p = nodes[n]
        cx, cy = X(p.x), Y(p.y)
        k = f['kind']
        if k == 'tee_eq':
            pg.line([(cx - 7, cy), (cx + 7, cy)], 1.8, (0.8, 0.2, 0.1))
            pg.line([(cx, cy), (cx, cy + 7)], 1.8, (0.8, 0.2, 0.1))
        elif k == 'elbow45':
            pg.line([(cx - 6, cy - 6), (cx + 6, cy + 6)], 1.8, (0.8, 0.2, 0.1))
        else:
            pg.line([(cx - 5, cy - 5), (cx + 5, cy + 5)], 1.8, (0.8, 0.2, 0.1))
            pg.line([(cx - 5, cy + 5), (cx + 5, cy - 5)], 1.8, (0.8, 0.2, 0.1))
    tags = {}
    cand = ((0, 18), (18, 18), (18, 0), (18, -18), (0, -18), (-18, -18), (-18, 0), (-18, 18))
    for i, n in enumerate(sorted(nodes), 1):
        tags[n] = i
        p = nodes[n]
        cx, cy = X(p.x), Y(p.y)
        dirs = _dirs(nodes, edges, n)
        best, bs = cand[0], -9.0
        for ox2, oy2 in cand:
            if not lab.free(cx + ox2 - 8, cy + oy2 - 8, 16, 16):
                continue
            s2 = _free_angle(dirs, ox2, oy2)
            if s2 > bs + 1e-9:
                bs, best = s2, (ox2, oy2)
        bx, by = cx + best[0], cy + best[1]
        _circle(pg, bx, by, 8)
        pg.text(bx - (2.0 if i < 10 else 4.5), by - 2.5, str(i), 6.5)
        if math.hypot(bx - cx, by - cy) > 11:
            pg.line([(cx, cy), (bx, by)], 0.5, (0.45, 0.45, 0.45))
        lab.add(bx - 8, by - 8, 16, 16)
    placed = 0
    for i, s in enumerate(res['plan']['segments'], 1):
        a = s['start']
        b = a + s['dir'] * s['length']
        mx, my = (X(a.x) + X(b.x)) / 2.0, (Y(a.y) + Y(b.y)) / 2.0
        nx, ny = -s['dir'].y, s['dir'].x
        txt = 'P%d %s-%s L=%s' % (i, s['a'], s['b'], ('%.0f' % s['length']))
        w, h = _tw(txt, 6.5), 8.0
        for k in (10, -10, 20, -20, 30, -30):
            lx = mx + nx * k - (0 if nx >= 0 else w)
            ly = my + ny * k - 3
            if lab.free(lx, ly, w, h):
                pg.text(lx, ly, txt, 6.5, (0.1, 0.25, 0.5))
                lab.add(lx, ly, w, h)
                placed += 1
                break
    tx = pw - 400.0
    ty = ph - 60.0
    pg.text(tx, ty, title, 9)
    ty -= 13
    pg.text(tx, ty, 'NPS %s, %s. ILLUSTRATIVE, generic.' % (nps, sch), 7)
    ty -= 16
    for row in rows:
        if ty < 70:
            break
        pg.text(tx, ty, '%s  %s  %s  %.1f mm' % row, 7)
        ty -= 11
    ty -= 6
    pg.text(tx, ty, 'Fittings: ' + (', '.join('%s x%d' % kv for kv in cnt.items()) or '-'), 7)
    ty -= 11
    pg.text(tx, ty, 'Total straight pipe: %.1f mm' % tot, 7)
    ty -= 18
    pg.text(tx, ty, 'Node tags', 7.5)
    ty -= 11
    col = 0
    for n in sorted(nodes):
        if ty < 62:
            break
        pg.text(tx + col * 135, ty, '%d = %s' % (tags[n], n), 6.5)
        if col == 1:
            col = 0
            ty -= 10
        else:
            col = 1
    if col == 1:
        ty -= 10
    ty -= 10
    pg.text(tx, ty, 'Symbols', 7.5)
    ty -= 10
    pg.text(tx, ty, 'X elbow 90 / 45   T tee', 6.5)
    ty -= 10
    pg.text(tx, ty, note, 6)
    ty -= 10
    pg.text(tx, ty, 'Bends, tees and pipe lengths come from the fittings tables in the program.', 6)
    pg.save(path)
    return {'pdf_bytes': os.path.getsize(path), 'segments_labeled': placed, 'segments': len(res['plan']['segments']),
            'nodes': len(nodes), 'tags': len(tags)}


LAST = {}


def remember(nodes, edges, res, nps, sch):
    LAST.clear()
    LAST.update(nodes=nodes, edges=edges, res=res, nps=nps, sch=sch)


class _Cmd(object):
    def GetResources(self):
        return {'MenuText': 'مخطط شبكة محسّن (A3 PDF)',
                'ToolTip': 'يرسم آخر شبكة مواسير على ورقة A3: أرقام العقد، أسماء المواسير وأطوالها، ورمز لكل وصلة'}

    def IsActive(self):
        return True

    def Activated(self):
        from PySide import QtWidgets
        if not LAST:
            QtWidgets.QMessageBox.warning(None, 'مخطط الشبكة', 'أنشئ شبكة مواسير أولاً')
            return
        p, _ = QtWidgets.QFileDialog.getSaveFileName(None, 'اسم ملف PDF', '', 'PDF (*.pdf)')
        if not p:
            return
        try:
            rows, cnt, tot = N.schedule_rows(LAST['res'], LAST['nps'], LAST['sch'])
            plan_pdf(p, LAST['nodes'], LAST['edges'], LAST['res'], LAST['nps'], LAST['sch'], rows, cnt, tot)
        except Exception as e:
            QtWidgets.QMessageBox.warning(None, 'تعذر الرسم', str(e))
            return
        QtWidgets.QMessageBox.information(None, 'تم', p)


def register():
    import FreeCADGui as Gui
    Gui.addCommand('Delta_Net_Refine_Export', _Cmd())
    if not getattr(N, '_refine_patched', False):
        orig = N.build

        def build(doc, nodes, edges, nps, schedule='SCH 40'):
            r = orig(doc, nodes, edges, nps, schedule)
            remember(nodes, edges, r, nps, schedule)
            return r
        N.build = build
        N._refine_patched = True
    from .gui import DeltaWorkbench
    if getattr(DeltaWorkbench, '_refine_patched', False):
        return
    o = DeltaWorkbench.Initialize

    def Initialize(self):
        o(self)
        self.appendToolbar('شبكات المواسير', ['Delta_Net_Refine_Export'])
        self.appendMenu('شبكات المواسير', ['Delta_Net_Refine_Export'])
    DeltaWorkbench._refine_patched = True
    DeltaWorkbench.Initialize = Initialize
