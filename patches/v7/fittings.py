# SPDX-License-Identifier: GPL-3.0-or-later
"""Generic illustrative pump-station fittings with ports, port snapping,
continuity check and quantity takeoff.

SCOPE: original generic geometry only. Not a manufacturer catalog, not a flange
standard, no pressure rating, no hydraulic or pump-selection calculation.
A matching outer diameter at two ports means geometric size continuity only. It
does NOT imply pressure, material, standard or gasket compatibility.
"""
import math
import FreeCAD as App
import Part
from .core import positive

SCOPE_AR = 'هندسة عامة توضيحية، ليست كتالوج مصنّع ولا معيار شفات. تطابق المقاس لا يعني توافق الضغط أو المعيار.'
SCOPE_EN = ('Generic illustrative geometry. Not a manufacturer catalog or flange standard. '
            'Matching port diameter is geometric continuity only, not pressure or standards compatibility.')
KINDS = {
    'reducer': 'مخفّض متحد المحور',
    'flange': 'شفة عامة',
    'gate_valve': 'محبس بوابة عام',
    'ball_valve': 'محبس كروي عام',
    'check_valve': 'صمام عدم رجوع عام',
    'pump': 'مضخة طرد مركزي عامة (غلاف تقريبي)',
    'pipe': 'ماسورة مستقيمة بمنفذين',
    'elbow90': 'كوع 90 درجة عام',
}
SNAP_TOL = 0.01  # mm
DIR_TOL = 1e-6


def _x():
    return App.Vector(1, 0, 0)


def _hollow(od, wall, length, start, axis):
    return Part.makeCylinder(od / 2, length, start, axis).cut(
        Part.makeCylinder(od / 2 - wall, length, start, axis))


class GenericFitting:
    def __init__(self, obj, kind, od1, wall1, od2=None, wall2=None, length=None):
        if kind not in KINDS:
            raise ValueError('Unknown fitting kind')
        obj.addProperty('App::PropertyString', 'FittingKind', 'Fitting')
        for key in ('OuterDiameter', 'WallThickness', 'OuterDiameter2', 'WallThickness2', 'Length'):
            obj.addProperty('App::PropertyLength', key, 'Fitting')
        obj.addProperty('App::PropertyVectorList', 'PortCenters', 'Connections')
        obj.addProperty('App::PropertyVectorList', 'PortDirections', 'Connections')
        obj.addProperty('App::PropertyFloatList', 'PortOuterDiameters', 'Connections')
        obj.addProperty('App::PropertyString', 'Scope', 'Status')
        obj.addProperty('App::PropertyString', 'Validation', 'Status')
        obj.FittingKind = kind
        obj.OuterDiameter = od1
        obj.WallThickness = wall1
        obj.OuterDiameter2 = od2 if od2 else od1
        obj.WallThickness2 = wall2 if wall2 else wall1
        obj.Length = length if length else self.default_length(kind, od1)
        obj.Scope = SCOPE_AR + ' | ' + SCOPE_EN
        for key in ('PortCenters', 'PortDirections', 'PortOuterDiameters', 'Scope', 'Validation'):
            obj.setEditorMode(key, 1)
        obj.Proxy = self
        if App.GuiUp:
            obj.ViewObject.Proxy = 0

    @staticmethod
    def default_length(kind, od):
        return {'reducer': 2.0 * od, 'flange': 0.2 * od, 'gate_valve': 2.5 * od,
                'ball_valve': 2.2 * od, 'check_valve': 2.5 * od, 'pump': 4.0 * od, 'pipe': 1000.0, 'elbow90': 1.5 * od}[kind]

    def execute(self, obj):
        try:
            kind = obj.FittingKind
            od1 = positive(obj.OuterDiameter.Value, 'Outer diameter')
            w1 = positive(obj.WallThickness.Value, 'Wall thickness')
            od2 = positive(obj.OuterDiameter2.Value, 'Second outer diameter')
            w2 = positive(obj.WallThickness2.Value, 'Second wall thickness')
            length = positive(obj.Length.Value, 'Length')
            if w1 >= od1 / 2 or w2 >= od2 / 2:
                raise ValueError('Wall must be less than radius')
            x = _x()
            if kind == 'reducer':
                if abs(od1 - od2) < 1e-9:
                    raise ValueError('Reducer needs two different diameters')
                if length < 2 * abs(od1 - od2) / 2 * 2:
                    raise ValueError('Reducer too short for its diameter change')
                outer = Part.makeCone(od1 / 2, od2 / 2, length, App.Vector(), x)
                inner = Part.makeCone(od1 / 2 - w1, od2 / 2 - w2, length, App.Vector(), x)
                shape = outer.cut(inner)
                centers = [App.Vector(), App.Vector(length, 0, 0)]
                dirs = [App.Vector(-1, 0, 0), x]
                ods = [od1, od2]
            elif kind == 'pipe':
                shape = _hollow(od1, w1, length, App.Vector(), x)
                centers = [App.Vector(), App.Vector(length, 0, 0)]
                dirs = [App.Vector(-1, 0, 0), x]
                ods = [od1, od1]
            elif kind == 'elbow90':
                if length <= od1 / 2 + 1e-6:
                    raise ValueError('Bend radius must exceed half the outer diameter')
                rb = length
                a = App.Vector()
                mid = App.Vector(rb * math.sin(math.pi / 4), rb - rb * math.cos(math.pi / 4), 0)
                b = App.Vector(rb, rb, 0)
                path = Part.Wire(Part.Arc(a, mid, b).toShape())

                def swept(radius):
                    prof = Part.Wire(Part.makeCircle(radius, a, x))
                    return path.makePipeShell([prof], True, True)
                shape = swept(od1 / 2).cut(swept(od1 / 2 - w1))
                centers = [a, b]
                dirs = [App.Vector(-1, 0, 0), App.Vector(0, 1, 0)]
                ods = [od1, od1]
            elif kind == 'flange':
                fod = 1.6 * od1 + 20.0
                shape = Part.makeCylinder(fod / 2, length, App.Vector(), x).cut(
                    Part.makeCylinder(od1 / 2 - w1, length, App.Vector(), x))
                centers = [App.Vector(), App.Vector(length, 0, 0)]
                dirs = [App.Vector(-1, 0, 0), x]
                ods = [od1, od1]
            elif kind in ('gate_valve', 'ball_valve', 'check_valve'):
                if length < 1.5 * od1:
                    raise ValueError('Valve length must be at least 1.5 x outer diameter')
                r = od1 / 2
                body = Part.makeCylinder(r, length, App.Vector(), x)
                mid = App.Vector(length / 2, 0, 0)
                z = App.Vector(0, 0, 1)
                if kind == 'gate_valve':
                    body = body.fuse(Part.makeCylinder(0.45 * od1, 0.9 * od1, App.Vector(length / 2, 0, r - w1 / 2), z))
                    body = body.fuse(Part.makeCylinder(0.06 * od1, 1.9 * od1, App.Vector(length / 2, 0, r - w1 / 2), z))
                    body = body.fuse(Part.makeCylinder(0.6 * od1, 0.08 * od1, App.Vector(length / 2, 0, r + 1.8 * od1), z))
                elif kind == 'ball_valve':
                    body = body.fuse(Part.makeSphere(0.8 * od1, mid))
                    body = body.fuse(Part.makeBox(0.9 * od1, 0.12 * od1, 0.1 * od1,
                                                  App.Vector(length / 2, -0.06 * od1, 0.8 * od1 - 0.02 * od1)))
                else:
                    body = body.fuse(Part.makeCylinder(0.55 * od1, 0.8 * od1, App.Vector(length / 2, 0, r - w1 / 2), z))
                shape = body.cut(Part.makeCylinder(r - w1, length + 2, App.Vector(-1, 0, 0), x))
                centers = [App.Vector(), App.Vector(length, 0, 0)]
                dirs = [App.Vector(-1, 0, 0), x]
                ods = [od1, od1]
            else:  # pump
                if length < 3 * max(od1, od2):
                    raise ValueError('Pump casing length must be at least 3 x the larger port diameter')
                rc = 0.75 * max(od1, od2) + 40.0
                ln = od1
                xd = ln + length / 2
                zt = rc + od2
                solids = [Part.makeCylinder(od1 / 2, ln, App.Vector(), x),
                          Part.makeCylinder(rc, length, App.Vector(ln, 0, 0), x),
                          Part.makeCylinder(od2 / 2, zt, App.Vector(xd, 0, 0), App.Vector(0, 0, 1)),
                          Part.makeCylinder(0.55 * rc, 1.2 * length, App.Vector(ln + length, 0, 0), x)]
                body = solids[0]
                for s in solids[1:]:
                    body = body.fuse(s)
                bore1 = Part.makeCylinder(od1 / 2 - w1, ln + length / 2 + 1, App.Vector(-1, 0, 0), x)
                bore2 = Part.makeCylinder(od2 / 2 - w2, zt + 2, App.Vector(xd, 0, 0), App.Vector(0, 0, 1))
                shape = body.cut(bore1).cut(bore2)
                centers = [App.Vector(), App.Vector(xd, 0, zt)]
                dirs = [App.Vector(-1, 0, 0), App.Vector(0, 0, 1)]
                ods = [od1, od2]
            shape = shape.removeSplitter()
            if not shape.isValid() or len(shape.Solids) != 1:
                raise ValueError('Fitting must be one valid solid')
            obj.Shape = shape
            obj.PortCenters = centers
            obj.PortDirections = dirs
            obj.PortOuterDiameters = ods
            obj.Validation = 'Valid generic geometry. ' + SCOPE_EN
        except (ValueError, RuntimeError) as exc:
            obj.Shape = Part.Shape()
            obj.PortCenters = []
            obj.PortDirections = []
            obj.PortOuterDiameters = []
            obj.Validation = str(exc)


# ---------------------------------------------------------------- creation
def create_fitting(doc, kind, nps1, nps2=None, length=None):
    from .tube_library import PRESETS
    from .documents import add_to
    if nps1 not in PRESETS or (nps2 is not None and nps2 not in PRESETS):
        raise ValueError('Unknown nominal size')
    p1 = PRESETS[nps1]
    p2 = PRESETS[nps2] if nps2 else p1
    doc.openTransaction('Generic fitting: ' + kind)
    try:
        obj = doc.addObject('Part::FeaturePython', 'GenericFitting')
        obj.Label = KINDS[kind] + ' ' + nps1 + ('x' + nps2 if nps2 and nps2 != nps1 else '')
        GenericFitting(obj, kind, p1['od_mm'], p1['wall_mm'], p2['od_mm'], p2['wall_mm'], length)
        for key, val in (('SizePort1', 'NPS ' + nps1), ('SizePort2', 'NPS ' + (nps2 or nps1))):
            obj.addProperty('App::PropertyString', key, 'Dimensional provenance')
            setattr(obj, key, val)
            obj.setEditorMode(key, 1)
        add_to(doc, 'PipingSystem', obj)
        doc.recompute()
        if obj.Shape.isNull():
            raise ValueError(obj.Validation)
        if App.GuiUp:
            obj.ViewObject.ShapeColor = (0.25, 0.45, 0.75)
        doc.commitTransaction()
        return obj
    except Exception:
        doc.abortTransaction()
        doc.recompute()
        raise


# ------------------------------------------------------------------- ports
def ports(obj):
    """Global ports of an object: list of (center, unit direction, outer diameter)."""
    result = []
    if hasattr(obj, 'PortCenters') and hasattr(obj, 'PortDirections') and len(obj.PortCenters):
        pl = obj.getGlobalPlacement() if hasattr(obj, 'getGlobalPlacement') else obj.Placement
        ods = list(obj.PortOuterDiameters) if hasattr(obj, 'PortOuterDiameters') and len(obj.PortOuterDiameters) \
            else [obj.OuterDiameter.Value] * len(obj.PortCenters)
        for c, d, od in zip(obj.PortCenters, obj.PortDirections, ods):
            v = pl.Rotation.multVec(d)
            v.normalize()
            result.append((pl.multVec(c), v, float(od)))
    elif hasattr(obj, 'PortSource') and hasattr(obj, 'StartPoint') and hasattr(obj, 'EndPoint') and not obj.Shape.isNull():
        axis = obj.EndPoint - obj.StartPoint
        if axis.Length > 0:
            axis.normalize()
            od = obj.OuterDiameter.Value
            result.append((obj.StartPoint, App.Vector(-axis.x, -axis.y, -axis.z), od))
            result.append((obj.EndPoint, axis, od))
    return result


def port_objects(doc):
    return [o for o in doc.Objects if ports(o)]


def snap(doc, moving, mport, fixed, fport):
    """Place `moving` so its port mport meets fixed port fport, face to face.
    Refuses a diameter mismatch (geometric continuity only)."""
    if moving.Document != doc or fixed.Document != doc or moving == fixed:
        raise ValueError('Select two different objects in this document')
    if not isinstance(getattr(moving, 'Proxy', None), GenericFitting):
        raise ValueError('Only a generic fitting can be moved by snapping')
    if any(p.isDerivedFrom('App::Part') for p in moving.InListRecursive):
        raise ValueError('Fitting must stay at document root, outside Part containers')
    mp, fp = ports(moving), ports(fixed)
    if not (0 <= mport < len(mp)) or not (0 <= fport < len(fp)):
        raise ValueError('Invalid port index')
    mc, md, mod = mp[mport]
    fc, fd, fod = fp[fport]
    if abs(mod - fod) > 1e-6:
        raise ValueError('Port diameter mismatch: %.3f mm vs %.3f mm. Geometric continuity only, no compatibility implied.' % (mod, fod))
    target = App.Vector(-fd.x, -fd.y, -fd.z)
    rot = App.Rotation(md, target)
    old = moving.Placement
    new_rot = rot.multiply(old.Rotation)
    local_center = moving.PortCenters[mport]
    new_pos = fc - new_rot.multVec(local_center)
    doc.openTransaction('Snap fitting port to port')
    try:
        moving.Placement = App.Placement(new_pos, new_rot)
        doc.recompute()
        c2, d2, _ = ports(moving)[mport]
        if (c2 - fc).Length > SNAP_TOL or d2.dot(fd) > -1 + 1e-6:
            raise ValueError('Snap verification failed')
        doc.commitTransaction()
        return moving
    except Exception:
        doc.abortTransaction()
        doc.recompute()
        raise


# ------------------------------------------------------------- continuity
def check_continuity(doc, overlap_tol_mm3=1.0):
    """Pairs of ports within SNAP_TOL are connections; they must face each other
    and have equal diameter. Remaining ports are reported as open. Solids of
    objects that are not directly connected must not overlap."""
    items = []
    for o in port_objects(doc):
        for i, (c, d, od) in enumerate(ports(o)):
            items.append((o, i, c, d, od))
    connected, errors, used = [], [], set()
    for a in range(len(items)):
        for b in range(a + 1, len(items)):
            oa, ia, ca, da, oda = items[a]
            ob, ib, cb, db, odb = items[b]
            if oa == ob or (ca - cb).Length > SNAP_TOL:
                continue
            used.add(a)
            used.add(b)
            name = '%s.%d <-> %s.%d' % (oa.Name, ia, ob.Name, ib)
            if da.dot(db) > -1 + 1e-6:
                errors.append(name + ': ports do not face each other')
            elif abs(oda - odb) > 1e-6:
                errors.append(name + ': diameter mismatch %.3f vs %.3f mm' % (oda, odb))
            else:
                connected.append(name)
    open_ports = ['%s.%d' % (items[k][0].Name, items[k][1]) for k in range(len(items)) if k not in used]
    linked = {frozenset((x.split(' <-> ')[0].split('.')[0], x.split(' <-> ')[1].split('.')[0])) for x in connected}
    objs = port_objects(doc)
    for a in range(len(objs)):
        for b in range(a + 1, len(objs)):
            if frozenset((objs[a].Name, objs[b].Name)) in linked:
                continue
            if not objs[a].Shape.BoundBox.intersect(objs[b].Shape.BoundBox):
                continue
            vol = objs[a].Shape.common(objs[b].Shape).Volume
            if vol > overlap_tol_mm3:
                errors.append('Overlap %s / %s: %.1f mm3' % (objs[a].Name, objs[b].Name, vol))
    return {'connected': connected, 'open_ports': open_ports, 'errors': errors,
            'ok': not errors, 'scope': SCOPE_EN}


# ---------------------------------------------------------------- takeoff
def takeoff(doc):
    """Count fittings by kind and size; sum straight tube length by diameter."""
    rows = {}
    for o in doc.Objects:
        if isinstance(getattr(o, 'Proxy', None), GenericFitting) and not o.Shape.isNull() and o.FittingKind == 'pipe':
            key = ('tube', 'OD %.1f x %.2f mm' % (o.OuterDiameter.Value, o.WallThickness.Value), 'm')
            rows[key] = rows.get(key, 0.0) + o.Length.Value / 1000.0
        elif isinstance(getattr(o, 'Proxy', None), GenericFitting) and not o.Shape.isNull():
            size = o.SizePort1 if o.SizePort1 == o.SizePort2 else o.SizePort1 + ' x ' + o.SizePort2
            key = ('fitting', o.FittingKind, size)
            rows[key] = rows.get(key, 0) + 1
        elif hasattr(o, 'PortSource') and not o.Shape.isNull():
            key = ('tube', 'OD %.1f x %.2f mm' % (o.OuterDiameter.Value, o.WallThickness.Value), 'm')
            rows[key] = rows.get(key, 0.0) + o.CenterlineLength.Value / 1000.0
        elif o.TypeId == 'PartDesign::FeaturePython' and hasattr(o, 'SourcePath') and not o.Shape.isNull() \
                and hasattr(o, 'CenterlineLength'):
            key = ('tube', 'OD %.1f x %.2f mm' % (o.OuterDiameter.Value, o.WallThickness.Value), 'm')
            rows[key] = rows.get(key, 0.0) + o.CenterlineLength.Value / 1000.0
    out = []
    for (cls, a, b), n in sorted(rows.items()):
        if cls == 'fitting':
            out.append({'item': KINDS[a], 'kind': a, 'size': b, 'qty': n, 'unit': 'pcs'})
        else:
            out.append({'item': 'ماسورة مستقيمة', 'kind': 'tube', 'size': a, 'qty': round(n, 4), 'unit': b})
    return out


def takeoff_csv(doc, path):
    import csv
    rows = takeoff(doc)
    with open(path, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['# ' + SCOPE_AR])
        w.writerow(['# ' + SCOPE_EN])
        w.writerow(['item', 'kind', 'size', 'qty', 'unit'])
        for r in rows:
            w.writerow([r['item'], r['kind'], r['size'], r['qty'], r['unit']])
    return rows
