"""Simple assembly helper on top of the bundled FreeCAD Assembly module. GPL-3.0-or-later.
Grounds the first part, joins a second part with one joint (revolute, slider or fixed), solves, and moves the
second part by a joint offset (rotation about the joint axis, or a shift along it). Kinematic positioning only:
no dynamics, no collision, no loads, no engineering validation."""
import os
import sys
import FreeCAD as App

JOINTS = {'Revolute': 'مفصل دوران', 'Slider': 'منزلق', 'Fixed': 'ثابت'}
AXES = {'Z': App.Vector(0, 0, 1), 'X': App.Vector(1, 0, 0), 'Y': App.Vector(0, 1, 0)}


def _jo():
    base = App.getResourceDir()
    for c in (os.path.join(base, 'Mod', 'Assembly'),):
        if os.path.isdir(c) and c not in sys.path:
            sys.path.append(c)
    import JointObject
    return JointObject


def _axis_rotation(axis):
    """Rotation that sends the joint's local Z axis to the chosen world axis."""
    return App.Rotation(App.Vector(0, 0, 1), AXES[axis])


def pick_reference(part, point, axis):
    """Pick [face, vertex] element names on a part: a planar face whose normal is parallel to the chosen world axis,
    and the vertex of that face closest to the requested point. Raises ValueError (Arabic message) if none."""
    sh = part.Shape
    ax = AXES[axis]
    best = None
    for i, f in enumerate(sh.Faces, 1):
        try:
            if f.Surface.TypeId != 'Part::GeomPlane':
                continue
            n = f.normalAt(0, 0)
        except Exception:
            continue
        if abs(abs(n.dot(ax)) - 1.0) > 1e-6:
            continue
        for v in f.Vertexes:
            d = (v.Point - point).Length
            if best is None or d < best[0] - 1e-9:
                vi = [k for k, vv in enumerate(sh.Vertexes, 1) if (vv.Point - v.Point).Length < 1e-7]
                if vi:
                    best = (d, 'Face%d' % i, 'Vertex%d' % vi[0])
    if best is None:
        raise ValueError('لا يوجد وجه مستوٍ عمودي على المحور %s في القطعة %s' % (axis, part.Label))
    return [best[1], best[2]], best[0]


def make_assembly(doc, part_a, part_b, joint_type='Revolute', axis='Z', point=None):
    """Return a dict with the assembly, the joint, the picked references and their distance to the point.
    part_a is grounded. The joint sits at the chosen face vertex of each part (the one closest to point)."""
    JO = _jo()
    if point is None:
        point = part_b.Placement.Base
    ra, da = pick_reference(part_a, point, axis)
    rb, db = pick_reference(part_b, point, axis)
    asm = doc.addObject('Assembly::AssemblyObject', 'Assembly')
    joints = asm.newObject('Assembly::JointGroup', 'Joints')
    for o in (part_a, part_b):
        asm.addObject(o)
    g = joints.newObject('App::FeaturePython', 'GroundedJoint')
    JO.GroundedJoint(g, part_a)
    names = list(JO.JointTypes)
    j = joints.newObject('App::FeaturePython', 'Joint')
    JO.Joint(j, names.index(joint_type))
    j.Reference1 = [part_a, ra]
    j.Reference2 = [part_b, rb]
    doc.recompute()
    r = asm.solve()
    doc.recompute()
    return {'assembly': asm, 'joint': j, 'solve_result': r, 'point': point, 'ref_a': ra, 'ref_b': rb, 'dist_a': da, 'dist_b': db}


def move(info, value):
    """Sign convention v128: the joint offset is applied negated so the result matches the value shown to the user (positive = counter-clockwise about the chosen axis, positive shift = along the chosen axis).
    Rotate (degrees) for Revolute, shift (mm) for Slider, about/along the joint's Z axis. Returns the solve code."""
    j = info['joint']; asm = info['assembly']
    if j.JointType == 'Slider':
        j.Offset2 = App.Placement(App.Vector(0, 0, -float(value)), App.Rotation())
    else:
        j.Offset2 = App.Placement(App.Vector(0, 0, 0), App.Rotation(App.Vector(0, 0, 1), -float(value)))
    r = asm.solve()
    asm.Document.recompute()
    return r
