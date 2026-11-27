# -*- coding: utf-8 -*-
"""Orthogonal router for schematic wires. GPL-3.0-or-later.

The stock core draws a wire as one straight line, one L, or one Z, so parallel wires land on
top of each other and wires run through symbol bodies and labels. This module plans an
orthogonal path that stays out of every device box, keeps clear of the wires already routed
and pays for crossing them, then writes that path into the same Connection object. The
straight, L and Z behaviour stays as the fallback.

route() is plain geometry on (x, y) tuples and imports nothing; FreeCAD is only touched in
plan(), install() and reroute(). UNTESTED until a CI run executes it.
"""
import heapq

EPS = 1e-6
BEND = 20.0        # cost of one bend, in mm of length
CROSS = 60.0       # cost of crossing a wire already routed, in mm of length
OVERLAP = 1200.0   # cost of running along a wire already routed, in mm of length
STUB = 12.0        # straight run out of a terminal before the router may turn, mm

LAST = {'ok': True, 'reason': 'not run'}


def _unit(d):
    dx, dy = float(d[0]), float(d[1])
    if abs(dx) >= abs(dy):
        return (1.0 if dx >= 0 else -1.0, 0.0)
    return (0.0, 1.0 if dy >= 0 else -1.0)


def _l_shape(a, b):
    """The old core path: a straight line when one axis is equal, otherwise one L."""
    if abs(a[1] - b[1]) < EPS or abs(a[0] - b[0]) < EPS:
        return [a, b]
    return [a, (b[0], a[1]), b]


def _inside(pt, r):
    x, y = pt
    return r[0] + EPS < x < r[2] - EPS and r[1] + EPS < y < r[3] - EPS


def _hits_rect(p, q, r):
    """True when the axis-aligned segment p-q passes through the open box r."""
    ax, ay = p
    bx, by = q
    if abs(ay - by) < EPS:
        if not (r[1] + EPS < ay < r[3] - EPS):
            return False
        lo, hi = (ax, bx) if ax <= bx else (bx, ax)
        return lo < r[2] - EPS and hi > r[0] + EPS
    if abs(ax - bx) < EPS:
        if not (r[0] + EPS < ax < r[2] - EPS):
            return False
        lo, hi = (ay, by) if ay <= by else (by, ay)
        return lo < r[3] - EPS and hi > r[1] + EPS
    return False


def _relation(p, q, s):
    """('overlap', length, (lo, hi)) | ('cross', point) | None between segment p-q and segment s."""
    (ax, ay), (bx, by) = p, q
    (cx, cy), (dx, dy) = s
    h1 = abs(ay - by) < EPS
    h2 = abs(cy - dy) < EPS
    if h1 and h2:
        if abs(ay - cy) > EPS:
            return None
        lo = max(min(ax, bx), min(cx, dx))
        hi = min(max(ax, bx), max(cx, dx))
        return ('overlap', hi - lo, ((lo, ay), (hi, ay))) if hi - lo > EPS else None
    if (not h1) and (not h2):
        if abs(ax - cx) > EPS:
            return None
        lo = max(min(ay, by), min(cy, dy))
        hi = min(max(ay, by), max(cy, dy))
        return ('overlap', hi - lo, ((ax, lo), (ax, hi))) if hi - lo > EPS else None
    if h1:
        hlo, hhi = (ax, bx) if ax <= bx else (bx, ax)
        vlo, vhi = (cy, dy) if cy <= dy else (dy, cy)
        if hlo + EPS < cx < hhi - EPS and vlo + EPS < ay < vhi - EPS:
            return ('cross', (cx, ay))
        return None
    hlo, hhi = (cx, dx) if cx <= dx else (dx, cx)
    vlo, vhi = (ay, by) if ay <= by else (by, ay)
    if hlo + EPS < ax < hhi - EPS and vlo + EPS < cy < vhi - EPS:
        return ('cross', (ax, cy))
    return None


def exit_dir(box, point):
    """Unit vector from the box centre to the terminal; the largest component wins."""
    cx, cy = (box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0
    return _unit((point[0] - cx, point[1] - cy))


def _stub(a, d, obstacles, own):
    """Longest stub out of a terminal that does not enter another device box."""
    for k in (STUB, STUB / 2.0, STUB / 4.0):
        p = (a[0] + d[0] * k, a[1] + d[1] * k)
        if not any(_hits_rect(a, p, r) for i, r in enumerate(obstacles) if i != own):
            return p
    return a


def _trim(p, q, k):
    dx, dy = q[0] - p[0], q[1] - p[1]
    span = abs(dx) + abs(dy)
    if span <= 2 * k:
        return None
    ux, uy = dx / span, dy / span
    return ((p[0] + ux * k, p[1] + uy * k), (q[0] - ux * k, q[1] - uy * k))


def _snap(v, grid):
    return round(v / grid) * grid


def _coords(start, end, obstacles, grid, margin):
    xs = {start[0], end[0]}
    ys = {start[1], end[1]}
    for r in obstacles:
        for v in (r[0] - margin, r[0], r[2], r[2] + margin):
            xs.add(_snap(v, grid))
        for v in (r[1] - margin, r[1], r[3], r[3] + margin):
            ys.add(_snap(v, grid))
    if obstacles:
        xs.add(_snap(min(r[0] for r in obstacles) - 2 * margin, grid))
        xs.add(_snap(max(r[2] for r in obstacles) + 2 * margin, grid))
        ys.add(_snap(min(r[1] for r in obstacles) - 2 * margin, grid))
        ys.add(_snap(max(r[3] for r in obstacles) + 2 * margin, grid))
    return sorted(xs), sorted(ys)


def route_ex(a, b, a_dir, b_dir, obstacles, used, grid=5.0, margin=6.0, bend=BEND):
    """Plan a path. Returns (points, ok, reason); ok False means the L-shape fallback."""
    a = (float(a[0]), float(a[1]))
    b = (float(b[0]), float(b[1]))
    da = _unit(a_dir)
    db = _unit(b_dir)
    obstacles = [tuple(float(v) for v in r) for r in obstacles]
    used = [((float(s[0][0]), float(s[0][1])), (float(s[1][0]), float(s[1][1]))) for s in used]

    if abs(a[0] - b[0]) < EPS or abs(a[1] - b[1]) < EPS:
        # a straight run stays straight unless a box is in the way or another wire already
        # runs along it; crossing another wire is left alone, the straight run is what it costs.
        # the first and last margin mm are the terminal itself, so they are not tested
        clear = True
        trimmed = _trim(a, b, margin)
        if trimmed is not None:
            clear = not any(_hits_rect(trimmed[0], trimmed[1], r) for r in obstacles)
        free = True
        for s in used:
            rel = _relation(a, b, s)
            if rel is not None and rel[0] == 'overlap':
                free = False
                break
        if clear and free:
            return ([a, b], True, 'straight')

    own_a = next((i for i, r in enumerate(obstacles) if _inside(a, r)), -1)
    own_b = next((i for i, r in enumerate(obstacles) if _inside(b, r)), -1)
    sa = _stub(a, da, obstacles, own_a)
    sb = _stub(b, db, obstacles, own_b)

    xs, ys = _coords(sa, sb, obstacles, grid, margin)
    ix = {v: i for i, v in enumerate(xs)}
    iy = {v: j for j, v in enumerate(ys)}
    si, sj = ix[sa[0]], iy[sa[1]]
    gi, gj = ix[sb[0]], iy[sb[1]]
    dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))

    def blocked(p, q):
        return any(_hits_rect(p, q, r) for r in obstacles)

    def near_terminal(pt):
        # inside the junction area of either terminal: two wires meeting at a terminal share
        # the approach, that is a node, not a defect
        return (abs(pt[0] - a[0]) <= 2 * STUB and abs(pt[1] - a[1]) <= 2 * STUB) or \
               (abs(pt[0] - b[0]) <= 2 * STUB and abs(pt[1] - b[1]) <= 2 * STUB)

    def wire_cost(p, q):
        c = 0.0
        for s in used:
            rel = _relation(p, q, s)
            if rel is None:
                continue
            if rel[0] == 'cross':
                c += CROSS
                continue
            lo, hi = rel[2]
            if near_terminal(lo) and near_terminal(hi):
                continue       # two wires sharing the approach to one terminal: a node
            c += OVERLAP
        return c

    start = (si, sj, dirs.index(da))
    best = {start: 0.0}
    prev = {}
    heap = [(0.0, 0.0, start)]
    goal = None
    nx, ny = len(xs), len(ys)
    while heap:
        _f, cost, state = heapq.heappop(heap)
        if cost > best.get(state, float('inf')) + EPS:
            continue
        i, j, d = state
        if (i, j) == (gi, gj) and dirs[d] != db:
            goal = state
            break
        for nd, (dx, dy) in enumerate(dirs):
            ni, nj = i + dx, j + dy
            if not (0 <= ni < nx and 0 <= nj < ny):
                continue
            if (ni, nj) == (gi, gj) and dirs[nd] == db:
                continue
            p = (xs[i], ys[j])
            q = (xs[ni], ys[nj])
            if blocked(p, q):
                continue
            step = abs(q[0] - p[0]) + abs(q[1] - p[1])
            if step < EPS:
                continue
            nc = cost + step + wire_cost(p, q) + (0.0 if nd == d else bend)
            ns = (ni, nj, nd)
            if nc + EPS < best.get(ns, float('inf')):
                best[ns] = nc
                prev[ns] = state
                h = abs(xs[ni] - xs[gi]) + abs(ys[nj] - ys[gj])
                heapq.heappush(heap, (nc + h, nc, ns))
    if goal is None:
        return (_l_shape(a, b), False, 'no path')
    chain = [goal]
    while chain[-1] != start:
        chain.append(prev[chain[-1]])
    chain.reverse()
    pts = [a, sa] + [(xs[i], ys[j]) for (i, j, _d) in chain[1:]] + [sb, b]
    out = [pts[0]]
    for p in pts[1:]:
        if abs(p[0] - out[-1][0]) > EPS or abs(p[1] - out[-1][1]) > EPS:
            out.append(p)
    return (out, True, 'routed')


def route(a, b, a_dir, b_dir, obstacles, used, grid=5.0, margin=6.0):
    """Orthogonal path from a to b: first point a, last point b.

    obstacles: (xmin, ymin, xmax, ymax) boxes of all devices, including both endpoints.
    used: ((x1, y1), (x2, y2)) axis-aligned segments of wires already routed.
    Falls back to the old L-shape when nothing is found; LAST says which happened.
    """
    pts, ok, reason = route_ex(a, b, a_dir, b_dir, obstacles, used, grid, margin)
    LAST['ok'] = ok
    LAST['reason'] = reason
    return pts


def clean(points):
    """Drop duplicate and collinear points."""
    out = []
    for p in points:
        if not out or abs(p[0] - out[-1][0]) > EPS or abs(p[1] - out[-1][1]) > EPS:
            out.append(p)
    i = 1
    while i < len(out) - 1:
        a, b, c = out[i - 1], out[i], out[i + 1]
        if (abs(a[0] - b[0]) < EPS and abs(b[0] - c[0]) < EPS) or (abs(a[1] - b[1]) < EPS and abs(b[1] - c[1]) < EPS):
            out.pop(i)
        else:
            i += 1
    return out


# ---------------------------------------------------------------- FreeCAD side

def boxes(doc):
    """[(object, (xmin, ymin, xmax, ymax))] for every device with a computed shape."""
    out = []
    for o in doc.Objects:
        shape = getattr(o, 'Shape', None)
        if getattr(o, 'DeviceType', None) and shape is not None and not shape.isNull():
            bb = shape.BoundBox
            out.append((o, (bb.XMin, bb.YMin, bb.XMax, bb.YMax)))
    return out


def segments(shape):
    """Axis-aligned ((x1, y1), (x2, y2)) segments of a shape; curved edges are skipped."""
    out = []
    for e in shape.Edges:
        a = e.Vertexes[0].Point
        b = e.Vertexes[-1].Point
        if abs(a.x - b.x) > EPS and abs(a.y - b.y) > EPS:
            continue
        out.append(((a.x, a.y), (b.x, b.y)))
    return out


def _ends(obj, rects, index):
    from . import core
    a = core.terminal_position(obj.SourceDevice, obj.SourceTerminal)
    b = core.terminal_position(obj.TargetDevice, obj.TargetTerminal)
    pa, pb = (a.x, a.y), (b.x, b.y)
    ia = index.get(id(obj.SourceDevice), -1)
    ib = index.get(id(obj.TargetDevice), -1)
    da = exit_dir(rects[ia], pa) if ia >= 0 else (1.0, 0.0)
    db = exit_dir(rects[ib], pb) if ib >= 0 else (-1.0, 0.0)
    return pa, pb, da, db, ia, ib


def plan(obj, doc=None):
    """Plan this wire from the document, or None when the stock path should be kept."""
    doc = doc or obj.Document
    if abs(obj.SchematicOffset.Value) > EPS:
        return None
    if not obj.SourceDevice or not obj.TargetDevice:
        return None
    found = boxes(doc)
    if not found:
        return None
    rects = [r for _o, r in found]
    index = {id(o): i for i, (o, _r) in enumerate(found)}
    pa, pb, da, db, _ia, _ib = _ends(obj, rects, index)
    used = []
    for o in doc.Objects:
        if o is obj:
            break
        shape = getattr(o, 'Shape', None)
        if hasattr(o, 'SourceTerminal') and shape is not None and not shape.isNull():
            used += segments(shape)
    return route_ex(pa, pb, da, db, rects, used)


def _write(obj, pts):
    import FreeCAD as App
    import Part
    pts = clean(pts)
    vec = [App.Vector(x, y, 0) for x, y in pts]
    obj.Shape = Part.makeLine(vec[0], vec[1]) if len(vec) == 2 else Part.makePolygon(vec)


def install():
    """Wrap core.Connection.execute. Idempotent. Returns 1 when installed, 0 when already there."""
    from . import core
    if getattr(core.Connection, '_wire_route_installed', False):
        return 0
    original = core.Connection.execute

    def execute(self, obj):
        planned = None
        try:
            planned = plan(obj)
        except Exception:
            planned = None
        if planned is None:
            return original(self, obj)
        pts, ok = planned
        if len(clean(pts)) < 2:
            return original(self, obj)
        try:
            _write(obj, pts)
            obj.Validation = 'Logical connection only' if ok else 'Route fallback'
        except Exception:
            return original(self, obj)
        return None

    core.Connection.execute = execute
    core.Connection._wire_route_installed = True
    return 1


def reroute(doc):
    """Route every wire in document order; return one report row per wire."""
    found = boxes(doc)
    rects = [r for _o, r in found]
    index = {id(o): i for i, (o, _r) in enumerate(found)}
    done = []
    report = []
    for obj in [o for o in doc.Objects if hasattr(o, 'SourceTerminal')]:
        if not obj.SourceDevice or not obj.TargetDevice:
            continue
        pa, pb, da, db, ia, ib = _ends(obj, rects, index)
        pts, ok, reason = route_ex(pa, pb, da, db, rects, done)
        _write(obj, pts)
        obj.Validation = 'Logical connection only' if ok else 'Route fallback'
        done += segments(obj.Shape)
        inside = 0
        for (p, q) in zip(pts, pts[1:]):
            for i, r in enumerate(rects):
                if i not in (ia, ib) and _hits_rect(p, q, r):
                    inside += 1
        cl = clean(pts)
        report.append({'wire': obj.WireId, 'points': len(cl), 'routed': ok,
                       'reason': reason, 'segments_in_foreign_box': inside,
                       'path': [(round(x, 1), round(y, 1)) for x, y in cl]})
    return report


def overlaps(doc):
    """Overlapping collinear segment pairs between different wires: (id, id, mm, junction).

    junction=True means the shared run lies at a terminal both wires end on, which is a node
    and not a drafting defect."""
    ends = {}
    segs = []
    for o in doc.Objects:
        shape = getattr(o, 'Shape', None)
        if hasattr(o, 'SourceTerminal') and shape is not None and not shape.isNull():
            sg = segments(shape)
            if sg:
                ends[o.WireId] = (sg[0][0], sg[-1][1])
            for s in sg:
                segs.append((o.WireId, s))

    def shared_terminal(w1, w2, pt, k=2 * STUB):
        # is pt within the junction area of a terminal that both wires end on
        e1, e2 = ends.get(w1), ends.get(w2)
        if e1 is None or e2 is None:
            return False
        for t in e1:
            if abs(pt[0] - t[0]) > k or abs(pt[1] - t[1]) > k:
                continue
            for u in e2:
                if abs(pt[0] - u[0]) <= k and abs(pt[1] - u[1]) <= k:
                    return True
        return False

    hits = []
    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            if segs[i][0] == segs[j][0]:
                continue
            rel = _relation(segs[i][1][0], segs[i][1][1], segs[j][1])
            if rel and rel[0] == 'overlap':
                lo, hi = rel[2]
                junc = (shared_terminal(segs[i][0], segs[j][0], lo) and
                        shared_terminal(segs[i][0], segs[j][0], hi))
                hits.append((segs[i][0], segs[j][0], round(rel[1], 2), junc))
    return hits


def crossings(doc):
    """Count perpendicular crossings between different wires."""
    segs = []
    for o in doc.Objects:
        shape = getattr(o, 'Shape', None)
        if hasattr(o, 'SourceTerminal') and shape is not None and not shape.isNull():
            for s in segments(shape):
                segs.append((o.WireId, s))
    hits = []
    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            if segs[i][0] == segs[j][0]:
                continue
            rel = _relation(segs[i][1][0], segs[i][1][1], segs[j][1])
            if rel and rel[0] == 'cross':
                hits.append((segs[i][0], segs[j][0]))
    return hits
