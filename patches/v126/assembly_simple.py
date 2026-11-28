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


def make_assembly(doc, part_a, part_b, joint_type='Revolute', axis='Z', point=None):
    """Return a dict with the assembly, the joint and the joint point. part_a is grounded."""
    JO = _jo()
    asm = doc.addObject('Assembly::AssemblyObject', 'Assembly')
    joints = asm.newObject('Assembly::JointGroup', 'Joints')
    for o in (part_a, part_b):
        asm.addObject(o)
    g = joints.newObject('App::FeaturePython', 'GroundedJoint')
    JO.GroundedJoint(g, part_a)
    names = list(JO.JointTypes)
    j = joints.newObject('App::FeaturePython', 'Joint')
    JO.Joint(j, names.index(joint_type))
    j.Reference1 = [part_a, ['Face1', 'Vertex1']]
    j.Reference2 = [part_b, ['Face1', 'Vertex1']]
    if point is None:
        point = part_b.Placement.Base
    rot = _axis_rotation(axis)
    # joint frame on part A at the chosen point (A is at identity unless moved), on part B at its own origin
    j.Placement1 = App.Placement(part_a.Placement.inverse().multVec(point), part_a.Placement.Rotation.inverted().multiply(rot))
    j.Placement2 = App.Placement(App.Vector(0, 0, 0), part_b.Placement.Rotation.inverted().multiply(rot))
    for p in ('Detach1', 'Detach2'):
        if hasattr(j, p):
            setattr(j, p, True)
    doc.recompute()
    r = asm.solve()
    doc.recompute()
    return {'assembly': asm, 'joint': j, 'solve_result': r, 'point': point}


def move(info, value):
    """Rotate (degrees) for Revolute, shift (mm) for Slider, about/along the joint's Z axis. Returns the solve code."""
    j = info['joint']; asm = info['assembly']
    if j.JointType == 'Slider':
        j.Offset2 = App.Placement(App.Vector(0, 0, float(value)), App.Rotation())
    else:
        j.Offset2 = App.Placement(App.Vector(0, 0, 0), App.Rotation(App.Vector(0, 0, 1), float(value)))
    r = asm.solve()
    asm.Document.recompute()
    return r
