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
box = (-1000.0, -1000.0, 1000.0, 1000.0)
pts = W.route((0, 0), (300, 200), (1, 0), (-1, 0), [box], [])
check('fallback returns the L shape', pts == [(0, 0), (300, 0), (300, 200)], str(pts))
check('fallback is flagged', W.LAST['ok'] is False, str(W.LAST))

# 6. a wire from a bottom terminal leaves downward and comes back around a circle
circ = (-35.0, -35.0, 35.0, 35.0)
other = (300.0, -300.0, 420.0, -200.0)
pts = W.route((0, -35), (300, -250), (0, -1), (-1, 0), [circ, other], [])
check('bottom terminal leaves downward', pts[1] == (0, -47), str(pts))
check('bottom route clears both boxes', orthogonal(pts) and enters(pts, [circ, other], (0, 1)) is None, str(pts))

# 7. determinism: same input twice gives the same path
p1 = W.route((100, 30), (400, 30), (1, 0), (-1, 0), [A, C, B], [])
p2 = W.route((100, 30), (400, 30), (1, 0), (-1, 0), [A, C, B], [])
check('deterministic', p1 == p2, str((p1, p2)))

print('')
print('%d checks, %d failed' % (CHECKS[0], len(FAILS)))
sys.exit(1 if FAILS else 0)
