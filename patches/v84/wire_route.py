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
CROSS = 120.0      # cost of crossing a wire already routed, in mm of length
OVERLAP = 250.0    # cost per mm of running along a wire already routed
NEAR = 12.0        # cost per mm of running closer than NEAR_GAP to a parallel wire
NEAR_GAP = 5.0     # mm; lanes are LANE apart, so only real hugging pays this
LANE = 8.0         # spacing between parallel lanes, mm
STUB = 14.0        # straight run out of a terminal before the router may turn, mm;
                   # margin + LANE, so a stub end lands on a lane and runs beside it stay LANE apart
LOOP_MAX = 1.9     # a path longer than this x the manhattan distance ...
LOOP_SLACK = 150.0 # ... plus this many mm is refused as a loop
TAG_H = 12.0       # estimated label boxes, mm: tag height above a symbol
TAG_W = 6.0        # estimated width per tag character
TAG_PAD = 2.0      # gap between symbol box and its tag
LBL_W = 14.0       # estimated terminal label box
LBL_H = 10.0

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


def _near(p, q, s, gap):
    """Length over which segment p-q runs parallel to s within gap mm."""
    (ax, ay), (bx, by) = p, q
    (cx, cy), (dx, dy) = s
    h1 = abs(ay - by) < EPS
    h2 = abs(cy - dy) < EPS
    if h1 != h2:
        return 0.0
    if h1:
        if abs(ay - cy) > gap:
            return 0.0
        lo = max(min(ax, bx), min(cx, dx))
        hi = min(max(ax, bx), max(cx, dx))
    else:
        if abs(ax - cx) > gap:
            return 0.0
        lo = max(min(ay, by), min(cy, dy))
        hi = min(max(ay, by), max(cy, dy))
    return max(0.0, hi - lo)


def _touches(seg, pt, k=2.0):
    """True when pt lies on the axis-aligned segment seg, within k mm."""
    (p, q) = seg
    if abs(p[1] - q[1]) < EPS:                       # horizontal
        lo, hi = min(p[0], q[0]), max(p[0], q[0])
        return abs(pt[1] - p[1]) <= k and lo - k <= pt[0] <= hi + k
    if abs(p[0] - q[0]) < EPS:                       # vertical
        lo, hi = min(p[1], q[1]), max(p[1], q[1])
        return abs(pt[0] - p[0]) <= k and lo - k <= pt[1] <= hi + k
    return False


def exit_dir(box, point):
    """Unit vector from the box centre to the terminal; the largest component wins."""
    cx, cy = (box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0
    return _unit((point[0] - cx, point[1] - cy))


def _stub(a, d, obstacles, own):
    """Stub out of a terminal. Returns (point, escaped): escaped is True when the point is
    outside the terminal's own symbol box, so the A* may treat that box as a wall."""
    best = None
    for k in (STUB, STUB / 2.0, STUB / 4.0):
        p = (a[0] + d[0] * k, a[1] + d[1] * k)
        if any(_hits_rect(a, p, r) for i, r in enumerate(obstacles) if i != own):
            continue
        if own < 0 or not _inside(p, obstacles[own]):
            return p, True
        if best is None:
            best = p
    if best is not None:
        return best, False
    return a, own < 0


def _trim(p, q, k):
    dx, dy = q[0] - p[0], q[1] - p[1]
    span = abs(dx) + abs(dy)
    if span <= 2 * k:
        return None
    ux, uy = dx / span, dy / span
    return ((p[0] + ux * k, p[1] + uy * k), (q[0] - ux * k, q[1] - uy * k))


def _snap(v, grid):
    return round(v / grid) * grid


def _coords(start, end, obstacles, grid, margin, used=()):
    """Candidate x and y values: the ends, and LANE-spaced lanes beside every box.

    Lanes are exact multiples of LANE from a box edge, so two parallel runs are never closer
    than LANE. grid is kept for the signature; it no longer rounds lane positions.
    """
    xs = {start[0], end[0]}
    ys = {start[1], end[1]}
    lanes = (0.0, LANE, 2.0 * LANE)
    for r in obstacles:
        for k in lanes:
            # exact multiples of LANE, never snapped: rounding to the grid is what let two
            # lanes land 5 mm apart and read as one thick bar
            xs.add(r[0] - margin - k)
            xs.add(r[2] + margin + k)
            ys.add(r[1] - margin - k)
            ys.add(r[3] + margin + k)
    lo_x = min(start[0], end[0]) - 200.0
    hi_x = max(start[0], end[0]) + 200.0
    lo_y = min(start[1], end[1]) - 200.0
    hi_y = max(start[1], end[1]) + 200.0
    for (p, q) in used:
        # a lane beside every wire already routed, so a parallel run can sit LANE away from it
        # instead of detouring or piling onto it; only near this wire, or the grid explodes
        if not (lo_x <= p[0] <= hi_x and lo_y <= p[1] <= hi_y):
            continue
        if abs(p[1] - q[1]) < EPS:
            ys.add(p[1] + LANE)
            ys.add(p[1] - LANE)
        elif abs(p[0] - q[0]) < EPS:
            xs.add(p[0] + LANE)
            xs.add(p[0] - LANE)
    if obstacles:
        xs.add(min(r[0] for r in obstacles) - 2 * margin)
        xs.add(max(r[2] for r in obstacles) + 2 * margin)
        ys.add(min(r[1] for r in obstacles) - 2 * margin)
        ys.add(max(r[3] for r in obstacles) + 2 * margin)
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
    sa, esc_a = _stub(a, da, obstacles, own_a)
    sb, esc_b = _stub(b, db, obstacles, own_b)
    # a box may not be entered at all unless its own terminal could not leave it
    wall_a = -1 if esc_a else own_a
    wall_b = -1 if esc_b else own_b

    xs, ys = _coords(sa, sb, obstacles, grid, margin, used)
    ix = {v: i for i, v in enumerate(xs)}
    iy = {v: j for j, v in enumerate(ys)}
    si, sj = ix[sa[0]], iy[sa[1]]
    gi, gj = ix[sb[0]], iy[sb[1]]
    dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))

    def blocked(p, q):
        # the A* runs from stub to stub, both outside their boxes, so neither endpoint box may
        # be entered at all; only the a->sa and sb->b stubs touch a box, and those are not A*
        return any(_hits_rect(p, q, r) for i, r in enumerate(obstacles)
                   if i != wall_a and i != wall_b)

    def near_pt(pt, t, k=STUB):
        return abs(pt[0] - t[0]) <= k and abs(pt[1] - t[1]) <= k

    def is_junction(seg, lo, hi):
        # free only where the other wire actually ends on the same terminal and the shared run
        # is inside that terminal's stub zone; riding a long run into the terminal is not free
        for t in (a, b):
            if _touches(seg, t) and near_pt(lo, t) and near_pt(hi, t):
                return True
        return False

    def wire_cost(p, q):
        c = 0.0
        for s in used:
            rel = _relation(p, q, s)
            if rel is None:
                c += NEAR * _near(p, q, s, NEAR_GAP)
                continue
            if rel[0] == 'cross':
                c += CROSS
                continue
            lo, hi = rel[2]
            if is_junction(s, lo, hi):
                continue       # two wires meeting at one terminal: a node
            c += OVERLAP * rel[1]
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
    length = sum(abs(out[i + 1][0] - out[i][0]) + abs(out[i + 1][1] - out[i][1])
                 for i in range(len(out) - 1))
    manhattan = abs(b[0] - a[0]) + abs(b[1] - a[1])
    if length > LOOP_MAX * manhattan + LOOP_SLACK:
        return (_l_shape(a, b), False, 'detour')
    return (out, True, 'routed')


PRESETS = {
    'balanced': {'NEAR': 12.0, 'LANE': 8.0, 'CROSS': 120.0, 'OVERLAP': 250.0},
    'fewer-crossings': {'NEAR': 0.0, 'LANE': 6.0, 'CROSS': 200.0, 'OVERLAP': 250.0},
}


def preset(name='balanced'):
    """Set NEAR, LANE, CROSS, OVERLAP and the matching STUB. Returns the values set.

    'balanced' separates parallel runs and accepts the crossings that costs.
    'fewer-crossings' drops the hugging penalty and tightens the lanes, which crosses less and
    overlaps more.
    """
    global NEAR, LANE, CROSS, OVERLAP, STUB
    p = PRESETS[name]
    NEAR, LANE, CROSS, OVERLAP = p['NEAR'], p['LANE'], p['CROSS'], p['OVERLAP']
    STUB = 6.0 + LANE
    return dict(p, STUB=STUB)


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


def text_boxes(doc):
    """Estimated label boxes: the tag above each symbol and a box beside each terminal label.

    Labels are drawn, not modelled: the tag sits above the symbol's top-left corner and the
    terminal name just to the right of the terminal dot. Neither is geometry in the document,
    so these boxes are estimated from the tag string and the terminal positions. Point
    TEXT_BOXES at your own callable if the drawing places labels differently.
    """
    from . import core
    out = []
    for o, r in boxes(doc):
        tag = str(getattr(o, 'Tag', '') or '')
        w = max(20.0, TAG_W * max(len(tag), 2))
        out.append((r[0], r[3] + TAG_PAD, r[0] + w, r[3] + TAG_PAD + TAG_H))
        for name in list(getattr(o, 'Terminals', None) or []):
            try:
                p = core.terminal_position(o, name)
            except Exception:
                continue
            out.append((p.x + 2.0, p.y - LBL_H / 2.0, p.x + 2.0 + LBL_W, p.y + LBL_H / 2.0))
    return out


TEXT_BOXES = text_boxes


def _near_box(pt, r, k):
    dx = max(r[0] - pt[0], 0.0, pt[0] - r[2])
    dy = max(r[1] - pt[1], 0.0, pt[1] - r[3])
    return dx <= k and dy <= k


def _labels(doc, a, b, k=2 * STUB):
    """Label boxes that are not at either terminal of this wire."""
    fn = TEXT_BOXES
    if fn is None:
        return []
    try:
        found = fn(doc)
    except Exception:
        return []
    return [r for r in found if not _near_box(a, r, k) and not _near_box(b, r, k)]


def plan(obj, doc=None):
    """Plan this wire from the document, or None when the stock path should be kept.

    Planning only: nothing is written. Returns (points, ok, reason) exactly as route_ex does.
    Use apply() to plan and write in one step.
    """
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
    return route_ex(pa, pb, da, db, rects + _labels(doc, pa, pb), used)


def apply(obj, doc=None):
    """Plan this wire and write it. True when the router handled it, False to keep the stock path.

    This is the one place that turns a plan into geometry, so install() and any explicit call
    site behave the same.
    """
    planned = plan(obj, doc)
    if planned is None:
        return False
    pts, ok = planned[0], planned[1]
    if len(clean(pts)) < 2:
        return False
    try:
        _write(obj, pts)
    except Exception:
        return False
    obj.Validation = 'Logical connection only' if ok else 'Route fallback'
    return True


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
        # apply() plans and writes; it never returns a tuple, so this cannot mis-unpack a plan
        try:
            if apply(obj):
                return None
        except Exception:
            pass
        return original(self, obj)

    core.Connection._wire_route_original = original
    core.Connection.execute = execute
    core.Connection._wire_route_installed = True
    return 1


def uninstall():
    """Put the stock core.Connection.execute back. Returns 1 when removed, 0 when not installed."""
    from . import core
    if not getattr(core.Connection, '_wire_route_installed', False):
        return 0
    core.Connection.execute = core.Connection._wire_route_original
    del core.Connection._wire_route_original
    core.Connection._wire_route_installed = False
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
        pts, ok, reason = route_ex(pa, pb, da, db, rects + _labels(doc, pa, pb), done)
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
