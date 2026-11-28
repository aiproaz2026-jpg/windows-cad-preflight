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
import math

EPS = 1e-6
BEND = 20.0        # cost of one bend, in mm of length
CROSS = 260.0      # cost of crossing a wire already routed, in mm of length
OVERLAP = 2000.0   # cost per mm of running along a wire already routed: overlap dominates
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

CELL = 40.0        # spatial index cell, mm
STUB_CROSS = 120.0 # cost of crossing another wire's stub, so a fan leaves a dense face in order
MIN_CLEAR = 2.0    # mm a wire must keep from another wire and from a symbol box
MAX_POPS = 4000000  # A* pops before a pass gives up (with the edge cache this is a few seconds)
CLEAR_COST = 20.0  # cost of running closer than CLEAR_AT to a box
CLEAR_AT = 1.4     # mm; the cost starts here, so a 2 mm report does not distort the routing
HARD_CLEAR = 0.0   # mm; an edge this close to a symbol box is refused outright (0 = off)
SHADOW_MIN = 45.0  # mm a straight run must shadow before it gives way to a routed one
FAN_STEP_MIN = 12.0      # stub step on a dense face, mm
FAN_STEP_MAX = 20.0
FAN_DENSE_PITCH = 16.0   # a face with terminals this close or closer is dense and steps wider
FAN_ORDER_BY_ARRIVAL = False  # order a face by where its wires come from (off: terminal order)

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


def _run_holds(lo, hi, t, k=2.0):
    """True when the shared run lo-hi runs into point t, within k mm.

    Two wires that both end on one terminal draw the same approach into it. When the run they
    share holds that terminal, they are drawn as one line into it, which is a node; when the run
    starts at a terminal and leaves it, the two wires sit on top of each other."""
    if abs(lo[1] - hi[1]) < EPS:                     # horizontal run
        return (abs(t[1] - lo[1]) <= k and
                min(lo[0], hi[0]) - k <= t[0] <= max(lo[0], hi[0]) + k)
    if abs(lo[0] - hi[0]) < EPS:                     # vertical run
        return (abs(t[0] - lo[0]) <= k and
                min(lo[1], hi[1]) - k <= t[1] <= max(lo[1], hi[1]) + k)
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


class _SegIndex(object):
    """Grid index over axis-aligned segments, so the A* looks at the wires near an edge only."""

    def __init__(self, cell=CELL):
        self.cell = float(cell)
        self.grid = {}
        self.segs = []
        self._mark = []
        self._stamp = 0

    def keys(self, seg, pad=0.0):
        (x1, y1), (x2, y2) = seg
        c = self.cell
        i0 = int(math.floor((min(x1, x2) - pad) / c))
        i1 = int(math.floor((max(x1, x2) + pad) / c))
        j0 = int(math.floor((min(y1, y2) - pad) / c))
        j1 = int(math.floor((max(y1, y2) + pad) / c))
        for i in range(i0, i1 + 1):
            for j in range(j0, j1 + 1):
                yield (i, j)

    def add(self, seg, flag=None):
        n = len(self.segs)
        self.segs.append((seg, flag))
        for key in self.keys(seg):
            bucket = self.grid.get(key)
            if bucket is None:
                self.grid[key] = [n]
            else:
                bucket.append(n)

    def near(self, seg, pad=0.0):
        """Segments near seg. A stamp array instead of a set: this is the A* inner loop."""
        if len(self._mark) < len(self.segs):
            self._mark = [0] * len(self.segs)
        self._stamp += 1
        stamp = self._stamp
        out = []
        for key in self.keys(seg, pad):
            for n in self.grid.get(key, ()):
                if self._mark[n] != stamp:
                    self._mark[n] = stamp
                    out.append(self.segs[n])
        return out

    def __len__(self):
        return len(self.segs)


class _RectIndex(object):
    """Grid index over boxes: which boxes can an edge touch."""

    def __init__(self, rects, cell=CELL):
        self.cell = float(cell)
        self.rects = list(rects)
        self.grid = {}
        self._mark = []
        self._stamp = 0
        for n, r in enumerate(self.rects):
            for key in self.keys(((r[0], r[1]), (r[2], r[3])), 0.0):
                bucket = self.grid.get(key)
                if bucket is None:
                    self.grid[key] = [n]
                else:
                    bucket.append(n)

    def keys(self, seg, pad=0.0):
        (x1, y1), (x2, y2) = seg
        c = self.cell
        i0 = int(math.floor((min(x1, x2) - pad) / c))
        i1 = int(math.floor((max(x1, x2) + pad) / c))
        j0 = int(math.floor((min(y1, y2) - pad) / c))
        j1 = int(math.floor((max(y1, y2) + pad) / c))
        for i in range(i0, i1 + 1):
            for j in range(j0, j1 + 1):
                yield (i, j)

    def near(self, seg, pad=0.0):
        if len(self._mark) < len(self.rects):
            self._mark = [0] * len(self.rects)
        self._stamp += 1
        stamp = self._stamp
        out = []
        for key in self.keys(seg, pad):
            for n in self.grid.get(key, ()):
                if self._mark[n] != stamp:
                    self._mark[n] = stamp
                    out.append(n)
        return out


def exit_dir(box, point):
    """Unit vector from the box centre to the terminal; the largest component wins."""
    cx, cy = (box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0
    return _unit((point[0] - cx, point[1] - cy))


def _overlaps_used(a, p, used):
    """True when the stub a-p would run along a wire already routed.

    A wire that also starts at this terminal is a junction, not an overlap, so its segment is
    skipped: two wires on one terminal share their first millimetres by definition.
    """
    for s, _flag in used:
        rel = _relation(a, p, s)
        if rel is not None and rel[0] == 'overlap':
            if _touches(s, a, 2.0):
                continue
            return True
    return False


def _stub(a, d, obstacles, own, length=STUB, used=()):
    """Stub out of a terminal. Returns (point, escaped): escaped is True when the point is
    outside the terminal's own symbol box, so the A* may treat that box as a wall."""
    best = None
    tries = []
    for k in (length, length * 0.75, length * 0.5, STUB, STUB / 2.0, STUB / 4.0):
        if k > EPS and all(abs(k - t) > 1e-6 for t in tries):
            tries.append(k)
    for k in tries:
        p = (a[0] + d[0] * k, a[1] + d[1] * k)
        if any(_hits_rect(a, p, r) for i, r in enumerate(obstacles) if i != own):
            continue
        if _overlaps_used(a, p, used):
            continue        # a longer stub here would lie on top of a wire already drawn
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
    lanes = (0.0, LANE, 2.0 * LANE, 3.0 * LANE)
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
    for (p, q), _flag in used:
        # a lane beside every wire already routed, so a parallel run can sit LANE away from it
        # instead of detouring or piling onto it; only near this wire, or the grid explodes
        if not (lo_x <= p[0] <= hi_x and lo_y <= p[1] <= hi_y):
            continue
        if abs(p[1] - q[1]) < EPS:
            for k in (LANE, 2.0 * LANE):
                ys.add(p[1] + k)
                ys.add(p[1] - k)
            # a stub end is the only corner to go round instead of crossing it, so it is a
            # coordinate; adding every wire end instead doubles the grid for nothing
            if _flag == 'stub':
                for v in (p[0], q[0]):
                    xs.add(v)
                    xs.add(v - LANE)
                    xs.add(v + LANE)
        elif abs(p[0] - q[0]) < EPS:
            for k in (LANE, 2.0 * LANE):
                xs.add(p[0] + k)
                xs.add(p[0] - k)
            if _flag == 'stub':
                for v in (p[1], q[1]):
                    ys.add(v)
                    ys.add(v - LANE)
                    ys.add(v + LANE)
    if obstacles:
        xs.add(min(r[0] for r in obstacles) - 2 * margin)
        xs.add(max(r[2] for r in obstacles) + 2 * margin)
        ys.add(min(r[1] for r in obstacles) - 2 * margin)
        ys.add(max(r[3] for r in obstacles) + 2 * margin)
    # keep the grid near the wire: lanes from every box and every routed wire would otherwise
    # grow the search without ever being used on a sheet this size
    span = 300.0
    xs = {v for v in xs if lo_x - span <= v <= hi_x + span}
    ys = {v for v in ys if lo_y - span <= v <= hi_y + span}
    xs.add(start[0]); xs.add(end[0])
    ys.add(start[1]); ys.add(end[1])
    return sorted(xs), sorted(ys)


def route_ex(a, b, a_dir, b_dir, obstacles, used, grid=5.0, margin=6.0, bend=BEND,
             a_stub=None, b_stub=None):
    """Plan a path. Returns (points, ok, reason); ok False means the L-shape fallback."""
    a = (float(a[0]), float(a[1]))
    b = (float(b[0]), float(b[1]))
    da = _unit(a_dir)
    db = _unit(b_dir)
    obstacles = [tuple(float(v) for v in r) for r in obstacles]
    # a used item is (segment, flag): flag 'stub' marks the short run out of a terminal, which
    # another wire pays much more to cross so a fan keeps its order
    norm = []
    for item in used:
        if len(item) == 2 and not isinstance(item[1], (tuple, list)):
            seg, flag = item[0], item[1]          # (segment, flag), flag may be None
        else:
            seg, flag = item, None                # a bare segment
        norm.append((((float(seg[0][0]), float(seg[0][1])),
                      (float(seg[1][0]), float(seg[1][1]))), flag))
    used = norm
    seg_index = _SegIndex()
    for seg, flag in used:
        seg_index.add(seg, flag)

    if abs(a[0] - b[0]) < EPS or abs(a[1] - b[1]) < EPS:
        # a straight run stays straight unless a box is in the way or another wire already
        # runs along it; crossing another wire is left alone, the straight run is what it costs.
        # the first and last margin mm are the terminal itself, so they are not tested
        clear = True
        trimmed = _trim(a, b, margin)
        if trimmed is not None:
            clear = not any(_hits_rect(trimmed[0], trimmed[1], r) for r in obstacles)
        free = True
        for s, _flag in used:
            rel = _relation(a, b, s)
            if rel is not None and rel[0] == 'overlap':
                free = False
                break
            # shadowing a routed wire is what puts two runs on one trunk, but a brief pass-by
            # near a terminal is not a trunk: only a long shadow makes the straight run give way
            if rel is not None and rel[0] == 'cross' and _flag == 'stub':
                free = False        # cutting across a fan stub: go round it instead
                break
            if rel is None and _near(a, b, s, LANE) > SHADOW_MIN:
                free = False
                break
        if clear and free:
            return ([a, b], True, 'straight')

    own_a = next((i for i, r in enumerate(obstacles) if _inside(a, r)), -1)
    own_b = next((i for i, r in enumerate(obstacles) if _inside(b, r)), -1)
    la = STUB if a_stub is None else float(a_stub)
    lb = STUB if b_stub is None else float(b_stub)
    sa, esc_a = _stub(a, da, obstacles, own_a, la, used)
    sb, esc_b = _stub(b, db, obstacles, own_b, lb, used)
    # a box may not be entered at all unless its own terminal could not leave it
    wall_a = -1 if esc_a else own_a
    wall_b = -1 if esc_b else own_b

    xs, ys = _coords(sa, sb, obstacles, grid, margin, used)
    ix = {v: i for i, v in enumerate(xs)}
    iy = {v: j for j, v in enumerate(ys)}
    si, sj = ix[sa[0]], iy[sa[1]]
    gi, gj = ix[sb[0]], iy[sb[1]]
    dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))

    # The last leg into a terminal is its stub, drawn by every wire that ends there. A wire may
    # join that stub anywhere along it, not only at its far end: forcing every wire onto the one
    # stub-end point makes them queue for a single node and detour around each other, which is
    # what a 12-point path into a terminal 970 mm away looks like.
    goals = {(gi, gj)}
    span = None                                  # (axis, lo, hi) of the stub, for the heuristic
    if abs(sb[1] - b[1]) < EPS and abs(sb[0] - b[0]) > EPS:      # stub along x
        lo, hi = sorted((sb[0], b[0]))
        goals = set((i, gj) for i, x in enumerate(xs) if lo - EPS <= x <= hi + EPS)
        span = (0, lo, hi)
    elif abs(sb[0] - b[0]) < EPS and abs(sb[1] - b[1]) > EPS:    # stub along y
        lo, hi = sorted((sb[1], b[1]))
        goals = set((gi, j) for j, y in enumerate(ys) if lo - EPS <= y <= hi + EPS)
        span = (1, lo, hi)
    if not goals:
        goals = {(gi, gj)}

    def h_to_goal(x, y):
        if span is None:
            return abs(x - xs[gi]) + abs(y - ys[gj])
        if span[0] == 0:                         # stub along x: fixed y, x may be anywhere on it
            return abs(y - ys[gj]) + max(0.0, span[1] - x, x - span[2])
        return abs(x - xs[gi]) + max(0.0, span[1] - y, y - span[2])

    rect_index = _RectIndex(obstacles)

    def blocked(p, q):
        # the A* runs from stub to stub, both outside their boxes, so neither endpoint box may
        # be entered at all; only the a->sa and sb->b stubs touch a box, and those are not A*.
        # boxes are inflated by HARD_CLEAR: a wire that close to a symbol reads as touching it
        if HARD_CLEAR <= EPS:
            for i in rect_index.near((p, q)):
                if i == wall_a or i == wall_b:
                    continue
                if _hits_rect(p, q, obstacles[i]):
                    return True
            return False
        for i in rect_index.near((p, q), HARD_CLEAR):
            if i == wall_a or i == wall_b:
                continue
            r = obstacles[i]
            if _hits_rect(p, q, (r[0] - HARD_CLEAR, r[1] - HARD_CLEAR,
                                 r[2] + HARD_CLEAR, r[3] + HARD_CLEAR)):
                return True
        return False

    def near_pt(pt, t, k=STUB):
        return abs(pt[0] - t[0]) <= k and abs(pt[1] - t[1]) <= k

    def is_junction(seg, lo, hi):
        # free only where the other wire ends on the same terminal this wire ends on. The shared
        # run has to hold that terminal - then the two wires are one approach into it - or sit
        # wholly inside its stub zone. Riding a long run that only starts at a terminal and
        # leaves it is not free.
        for t in (a, b):
            if not _touches(seg, t):
                continue
            if _run_holds(lo, hi, t):
                return True
            if near_pt(lo, t) and near_pt(hi, t):
                return True
        return False

    # cells that come within CLEAR_AT of a box: an edge outside all of them pays nothing, which
    # is most edges, and that is what keeps this check out of the A* hot loop
    near_cells = set()
    for r in obstacles:
        for key in rect_index.keys(((r[0] - CLEAR_AT, r[1] - CLEAR_AT),
                                    (r[2] + CLEAR_AT, r[3] + CLEAR_AT))):
            near_cells.add(key)

    cell = CELL

    def cell_of(pt):
        return (int(math.floor(pt[0] / cell)), int(math.floor(pt[1] / cell)))

    def wire_cost(p, q):
        c = 0.0
        # three O(1) cell lookups instead of a range query: most edges are nowhere near a box
        if (near_cells and (cell_of(p) in near_cells or cell_of(q) in near_cells or
                            cell_of(((p[0] + q[0]) / 2.0, (p[1] + q[1]) / 2.0)) in near_cells)):
            for i in rect_index.near((p, q), CLEAR_AT):
                if i == wall_a or i == wall_b:
                    continue
                g = _gap_seg_rect(p, q, obstacles[i])
                if EPS < g < CLEAR_AT:
                    c += CLEAR_COST   # this close to a symbol reads as touching at page scale
        for s, flag in seg_index.near((p, q), NEAR_GAP):
            rel = _relation(p, q, s)
            if rel is None:
                c += NEAR * _near(p, q, s, NEAR_GAP)
                continue
            if rel[0] == 'cross':
                c += STUB_CROSS if flag == 'stub' else CROSS
                continue
            lo, hi = rel[2]
            if is_junction(s, lo, hi):
                continue       # two wires meeting at one terminal: a node
            c += OVERLAP * rel[1]
        return c

    def overlaps_used(p, q, allow_stub=False):
        for s, flag in seg_index.near((p, q)):
            rel = _relation(p, q, s)
            if rel is not None and rel[0] == 'overlap':
                lo, hi = rel[2]
                if is_junction(s, lo, hi):
                    continue
                # riding another wire's terminal stub is the same kind of node as a junction:
                # both wires start at a terminal of this wire's own ends
                # a shared stub is a node only inside the junction zone: past 2 * STUB the two
                # wires are drawn on top of each other, and that is an overlap whatever the
                # terminal says. Three wires sharing one 30 mm run was exactly this.
                if (allow_stub and flag == 'stub' and
                        _stub_share_ok(lo, hi, 2.0 * max(STUB, la, lb)) and
                        (_touches(s, a, 2.0) or _touches(s, b, 2.0))):
                    continue
                return True
        return False

    def search(strict, allow_stub=False, max_pops=MAX_POPS):
        """A* from the start stub to the end stub.

        strict refuses any overlap outright. Overlap is not a price to trade against crossings or
        clearance: two wires drawn on top of each other are a defect whatever else the path
        saves. The loose pass is only a backstop for a sheet where no strict path exists.
        """
        start = (si, sj, dirs.index(da))
        best = {start: 0.0}
        prev = {}
        heap = [(0.0, 0.0, start)]
        goal = None
        nx, ny = len(xs), len(ys)
        pops = 0
        edge_cache = {}
        while heap:
            pops += 1
            if pops > max_pops:
                return None, {}
            _f, cost, state = heapq.heappop(heap)
            if cost > best.get(state, float('inf')) + EPS:
                continue
            i, j, d = state
            if (i, j) in goals and dirs[d] != db:
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
                ekey = (i, j, ni, nj) if (i, j) <= (ni, nj) else (ni, nj, i, j)
                got = edge_cache.get(ekey)
                if got is None:
                    got = (blocked(p, q), wire_cost(p, q))
                    edge_cache[ekey] = got
                if got[0]:
                    continue
                if strict and overlaps_used(p, q, allow_stub):
                    continue
                step = abs(q[0] - p[0]) + abs(q[1] - p[1])
                if step < EPS:
                    continue
                nc = cost + step + got[1] + (0.0 if nd == d else bend)
                ns = (ni, nj, nd)
                if nc + EPS < best.get(ns, float('inf')):
                    best[ns] = nc
                    prev[ns] = state
                    h = h_to_goal(xs[ni], ys[nj])
                    heapq.heappush(heap, (nc + h, nc, ns))
        return goal, prev

    LAST['strict'] = 'strict'
    goal, prev = search(True, True)     # strict, but an exact terminal stub may be shared
    if goal is None:
        goal, prev = search(False)
        LAST['strict'] = 'loose'
    if goal is None:
        return (_l_shape(a, b), False, 'no path')
    chain = [goal]
    while chain[-1] in prev:
        chain.append(prev[chain[-1]])
    chain.reverse()
    pts = [a, sa] + [(xs[i], ys[j]) for (i, j, _d) in chain[1:]]
    pts += [sb, b] if (chain[-1][0], chain[-1][1]) == (gi, gj) else [b]
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
    'balanced': {'NEAR': 12.0, 'LANE': 8.0, 'CROSS': 120.0, 'OVERLAP': 2000.0},
    'fewer-crossings': {'NEAR': 0.0, 'LANE': 6.0, 'CROSS': 400.0, 'OVERLAP': 2000.0},
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


def _stub_share_ok(lo, hi, zone=None):
    """True when a run shared with another wire's stub is short enough to be a node.

    Two wires that end on the same terminal share the drawn stub leaving it; that is a junction.
    The zone is twice the terminal's real stub length (fan length when the terminal is fanned),
    so a long fanned stub gets the room it needs and a plain 14 mm stub keeps 28 mm. route_ex
    passes that zone; the default is the plain 2 * STUB. A run longer than the zone is two wires
    drawn on top of each other, whatever terminal it starts at."""
    if zone is None:
        zone = 2.0 * STUB
    return abs(hi[0] - lo[0]) + abs(hi[1] - lo[1]) <= zone


def route(a, b, a_dir, b_dir, obstacles, used, grid=5.0, margin=6.0, a_stub=None, b_stub=None):
    """Orthogonal path from a to b: first point a, last point b.

    obstacles: (xmin, ymin, xmax, ymax) boxes of all devices, including both endpoints.
    used: ((x1, y1), (x2, y2)) axis-aligned segments of wires already routed.
    Falls back to the old L-shape when nothing is found; LAST says which happened.
    """
    pts, ok, reason = route_ex(a, b, a_dir, b_dir, obstacles, used, grid, margin,
                               a_stub=a_stub, b_stub=b_stub)
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


FAN = True          # fan the stubs of a multi-terminal block
FAN_MAX = 12        # at most this many distinct stub lengths (no ties: ties stack)
FAN_TYPES = ('plc', 'vfd', 'block')   # DeviceType substrings that get fanned
FAN_MIN_TERMS = 6   # a face with this many terminals fans whatever its DeviceType says
FAN_COUNT_WHOLE_DEVICE = False   # True counts the device's terminals instead of one side's


def _wants_fan(device, count=0):
    """Fan this face's stubs? A FanStubs property wins, then the terminal count, then the type.

    count is how many terminals leave on this side: a block with FAN_MIN_TERMS or more terminals
    on one side fans whatever its DeviceType says. The count is per side on purpose. Counting the
    whole device instead fans every 8-terminal contactor and overload, and on the reversing demo
    that costs more than it saves (2 pairs/2.5 mm of overlap and 23 crossings become 2 pairs/60 mm
    and 27). Terminals spread around a symbol's own leads leave in different directions anyway, so
    the type rule is what covers a block there.
    """
    flag = getattr(device, 'FanStubs', None)
    if flag is not None:
        return bool(flag)
    if count >= FAN_MIN_TERMS:
        return True
    kind = str(getattr(device, 'DeviceType', '') or '').lower()
    return any(t in kind for t in FAN_TYPES)


def _terminal_pos(device, name):
    """Where one terminal sits. Its own call so the fan logic can be tested without FreeCAD."""
    from . import core
    return core.terminal_position(device, name)


def fan_lengths(device, rect, arrivals=None):
    """Stub length per terminal of one device: distinct lengths a step apart for terminals that
    leave in the same direction, so a multi-terminal block fans out instead of stacking its
    stubs on top of each other.

    arrivals maps a terminal to (y, x) of the far end of its wire. Where it is known, the face is
    ordered by where each wire comes from: the wire whose far end is lowest - the one arriving
    from below - gets the longest stub, so it turns at the outermost lane and passes the other
    terminals' stubs on the outside instead of cutting across them. The wire arriving from above
    gets the shortest stub and turns in close to the block.
    """
    out = {}
    if not FAN:
        return out
    groups = {}
    order = {}
    where = {}
    for index, name in enumerate(list(getattr(device, 'Terminals', None) or [])):
        try:
            p = _terminal_pos(device, name)
        except Exception:
            continue
        where[name] = (p.x, p.y)
        d = exit_dir(rect, (p.x, p.y))
        groups.setdefault(d, []).append(name)
        order[name] = index
    for d, names in groups.items():
        count = len(order) if FAN_COUNT_WHOLE_DEVICE else len(names)
        if not _wants_fan(device, count):
            continue
        names.sort(key=lambda n: order.get(n, 0))     # terminal order, as the block lists them
        if arrivals and FAN_ORDER_BY_ARRIVAL:
            def arrival_key(n):
                far = arrivals.get(n)
                return (-(far[0] if far is not None else where[n][1]), order.get(n, 0))
            names.sort(key=arrival_key)
        step = _fan_step([where[n] for n in names], d)
        for rank, name in enumerate(names):
            out[name] = STUB + min(rank, FAN_MAX) * step
    return out


def _fan_step(points, d):
    """Stub step for one face, mm.

    A dense face needs a step as wide as its terminal pitch, or the fan turns back into a stack:
    with terminals 10 mm apart and an 8 mm step the wire from the top terminal turns at x+14 and
    crosses the 22 mm stub of the terminal below it. Faces whose terminals are already further
    apart than FAN_DENSE_PITCH keep LANE, so a contactor's main poles do not grow 70 mm stubs.
    """
    if len(points) < 3:
        return LANE
    cross = 1 if abs(d[0]) > EPS else 0        # a horizontal exit means the face runs along y
    vals = sorted(p[cross] for p in points)
    gaps = [vals[i + 1] - vals[i] for i in range(len(vals) - 1) if vals[i + 1] - vals[i] > EPS]
    if not gaps:
        return LANE
    pitch = min(gaps)
    if pitch > FAN_DENSE_PITCH:
        return LANE
    return max(LANE, FAN_STEP_MIN, min(FAN_STEP_MAX, pitch))


_CTX = {'doc': None, 'stamp': None, 'rects': [], 'index': {}, 'labels': [], 'fan': {},
        'arrivals': {}}


def clear_cache():
    """Drop the per-document cache of boxes, labels and fan lengths. Call it after moving or
    adding symbols; the cache also rebuilds itself when a device position changes."""
    _CTX.update({'doc': None, 'stamp': None, 'rects': [], 'index': {}, 'labels': [], 'fan': {},
                 'arrivals': {}})


def _stamp(doc):
    """Cheap fingerprint of the document: object identity and device position."""
    out = []
    for o in doc.Objects:
        p = getattr(o, 'Position', None)
        try:
            out.append((id(o), round(p.x, 1), round(p.y, 1)))
        except Exception:
            out.append((id(o), 0.0, 0.0))
    return tuple(out)


def _ctx(doc):
    """Per-document cache: device boxes, their index, label boxes and fan lengths.

    Every wire used to rescan the whole document for boxes and label boxes, which is what made
    a gallery sheet take minutes. The cache is rebuilt when the object list or a device position
    changes, so moving a symbol is picked up on the next wire.
    """
    st = _stamp(doc)
    if _CTX['doc'] is doc and _CTX['stamp'] == st:
        return _CTX
    found = boxes(doc)
    _CTX.update({'doc': doc, 'stamp': st,
                 'rects': [r for _o, r in found],
                 'index': {id(o): i for i, (o, _r) in enumerate(found)},
                 'labels': [], 'fan': {}, 'arrivals': _arrivals(doc)})
    try:
        _CTX['labels'] = text_boxes(doc)
    except Exception:
        _CTX['labels'] = []
    return _CTX


def _arrivals(doc):
    """terminal -> (y, x) of the far end of its wire, for every wired terminal.

    This is what lets a fan order its stubs by the direction the wire arrives from.
    """
    out = {}
    for o in doc.Objects:
        if not hasattr(o, 'SourceTerminal'):
            continue
        sd = getattr(o, 'SourceDevice', None)
        td = getattr(o, 'TargetDevice', None)
        if sd is None or td is None:
            continue
        try:
            a = _terminal_pos(sd, o.SourceTerminal)
            b = _terminal_pos(td, o.TargetTerminal)
        except Exception:
            continue
        out.setdefault(id(sd), {})[o.SourceTerminal] = (b.y, b.x)
        out.setdefault(id(td), {})[o.TargetTerminal] = (a.y, a.x)
    return out


def _fan(device, rect, ctx=None):
    """fan_lengths for one device, cached per document, ordered by where its wires come from."""
    if ctx is None:
        return fan_lengths(device, rect)
    key = (id(device), tuple(rect))
    got = ctx['fan'].get(key)
    if got is None:
        got = fan_lengths(device, rect, ctx['arrivals'].get(id(device)))
        ctx['fan'][key] = got
    return got


def _marks(segs, a_fan=False, b_fan=False):
    """Mark a wire's first and last segment as a fan stub when that terminal is fanned.

    Only a fanned terminal's stub is marked: a plain wire's short first run is not a fan, and
    charging other wires to cross it turned the PLC demo from 7 crossings into 12.
    """
    if len(segs) < 3:
        return [(s, None) for s in segs]
    return ([(segs[0], 'stub' if a_fan else None)] + [(s, None) for s in segs[1:-1]] +
            [(segs[-1], 'stub' if b_fan else None)])


def _ends(obj, rects, index, ctx=None):
    from . import core
    a = core.terminal_position(obj.SourceDevice, obj.SourceTerminal)
    b = core.terminal_position(obj.TargetDevice, obj.TargetTerminal)
    pa, pb = (a.x, a.y), (b.x, b.y)
    ia = index.get(id(obj.SourceDevice), -1)
    ib = index.get(id(obj.TargetDevice), -1)
    da = exit_dir(rects[ia], pa) if ia >= 0 else (1.0, 0.0)
    db = exit_dir(rects[ib], pb) if ib >= 0 else (-1.0, 0.0)
    la = _fan(obj.SourceDevice, rects[ia], ctx).get(obj.SourceTerminal, STUB) if ia >= 0 else STUB
    lb = _fan(obj.TargetDevice, rects[ib], ctx).get(obj.TargetTerminal, STUB) if ib >= 0 else STUB
    return pa, pb, da, db, ia, ib, la, lb


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


def _pt_seg(pt, seg):
    """Distance from a point to an axis-aligned segment."""
    (x1, y1), (x2, y2) = seg
    dx = max(min(x1, x2) - pt[0], 0.0, pt[0] - max(x1, x2))
    dy = max(min(y1, y2) - pt[1], 0.0, pt[1] - max(y1, y2))
    return math.hypot(dx, dy)


def _gap_seg_rect(p, q, r):
    """Distance from an axis-aligned segment to a box; 0 when they touch or overlap."""
    (x1, y1), (x2, y2) = p, q
    lo_x, hi_x = min(x1, x2), max(x1, x2)
    lo_y, hi_y = min(y1, y2), max(y1, y2)
    dx = max(r[0] - hi_x, 0.0, lo_x - r[2])
    dy = max(r[1] - hi_y, 0.0, lo_y - r[3])
    return math.hypot(dx, dy)


def clearance_pairs(doc, limit=MIN_CLEAR):
    """Everything closer than limit mm that is not already touching: one row per pair.

    Rows are ('wire', idA, idB, mm) for two wires, and ('box', wireId, tag, mm) for a wire and a
    symbol box. Pairs that meet at a terminal are left out: that is a junction, not a defect.
    """
    found = []
    wires = []
    for o in doc.Objects:
        shape = getattr(o, 'Shape', None)
        if hasattr(o, 'SourceTerminal') and shape is not None and not shape.isNull():
            sg = segments(shape)
            if sg:
                wires.append((o.WireId, sg, (sg[0][0], sg[-1][1])))
    for i in range(len(wires)):
        wa, sa, ea = wires[i]
        for j in range(i + 1, len(wires)):
            wb, sb, eb = wires[j]
            if _junction(ea, eb):
                continue
            best = None
            for s1 in sa:
                for s2 in sb:
                    if _relation(s1[0], s1[1], s2) is not None:
                        continue                    # touching or crossing, counted elsewhere
                    d = min(_pt_seg(s1[0], s2), _pt_seg(s1[1], s2),
                            _pt_seg(s2[0], s1), _pt_seg(s2[1], s1))
                    if best is None or d < best:
                        best = d
            if best is not None and best < limit:
                found.append(('wire', wa, wb, round(best, 2)))
    for o, r in boxes(doc):
        for wid, sg, ends in wires:
            own = (id(getattr(o, 'SourceDevice', None)), id(getattr(o, 'TargetDevice', None)))
            if id(o) in own:
                continue                            # a wire starts or ends on this symbol
            best = None
            for seg in sg:
                g = _gap_seg_rect(seg[0], seg[1], r)
                if g > EPS and (best is None or g < best):
                    best = g
            if best is not None and best < limit:
                found.append(('box', wid, str(getattr(o, 'Tag', '')), round(best, 2)))
    return found


def _junction(e1, e2, k=2 * STUB):
    """True when the two wires end on the same terminal, so their meeting is a node."""
    for t in e1:
        for u in e2:
            if abs(t[0] - u[0]) <= k and abs(t[1] - u[1]) <= k:
                return True
    return False


def _label_zone(la, lb):
    """How far from a terminal its labels stop being obstacles: the drawn stub plus one lane.

    A fanned terminal draws a longer stub, and the wire legitimately occupies that space, so the
    labels beside it are not in the way for the first stub + LANE mm either."""
    return max(2.0 * STUB, la + LANE, lb + LANE)


def _labels(doc, a, b, k=2 * STUB):
    """Label boxes that are not at either terminal of this wire."""
    fn = TEXT_BOXES
    if fn is None:
        return []
    try:
        found = _ctx(doc)['labels'] if fn is text_boxes else fn(doc)
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
    ctx = _ctx(doc)
    rects = ctx['rects']
    if not rects:
        return None
    index = ctx['index']
    pa, pb, da, db, ia, ib, la, lb = _ends(obj, rects, index, ctx)
    used = []
    for o in doc.Objects:
        if o is obj:
            break
        shape = getattr(o, 'Shape', None)
        if hasattr(o, 'SourceTerminal') and shape is not None and not shape.isNull():
            oa = index.get(id(getattr(o, 'SourceDevice', None)), -1)
            ob = index.get(id(getattr(o, 'TargetDevice', None)), -1)
            used += _marks(segments(shape),
                           oa >= 0 and bool(_fan(o.SourceDevice, rects[oa], ctx)),
                           ob >= 0 and bool(_fan(o.TargetDevice, rects[ob], ctx)))
    return route_ex(pa, pb, da, db, rects + _labels(doc, pa, pb, _label_zone(la, lb)),
                    used, a_stub=la, b_stub=lb)


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
    """Route every wire in document order; return one report row per wire.

    The document is scanned once for boxes and label boxes (see _ctx), and each wire's stubs are
    marked in the used list so the next wire keeps clear of the fan at a dense face.
    """
    import time
    ctx = _ctx(doc)
    rects = ctx['rects']
    index = ctx['index']
    done = []
    report = []
    for obj in [o for o in doc.Objects if hasattr(o, 'SourceTerminal')]:
        if not obj.SourceDevice or not obj.TargetDevice:
            continue
        t0 = time.time()
        pa, pb, da, db, ia, ib, la, lb = _ends(obj, rects, index, ctx)
        fa = ia >= 0 and bool(_fan(obj.SourceDevice, rects[ia], ctx))
        fb = ib >= 0 and bool(_fan(obj.TargetDevice, rects[ib], ctx))
        pts, ok, reason = route_ex(pa, pb, da, db,
                                   rects + _labels(doc, pa, pb, _label_zone(la, lb)), done,
                                   a_stub=la, b_stub=lb)
        _write(obj, pts)
        obj.Validation = 'Logical connection only' if ok else 'Route fallback'
        done += _marks(segments(obj.Shape), fa, fb)
        inside = 0
        for (p, q) in zip(pts, pts[1:]):
            for i, r in enumerate(rects):
                if i not in (ia, ib) and _hits_rect(p, q, r):
                    inside += 1
        cl = clean(pts)
        report.append({'wire': obj.WireId, 'points': len(cl), 'routed': ok,
                       'reason': reason, 'segments_in_foreign_box': inside,
                       'ms': round((time.time() - t0) * 1000.0, 1),
                       'strict': LAST.get('strict', 'strict'),
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

    def shared_terminal(w1, w2, lo, hi):
        # a shared run is a node when it runs into a terminal both wires end on: the two wires are
        # drawn as one approach into that terminal. Any other shared run is two wires on top of
        # each other. The tolerance is the terminal itself, not a zone: three wires into one
        # terminal share however long their common approach is drawn.
        e1, e2 = ends.get(w1), ends.get(w2)
        if e1 is None or e2 is None:
            return False
        for t in e1:
            for u in e2:
                if abs(t[0] - u[0]) <= 0.5 and abs(t[1] - u[1]) <= 0.5:
                    if _run_holds(lo, hi, t):
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
                junc = shared_terminal(segs[i][0], segs[j][0], lo, hi)
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
