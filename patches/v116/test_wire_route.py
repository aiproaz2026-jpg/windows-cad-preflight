# -*- coding: utf-8 -*-
"""Unit tests for wire_route.route(). Plain Python, no FreeCAD, no dependencies.
Run: python test_wire_route.py     (exit 0 = all passed) GPL-3.0-or-later."""
import sys
import wire_route as W

FAILS = []
CHECKS = [0]


def check(name, cond, detail=''):
    CHECKS[0] += 1
    if cond:
        print('PASS %s' % name)
    else:
        print('FAIL %s %s' % (name, detail))
        FAILS.append(name)


def orthogonal(pts):
    for p, q in zip(pts, pts[1:]):
        if abs(p[0] - q[0]) > 1e-9 and abs(p[1] - q[1]) > 1e-9:
            return False
    return True


def enters(pts, boxes, skip):
    for p, q in zip(pts, pts[1:]):
        for i, r in enumerate(boxes):
            if i in skip:
                continue
            if W._hits_rect(p, q, r):
                return i
    return None


def overlaps_any(pts, used):
    for p, q in zip(pts, pts[1:]):
        for s in used:
            rel = W._relation(p, q, s)
            if rel is not None and rel[0] == 'overlap':
                return True
    return False


# 1. a clear straight run stays straight
A = (0.0, 0.0, 100.0, 60.0)
B = (400.0, 0.0, 500.0, 60.0)
pts = W.route((100, 30), (400, 30), (1, 0), (-1, 0), [A, B], [])
check('straight stays straight', pts == [(100, 30), (400, 30)], str(pts))

# 2. a box between the two terminals is avoided
C = (200.0, -40.0, 300.0, 40.0)
pts = W.route((100, 30), (400, 30), (1, 0), (-1, 0), [A, C, B], [])
check('avoids the body box', orthogonal(pts) and enters(pts, [A, C, B], (0, 2)) is None, str(pts))
check('avoids: first and last point', pts[0] == (100, 30) and pts[-1] == (400, 30), str(pts))
check('avoids: more than the L', len(pts) >= 4, str(pts))

# 3. a wire already routed on the same line is not overlapped
used = [((150, 30), (250, 30))]
pts = W.route((100, 30), (400, 30), (1, 0), (-1, 0), [A, B], used)
check('no overlap with a used wire', orthogonal(pts) and not overlaps_any(pts, used), str(pts))
check('no overlap: endpoints kept', pts[0] == (100, 30) and pts[-1] == (400, 30), str(pts))

# 4. two parallel wires between the same pair of boxes end up on different lines
first = W.route((100, 30), (400, 30), (1, 0), (-1, 0), [A, B], [])
second = W.route((100, 45), (400, 45), (1, 0), (-1, 0), [A, B], [((p, q) for p, q in [])] and [])
used1 = list(zip(first, first[1:]))
second = W.route((100, 45), (400, 45), (1, 0), (-1, 0), [A, B], used1)
check('second parallel wire clears the first', orthogonal(second) and not overlaps_any(second, used1), str(second))

# 5. nothing reachable -> the old L shape and the flag
# the target is sealed in a ring of walls that are not its own symbol
walls = [(250.0, 150.0, 350.0, 160.0), (250.0, 240.0, 350.0, 250.0),
         (250.0, 160.0, 260.0, 240.0), (340.0, 160.0, 350.0, 240.0)]
pts = W.route((0, 0), (300, 200), (1, 0), (-1, 0), walls, [])
check('fallback returns the L shape', pts == [(0, 0), (300, 0), (300, 200)], str(pts))
check('fallback is flagged', W.LAST['ok'] is False, str(W.LAST))

# 6. a wire from a bottom terminal leaves downward and comes back around a circle
circ = (-35.0, -35.0, 35.0, 35.0)
other = (300.0, -300.0, 420.0, -200.0)
pts = W.route((0, -35), (300, -250), (0, -1), (-1, 0), [circ, other], [])
check('bottom terminal leaves downward', pts[1] == (0, -49), str(pts))
check('bottom route clears both boxes', orthogonal(pts) and enters(pts, [circ, other], (0, 1)) is None, str(pts))

# 7. determinism: same input twice gives the same path
p1 = W.route((100, 30), (400, 30), (1, 0), (-1, 0), [A, C, B], [])
p2 = W.route((100, 30), (400, 30), (1, 0), (-1, 0), [A, C, B], [])
check('deterministic', p1 == p2, str((p1, p2)))

# 8. the installed hook must accept whatever plan() returns and write the shape.
#    plan() returns a 3-tuple (points, ok, reason); a wrapper that unpacks two of them raises
#    ValueError on every wire and FreeCAD silently keeps the old shape.
try:
    from DeltaEngineering import wire_route as WP
    from DeltaEngineering import core as CORE
except Exception:
    WP = None
    CORE = None
if WP is None:
    print('SKIP hook test: DeltaEngineering package not importable here')
else:
    class FakeWire(object):
        Shape = None
        Validation = None

    saved_plan = WP.plan
    try:
        WP.plan = lambda obj, doc=None: ([(0.0, 0.0), (50.0, 0.0), (50.0, 30.0)], True, 'routed')
        installed = WP.install()
        obj = FakeWire()
        raised = None
        try:
            CORE.Connection.execute(None, obj)
        except Exception as exc:
            raised = exc
        check('hook runs without raising on a 3-tuple plan', raised is None, repr(raised))
        check('hook writes the shape', obj.Shape is not None, str(obj.Shape))
        check('hook sets Validation', obj.Validation == 'Logical connection only', str(obj.Validation))
        check('install is idempotent', WP.install() == 0, 'second install returned 1')
        check('uninstall restores', WP.uninstall() == 1, 'uninstall returned 0')
    finally:
        WP.plan = saved_plan

# 8b. crossing another wire's stub is what makes a fan look stacked: a straight run through it
#     gives way, while a plain crossing is still allowed
stub_seg = ((250.0, 10.0), (250.0, 100.0))
plain = W.route((100, 30), (400, 30), (1, 0), (-1, 0), [A, B], [stub_seg])
check('a plain crossing keeps the straight run', plain == [(100, 30), (400, 30)], str(plain))
guarded = W.route((100, 30), (400, 30), (1, 0), (-1, 0), [A, B], [(stub_seg, 'stub')])
cuts = [s for s in zip(guarded, guarded[1:])
        if (W._relation(s[0], s[1], stub_seg) or ('',))[0] == 'cross']
check('a straight run does not cut across a stub', not cuts, str(guarded))
check('going round the stub still reaches both ends',
      guarded[0] == (100, 30) and guarded[-1] == (400, 30) and orthogonal(guarded), str(guarded))

# 8c. a short pass-by is not a trunk: a straight run shadowing a wire for less than SHADOW_MIN
#     stays straight, which is the crossings the last revision paid for nothing
short_shadow = [((150.0, 32.0), (150.0 + W.SHADOW_MIN - 10.0, 32.0))]
pts = W.route((100, 30), (400, 30), (1, 0), (-1, 0), [A, B], short_shadow)
check('a short shadow keeps the straight run', pts == [(100, 30), (400, 30)], str(pts))
long_shadow = [((150.0, 32.0), (150.0 + W.SHADOW_MIN + 20.0, 32.0))]
pts = W.route((100, 30), (400, 30), (1, 0), (-1, 0), [A, B], long_shadow)
check('a long shadow still gives way', pts != [(100, 30), (400, 30)] and orthogonal(pts), str(pts))

# 9. fan-out: a face with many terminals fans even when its DeviceType is unknown, and the
#    stub lengths follow the order the block lists its terminals, not their geometric order.
class FakeTerm(object):
    def __init__(self, x, y):
        self.x, self.y = x, y


class FakeDevice(object):
    def __init__(self, names, positions, kind='Generic schematic symbol', fan=None):
        self.Terminals = list(names)
        self.DeviceType = kind
        self._pos = dict(zip(names, positions))
        if fan is not None:
            self.FanStubs = fan


saved_pos = W._terminal_pos
W._terminal_pos = lambda device, name: FakeTerm(*device._pos[name])
try:
    rect = (0.0, -45.0, 60.0, 45.0)
    names = ['T%d' % i for i in range(1, 7)]
    # terminals sit in reverse geometric order: T1 is the lowest, so ranking by y would hand
    # the longest stub to the wrong end of the block
    ys = [40.0 - 12.0 * i for i in range(6)]
    dev = FakeDevice(names, [(200.0, y) for y in ys])
    got = W.fan_lengths(dev, rect)
    check('fan: 6 terminals on one face fan with an unknown DeviceType', len(got) == 6, str(got))
    seq = [got[n] for n in names]
    check('fan: lengths follow terminal order, not geometry',
          seq == sorted(seq) and len(set(seq)) == 6 and seq[0] == W.STUB, str(seq))
    steps = {round(seq[i + 1] - seq[i], 6) for i in range(len(seq) - 1)}
    check('fan: one constant step, at least LANE, distinct for every terminal',
          len(steps) == 1 and min(steps) >= W.LANE, str(seq))

    few = FakeDevice(names[:5], [(200.0, ys[i]) for i in range(5)])
    check('fan: 5 terminals of an unknown type stay unfanned',
          W.fan_lengths(few, rect) == {}, str(W.fan_lengths(few, rect)))

    plc = FakeDevice(names[:2], [(200.0, 20.0), (200.0, -20.0)], kind='PLC block (illustr.)')
    check('fan: a PLC type fans a two-terminal face',
          len(W.fan_lengths(plc, rect)) == 2, str(W.fan_lengths(plc, rect)))

    # the count rule is per side: 6 terminals spread 3/3 over two faces stay stock, because they
    # already leave in different directions and fanning every 8-terminal contactor hurt the
    # reversing demo
    split = FakeDevice(names, [(200.0, 30.0), (200.0, 0.0), (200.0, -30.0),
                              (-200.0, 30.0), (-200.0, 0.0), (-200.0, -30.0)])
    check('fan: 6 terminals spread 3/3 over two faces stay unfanned',
          W.fan_lengths(split, rect) == {}, str(W.fan_lengths(split, rect)))

    # a dense face gets a step as wide as its pitch; a loose face keeps LANE
    dense = FakeDevice(names[:3], [(200.0, 0.0), (200.0, -10.0), (200.0, -20.0)],
                       kind='PLC block (illustr.)')
    gd = W.fan_lengths(dense, rect)
    check('fan: a 10 mm pitch face gets a 12 mm step',
          [gd[n] for n in names[:3]] == [14.0, 26.0, 38.0], str([gd[n] for n in names[:3]]))
    mid = FakeDevice(names[:3], [(200.0, 0.0), (200.0, -14.0), (200.0, -28.0)],
                     kind='PLC block (illustr.)')
    gm = W.fan_lengths(mid, rect)
    check('fan: a 14 mm pitch face is dense and steps 14 mm',
          [gm[n] for n in names[:3]] == [14.0, 28.0, 42.0], str([gm[n] for n in names[:3]]))
    loose = FakeDevice(names[:3], [(200.0, 0.0), (200.0, -18.0), (200.0, -36.0)],
                       kind='PLC block (illustr.)')
    gl = W.fan_lengths(loose, rect)
    check('fan: an 18 mm pitch face keeps the 8 mm step',
          [gl[n] for n in names[:3]] == [14.0, 22.0, 30.0], str([gl[n] for n in names[:3]]))

    saved_whole = W.FAN_COUNT_WHOLE_DEVICE
    W.FAN_COUNT_WHOLE_DEVICE = True
    try:
        check('fan: counting the whole device fans the split 3/3 block',
              len(W.fan_lengths(split, rect)) == 6, str(W.fan_lengths(split, rect)))
    finally:
        W.FAN_COUNT_WHOLE_DEVICE = saved_whole

    off = FakeDevice(names, [(200.0, y) for y in ys], fan=False)
    check('fan: FanStubs False wins over the terminal count',
          W.fan_lengths(off, rect) == {}, str(W.fan_lengths(off, rect)))

    on = FakeDevice(names[:2], [(200.0, 20.0), (200.0, -20.0)], fan=True)
    check('fan: FanStubs True fans a two-terminal face',
          len(W.fan_lengths(on, rect)) == 2, str(W.fan_lengths(on, rect)))
finally:
    W._terminal_pos = saved_pos

# 9. a shared stub is a node only inside the junction zone (2 * STUB). Three wires sharing one
#    30 mm run started at a common terminal was accepted before this cap and showed up as three
#    overlap pairs in CI on the control panel.
check('stub share: 20 mm at a terminal is still a node', W._stub_share_ok((0, 0), (20, 0)))
check('stub share: exactly 2 * STUB is allowed', W._stub_share_ok((0, 0), (2 * W.STUB, 0)))
check('stub share: 30 mm is not a node on a plain 14 mm stub', not W._stub_share_ok((0, 0), (30, 0)))
check('stub share: 30 mm is a node on a 30 mm fanned stub',
      W._stub_share_ok((0, 0), (30, 0), 2 * 30.0))

# 9b. the same run on the wire itself: a 30 mm stub to ride puts the wire on its own lane
stub30 = ((100.0, 0.0), (130.0, 0.0))
pts = W.route((100, 0), (400, 0), (1, 0), (-1, 0), [], [(stub30, 'stub')])
def longest_share(pts, used):
    best = 0.0
    for p, q in zip(pts, pts[1:]):
        for seg in used:
            rel = W._relation(p, q, seg)
            if rel is not None and rel[0] == 'overlap':
                best = max(best, rel[1])
    return best


check('stub share: a 30 mm stub is not ridden past the junction zone',
      longest_share(pts, [stub30]) <= 2 * W.STUB + 1e-6, str(pts))
check('stub share: the detour keeps both ends',
      pts[0] == (100, 0) and pts[-1] == (400, 0) and orthogonal(pts), str(pts))
stub20 = ((100.0, 0.0), (120.0, 0.0))
check('stub share: the junction zone itself stays allowed',
      W._stub_share_ok(stub20[0], stub20[1]))

# 9c. the geometry CI measured, reproduced on a document: three wires on one 30 mm run
class _P(object):
    def __init__(self, x, y):
        self.x, self.y = x, y


class _V(object):
    def __init__(self, pt):
        self.Point = _P(pt[0], pt[1])


class _E(object):
    def __init__(self, p, q):
        self.Vertexes = [_V(p), _V(q)]


class _Shape(object):
    def __init__(self, pts):
        self.Edges = [_E(p, q) for p, q in zip(pts, pts[1:])]

    def isNull(self):
        return False


class _Wire(object):
    def __init__(self, wid, pts):
        self.WireId, self.Shape, self.SourceTerminal = wid, _Shape(pts), True


class _Doc(object):
    def __init__(self, wires):
        self.Objects = wires


fan_out = _Doc([
    _Wire('W7', [(0, 0), (30, 0), (30, 40)]),
    _Wire('W19', [(0, 0), (30, 0), (30, -40)]),
    _Wire('W22', [(0, 0), (30, 0), (40, 0), (40, 80)]),
])
hits = W.overlaps(fan_out)
check('shared 30 mm run: three pairs, all of them the node into A1.M',
      len(hits) == 3 and all(h[3] for h in hits), str(hits))
check('shared 30 mm run: each pair is 30 mm',
      all(abs(h[2] - 30.0) < 1e-6 for h in hits), str(hits))

short_out = _Doc([
    _Wire('W1', [(0, 0), (20, 0), (20, 40)]),
    _Wire('W2', [(0, 0), (20, 0), (20, -40)]),
])
short_hits = W.overlaps(short_out)
check('shared 20 mm run: still one pair of 20 mm', len(short_hits) == 1 and
      abs(short_hits[0][2] - 20.0) < 1e-6, str(short_hits))

# 10. three wires through one 20 mm corridor: the later wires take a lane, nobody is drawn on top
corridor = [(150, -120, 350, -10), (150, 10, 350, 120)]
cpairs = [((100, 0), (400, 0)), ((100, -40), (400, -40)), ((100, -80), (400, -80))]
cpaths, cused = [], []
for a, b in cpairs:
    p = W.route(a, b, (1, 0), (-1, 0), corridor, list(cused))
    cpaths.append(p)
    cused.extend(zip(p, p[1:]))
check('corridor: the clear wire stays straight', cpaths[0] == [(100, 0), (400, 0)], str(cpaths[0]))
shared = []
for i in range(len(cpaths)):
    for j in range(i + 1, len(cpaths)):
        for p, q in zip(cpaths[i], cpaths[i][1:]):
            for s2 in zip(cpaths[j], cpaths[j][1:]):
                rel = W._relation(p, q, s2)
                if rel is not None and rel[0] == 'overlap':
                    shared.append((i, j, round(rel[1], 1)))
check('corridor: three wires through one gap, no overlap between them', not shared, str(shared))
check('corridor: every wire still reaches both ends',
      all(p[0] == a and p[-1] == b for p, (a, b) in zip(cpaths, cpairs)), str(cpaths))

# 11. lane pitch: a run beside another wire keeps SPACE_MIN where the sheet leaves room, and the
#     tight pitch is only a fallback. _seg_gap is the distance the clean pass reasons about.
check('gap: two parallel segments 2 mm apart', abs(W._seg_gap((0, 0), (10, 0), ((0, 2), (10, 2))) - 2.0) < 1e-9)
check('gap: touching segments read 0', W._seg_gap((0, 0), (10, 0), ((5, 0), (5, 10))) == 0.0)
check('gap: separated in x as well', abs(W._seg_gap((0, 0), (10, 0), ((14, 3), (20, 3))) - 5.0) < 1e-9)

used_one = [((200.0, 0.0), (300.0, 0.0))]
pts = W.route((100, 2), (400, 2), (1, 0), (-1, 0), [], used_one)
best = min(W._seg_gap(p, q, used_one[0]) for p, q in zip(pts, pts[1:]))
check('lane pitch: open space keeps 4 mm from the wire beside it', best >= W.SPACE_MIN - 1e-6, str(pts))

tight = [(100.0, 3.0, 400.0, 4.0), (100.0, -4.0, 400.0, -3.0)]     # a 6 mm corridor
pts = W.route((100, 2), (400, 2), (1, 0), (-1, 0), tight, used_one)
check('lane pitch: a corridor too narrow for 4 mm still routes',
      pts[0] == (100, 2) and pts[-1] == (400, 2) and orthogonal(pts), str(pts))
check('lane pitch: the tight fallback is reported, not hidden', W.LAST.get('draft') in ('tight', 'clean'),
      str(W.LAST))

# 12. crowded face: the gap in front of a face decides the lane pitch its wires ask for.
#     _corridor measures that gap and _face_pitch turns it into a pitch. No FreeCAD here, so the
#     terminal table is stood in for.
class _V(object):
    def __init__(self, x, y):
        self.x, self.y = x, y


class _Dev(object):
    def __init__(self, names):
        self.Terminals = names


_terms = {'L+': _V(0, 40), 'M': _V(0, 45), 'I0.0': _V(0, 50),
          'I0.1': _V(0, 55), 'Q0.0': _V(0, 60), 'Q0.1': _V(0, 65)}
_real_term = W._terminal_pos
W._terminal_pos = lambda device, name: _terms[name]
face = (0.0, 30.0, 100.0, 75.0)          # the block, terminals on its left face
wide = [(-300.0, 0.0, -220.0, 100.0)]    # a neighbour 220 mm away
narrow = [(-20.0, 0.0, -20.0, 100.0)]    # a neighbour 20 mm away

check('length: a two-leg path adds its legs',
      abs(W._length([(0, 0), (10, 0), (10, 5)]) - 15.0) < 1e-9)
check('corridor: an empty sheet reads as the limit',
      W._corridor(face, (0, 50), (-1, 0), []) == 400.0)
check('corridor: a neighbour 220 mm away reads 220',
      abs(W._corridor(face, (0, 50), (-1, 0), wide) - 220.0) < 1e-9,
      str(W._corridor(face, (0, 50), (-1, 0), wide)))
check('corridor: a box 20 mm in front reads 20',
      abs(W._corridor(face, (0, 50), (-1, 0), narrow) - 20.0) < 1e-9)
check('corridor: a box beside the exit line is not counted',
      abs(W._corridor(face, (0, 50), (-1, 0), [(-20.0, 200.0, -20.0, 300.0)]) - 400.0) < 1e-9)

pitch, gap = W._face_pitch(_Dev(list(_terms)), face, (0, 50), (-1, 0), wide, None)
check('pitch: a wide gap keeps the 4 mm lane', pitch == W.SPACE_MIN, str((pitch, gap)))
pitch, gap = W._face_pitch(_Dev(list(_terms)), face, (0, 50), (-1, 0), narrow, None)
check('pitch: six terminals in a 20 mm gap ask for less than 4 mm', pitch < W.SPACE_MIN, str((pitch, gap)))
check('pitch: and never tighter than the floor', pitch >= W.TIGHT_PITCH - 1e-9, str((pitch, gap)))
check('pitch: the gap it measured is reported', abs(gap - 20.0) < 1e-9, str(gap))
W._terminal_pos = _real_term

tight2 = [(100.0, 3.0, 400.0, 4.0), (100.0, -4.0, 400.0, -3.0)]
pts, ok, reason = W.route_ex((100, 2), (400, 2), (1, 0), (-1, 0), tight2, [],
                             space_min=W.TIGHT_PITCH)
check('route_ex: a wire can be given its own space_min', pts[0] == (100, 2) and pts[-1] == (400, 2),
      str(pts))
check('route_ex: the tight pitch is floored, not taken as asked',
      W.route_ex((100, 2), (400, 2), (1, 0), (-1, 0), [], [], space_min=0.1)[0][0] == (100, 2))

check('wrap: a clean path may not be more than a third longer',
      abs(W.WRAP_MAX - 1.35) < 1e-9, str(W.WRAP_MAX))
pts = W.route((100, 2), (400, 2), (1, 0), (-1, 0), [], used_one)
check('wrap: a wire that never entered the clean pass carries no wrap flag',
      'wrap' not in W.LAST, str(sorted(W.LAST)))
check('wrap: a wire that never needed the clean pass reports no wrap',
      W.LAST.get('wrap', '') in ('', 'clean', 'kept'), str(W.LAST.get('wrap')))

# 13. wide lanes: the clean pass tries LANE (8 mm) first and falls back to SPACE_MIN (4 mm), and
#     a clean path may never add crossings to buy that lane.
check('lanes: LANE is wider than SPACE_MIN, and SPACE_MIN wider than the tight pitch',
      W.LANE > W.SPACE_MIN > W.TIGHT_PITCH, str((W.LANE, W.SPACE_MIN, W.TIGHT_PITCH)))
pts = W.route((100, 2), (400, 2), (1, 0), (-1, 0), [], used_one)
check('lanes: a routed wire reports which lane it settled on',
      W.LAST.get('lane', 0) in (0, 0.0, W.SPACE_MIN, W.LANE), str(W.LAST.get('lane')))
check('lanes: the clean pass reports whether a crossing blocked it',
      W.LAST.get('cross', '') in ('', 'kept'), str(W.LAST.get('cross')))
check('lanes: the clean pass is on, so the wide tier is reachable', W.CLEAN_PASS is True)

crowded = [((100.0, 4.0), (400.0, 4.0)), ((100.0, 8.0), (400.0, 8.0)),
           ((100.0, 12.0), (400.0, 12.0))]
pts = W.route((100, 0), (400, 0), (1, 0), (-1, 0), [], crowded)
gaps = [W._seg_gap(p, q, s) for p, q in zip(pts, pts[1:]) for s in crowded]
check('lanes: a wire beside a bundle keeps a lane, not a hairline',
      min(gaps) >= W.SPACE_MIN - 1e-6, str(min(gaps)))

# 14. the clean pass is reported per wire, and LAST does not leak from one wire to the next.
#     A wire that never entered the clean pass must not carry the previous wire's lane or wrap.
used_bundle = [((100.0, 0.0), (400.0, 0.0)), ((100.0, 2.0), (400.0, 2.0)),
               ((100.0, 4.0), (400.0, 4.0))]
W.route((100, 6), (400, 6), (1, 0), (-1, 0), [], used_bundle)
crowded_wire = dict(W.LAST)
W.route((100, 300), (400, 300), (1, 0), (-1, 0), [], [])
open_wire = dict(W.LAST)
check('report: a wire beside a bundle reports the crowding it started with',
      crowded_wire.get('crowded_before_mm') is not None, str(crowded_wire))
check('report: the crowding after the clean pass is reported too',
      crowded_wire.get('crowded_after_mm') is not None, str(crowded_wire))
check('report: the tiers tried are named, with the reason for each',
      isinstance(crowded_wire.get('clean_tiers'), str), str(crowded_wire.get('clean_tiers')))
check('report: the pops the clean pass spent are reported',
      isinstance(crowded_wire.get('clean_pops'), int), str(crowded_wire.get('clean_pops')))
check('report: an open wire does not inherit the crowded wire flags',
      'lane' not in open_wire and 'wrap' not in open_wire, str(open_wire))
check('report: an open wire reports no crowding of its own',
      open_wire.get('crowded_before_mm') == open_wire.get('crowded_after_mm'),
      str((open_wire.get('crowded_before_mm'), open_wire.get('crowded_after_mm'))))

# 15. a shared terminal approach is not crowding, and the clean pass has a budget.
used_line = [((100.0, 0.0), (400.0, 0.0))]
W.route((100, 2), (400, 2), (1, 0), (-1, 0), [], used_line, a_stub=200.0, b_stub=200.0)
check('stub: a run inside a long terminal stub is not counted as crowding',
      W.LAST.get('crowded_before_mm') == 0.0, str(W.LAST.get('crowded_before_mm')))
W.route((100, 2), (400, 2), (1, 0), (-1, 0), tight, used_line)
check('stub: a run squeezed beside a wire outside any stub is counted',
      (W.LAST.get('crowded_before_mm') or 0.0) > 0.0, str(W.LAST.get('crowded_before_mm')))
check('budget: the clean pass has a per-document cap', 0 < W.CLEAN_POPS <= W.CLEAN_TOTAL,
      str((W.CLEAN_POPS, W.CLEAN_TOTAL)))
check('narrow: the clean pass triggers on a run shorter than a lane, not on 4 mm crowding',
      0 < W.NARROW_MIN < 1000, str(W.NARROW_MIN))

# 16. the nudge pass: it moves a band apart, and it refuses what would break the drawing.
def band(offsets):
    # each wire rises at its own x, runs along the band, and drops back down: the way a real
    # bundle leaves a face, so the approach and return runs are not on top of each other
    out = []
    for i, y in enumerate(offsets):
        x = 10.0 + 10.0 * i
        out.append((None, [(x, 100.0), (x, y), (400.0 + x, y), (400.0 + x, 200.0)], -1, -1))
    return out


def pitch_of(paths):
    ys = sorted(p[1][1][1] for p in paths)
    return min(b - a for a, b in zip(ys, ys[1:])) if len(ys) > 1 else 0.0


band3 = band([300.0, 302.0, 304.0])
check('spread: a 2 mm band is the case the pass exists for', pitch_of(band3) == 2.0,
      str(pitch_of(band3)))
info = W.spread_paths(band3, [])
check('spread: a band in open space is nudged apart',
      pitch_of(band3) >= W.SPACE_MIN - 0.01, str(pitch_of(band3)))
check('spread: the nudge is reported per wire', sum(i['moves'] for i in info) > 0, str(info))
check('spread: the nudged wires keep their ends and their bends',
      all(p[1][0] == (10.0 + 10.0 * i, 100.0) and len(p[1]) == 4 for i, p in enumerate(band3)),
      str([p[1] for p in band3]))
check('spread: a nudge only lengthens the neighbours, so the run stays square',
      all(W._orthogonal(p[1]) for p in band3), 'not orthogonal')

blocked = band([300.0, 302.0, 304.0])
wall = [(20.0, 306.0, 390.0, 340.0)]
before = [list(p[1]) for p in blocked]
info = W.spread_paths(blocked, wall)
check('spread: a nudge into a symbol box is refused',
      blocked[2][1][1][1] == 304.0, str(blocked[2][1]))
check('spread: a refused nudge leaves the wire that was refused where it was',
      blocked[2][1][1][1] == 304.0 and blocked[2][1] == before[2], str(blocked[2][1]))
check('spread: the wire with room on the open side still moves', blocked[0][1][1][1] < 300.0,
      str(blocked[0][1]))
check('spread: a refused nudge is counted', sum(i['refused'] for i in info) > 0, str(info))

# a vertical standing right where the lower run would be nudged to
crossed = [(None, [(10.0, 100.0), (10.0, 300.0), (410.0, 300.0), (410.0, 200.0)], -1, -1),
           (None, [(20.0, 100.0), (20.0, 302.0), (420.0, 302.0), (420.0, 200.0)], -1, -1),
           (None, [(200.0, 280.0), (200.0, 299.9)], -1, -1)]
before = [list(p[1]) for p in crossed]
info = W.spread_paths(crossed, [])
def _crosses(pts, seg):
    return any((W._relation(p, q, seg) or ('',))[0] == 'cross'
               for p, q in zip(pts, pts[1:]))


check('spread: no nudge is bought with a crossing',
      not any(_crosses(p[1], ((200.0, 280.0), (200.0, 299.9))) for p in crossed),
      str([p[1] for p in crossed]))
check('spread: the crossing guard is not vacuous - the band still moved somewhere',
      sum(i['moves'] for i in info) > 0, str(info))


class _Tagged(object):
    def __init__(self, tag):
        self.Tag = tag


_b = W._blocker([(0.0, 100.0), (0.0, 300.0)],
                [(20.0, 320.0, 60.0, 360.0), (-50.0, 0.0, -10.0, 40.0)],
                (), [_Tagged('K1'), _Tagged('A1')])
check('blocked: the box a wire is hemmed against is named with its gap',
      _b[0] == 'K1' and abs(_b[1] - 28.3) < 0.1, str(_b))
check('blocked: the wire\'s own boxes are not blamed',
      W._blocker([(0.0, 100.0), (0.0, 300.0)], [(0.0, 100.0, 5.0, 300.0)],
                 (0,), [_Tagged('own')]) is None, 'own box reported')


class _Wire(object):
    def __init__(self, wid):
        self.WireId = wid


_near = [( _Wire('W9'), [(0.0, 302.0), (400.0, 302.0)], -1, -1)]
check('blocked: a wire is hemmed by its neighbour, not by a box 400 mm away',
      W._hemmed([(0.0, 300.0), (400.0, 300.0)],
                [(20.0, 700.0, 60.0, 760.0)], (), [_Tagged('K1')], _near)
      == 'wire W9:2.0',
      W._hemmed([(0.0, 300.0), (400.0, 300.0)],
                [(20.0, 700.0, 60.0, 760.0)], (), [_Tagged('K1')], _near))
check('blocked: a nearer box wins over a further wire',
      W._hemmed([(0.0, 300.0), (400.0, 300.0)],
                [(20.0, 301.0, 60.0, 340.0)], (), [_Tagged('K1')], _near)
      == 'K1:1.0',
      W._hemmed([(0.0, 300.0), (400.0, 300.0)],
                [(20.0, 301.0, 60.0, 340.0)], (), [_Tagged('K1')], _near))

# 17. the reserved ring around a dense face: the room its own wires need to fan out in.
class _Dev(object):
    def __init__(self, name):
        self.Name = name


class _TermWire(object):
    def __init__(self, a, b):
        self.SourceTerminal = 'X'
        self.SourceDevice = a
        self.TargetDevice = b


_dev = _Dev('A1')
_far = _Dev('far')
_ctx_face = {'rects': [(0.0, 0.0, 20.0, 20.0)], 'objs': [_dev]}


class _Doc(object):
    def __init__(self, objs):
        self.Objects = objs


_six = _Doc([_TermWire(_dev, _far) for _ in range(6)])
_five = _Doc([_TermWire(_dev, _far) for _ in range(5)])
_rings = W._corridors(_six, _ctx_face)
check('reserve: a face with six wired terminals gets a ring around it',
      len(_rings) == 1 and _rings[0][0] == (-48.0, -48.0, 68.0, 68.0), str(_rings))
check('reserve: a face with five does not', W._corridors(_five, _ctx_face) == [], 'a ring appeared')
check('reserve: a wire ending on the face may cross its own ring',
      W._reserved_for(_rings, (0,)) == [], str(W._reserved_for(_rings, (0,))))
check('reserve: a wire with no business there may not',
      W._reserved_for(_rings, (-1,)) == [(-48.0, -48.0, 68.0, 68.0)], 'own ring not reserved')

_ring = [(-40.0, -40.0, 60.0, 60.0)]
# a wall with two gaps: the upper gap is the short way and it runs through the ring
_wall = [(0.0, -200.0, 20.0, -100.0), (0.0, -60.0, 20.0, 0.0), (0.0, 40.0, 20.0, 200.0)]
_ring2 = [(-100.0, -10.0, 100.0, 50.0)]
_plain = W.route((-100.0, 20.0), (200.0, 20.0), (1, 0), (-1, 0), _wall, [])
_res = W.route_ex((-100.0, 20.0), (200.0, 20.0), (1, 0), (-1, 0), _wall, [], reserved=_ring2)
check('reserve: without the ring the long wire takes the short gap through the band',
      len(_plain) == 2, str(_plain))
check('reserve: with the ring it takes the far gap instead',
      _res[1] and min(p[1] for p in _res[0]) < -60.0, str(_res[0]))
check('reserve: going round is not paid for by crossing the wire\'s own path',
      W._orthogonal(_res[0]), 'not orthogonal')

print('')
print('%d checks, %d failed' % (CHECKS[0], len(FAILS)))
sys.exit(1 if FAILS else 0)
