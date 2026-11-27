"""Editable 3D pipe fittings (elbows, equal tee, concentric reducer, Class 150 flange). GPL-3.0-or-later.
Dimensions come from fittings_library.py (center-to-end, run/outlet, length H, flange table) and the
pipe outside diameter / SCH 40 wall table below (ASME B36.10, two agreeing sources).
Every dimension is an editable property. Nominal geometry only, no pressure rating or approval."""
import math
import FreeCAD as App
import Part
from . import fittings_library as FL

# ASME B36.10 outside diameter and SCH 40 wall, mm. Two sources agree on every value:
#  S1 https://www.skfitting.com/en/standard-hub/asme-b36-10-pipe-dimensions/
#  S2 https://pipedata.org/pipes/
PIPE_OD = {'1': 33.40, '1 1/4': 42.16, '1 1/2': 48.26, '2': 60.32, '2 1/2': 73.02, '3': 88.90, '3 1/2': 101.60, '4': 114.30}
WALL_SCH40 = {'1': 3.38, '1 1/4': 3.56, '1 1/2': 3.68, '2': 3.91, '2 1/2': 5.16, '3': 5.49, '3 1/2': 5.74, '4': 6.02}
PIPE_SOURCES = ['https://www.skfitting.com/en/standard-hub/asme-b36-10-pipe-dimensions/', 'https://pipedata.org/pipes/']
PIPE_NOTE = ('Pipe OD and default wall (SCH 40) from ASME B36.10 as printed by two sources. '
             'Wall is an editable default and is not part of the fitting tables.')
V = App.Vector

KINDS = ['elbow90lr', 'elbow90sr', 'elbow45', 'tee_eq', 'reducer', 'flange150']
NAMES = {'elbow90lr': 'كوع ٩٠° نصف قطر طويل', 'elbow90sr': 'كوع ٩٠° نصف قطر قصير', 'elbow45': 'كوع ٤٥°',
         'tee_eq': 'تي متساوي', 'reducer': 'مخفض متحد المحور', 'flange150': 'فلنجة كلاس ١٥٠'}


def presets(kind):
    if kind == 'reducer':
        return ['%s x %s' % k for k in FL.REDUCER_H]
    return list(FL.NPS_RANGE)


def _addp(obj, typ, name, grp, val=None):
    obj.addProperty(typ, name, grp)
    if val is not None:
        setattr(obj, name, val)


def _tube(ro, ri, p, d, h):
    o = Part.makeCylinder(ro, h, p, d)
    return o, Part.makeCylinder(ri, h, p, d)


def _arc(r, ang, base, axis, p0, dirv):
    c = Part.makeCircle(r, p0, dirv)
    return Part.Face(Part.Wire(c)).revolve(base, axis, ang)


def build_elbow(ro, ri, R, ang, t):
    """Pipe of outer ro / inner ri along a centerline: straight t, arc radius R by ang degrees, straight t."""
    out = []
    for r in (ro, ri):
        parts = []
        if t > 0:
            parts.append(Part.makeCylinder(r, t, V(0, 0, 0), V(1, 0, 0)))
        parts.append(_arc(r, ang, V(t, R, 0), V(0, 0, 1), V(t, 0, 0), V(1, 0, 0)))
        if t > 0:
            a = math.radians(ang)
            end = V(t + R * math.sin(a), R - R * math.cos(a), 0)
            parts.append(Part.makeCylinder(r, t, end, V(math.cos(a), math.sin(a), 0)))
        s = parts[0]
        for q in parts[1:]:
            s = s.fuse(q)
        out.append(s)
    return out[0].cut(out[1]).removeSplitter()


class Fitting3D(object):
    def __init__(self, obj, kind, preset):
        self.kind = kind
        _addp(obj, 'App::PropertyString', 'FittingKind', 'Fitting', kind)
        obj.setEditorMode('FittingKind', 1)
        _addp(obj, 'App::PropertyEnumeration', 'SizePreset', 'Fitting')
        obj.SizePreset = presets(kind)
        obj.SizePreset = preset
        self._fields(obj)
        self.load(obj, preset)
        obj.Proxy = self

    def _fields(self, obj):
        k = self.kind
        if k == 'reducer':
            for n in ('OuterDiameterLarge', 'WallLarge', 'OuterDiameterSmall', 'WallSmall', 'Length'):
                _addp(obj, 'App::PropertyLength', n, 'Dimensions')
        else:
            _addp(obj, 'App::PropertyLength', 'OuterDiameter', 'Dimensions')
            _addp(obj, 'App::PropertyLength', 'Wall', 'Dimensions')
        if k.startswith('elbow'):
            _addp(obj, 'App::PropertyLength', 'CenterToEnd', 'Dimensions')
            _addp(obj, 'App::PropertyLength', 'BendRadius', 'Dimensions')
        elif k == 'tee_eq':
            _addp(obj, 'App::PropertyLength', 'RunCenterToEnd', 'Dimensions')
            _addp(obj, 'App::PropertyLength', 'OutletCenterToEnd', 'Dimensions')
        elif k == 'flange150':
            for n in ('FlangeOD', 'BoltCircle', 'BoltHoleDiameter', 'Thickness', 'RaisedFaceDiameter', 'RaisedFaceHeight', 'Bore'):
                _addp(obj, 'App::PropertyLength', n, 'Dimensions')
            _addp(obj, 'App::PropertyInteger', 'BoltHoles', 'Dimensions')

    def load(self, obj, preset):
        k = self.kind
        if k == 'reducer':
            big, small = preset.split(' x ')
            obj.OuterDiameterLarge = PIPE_OD[big]; obj.WallLarge = WALL_SCH40[big]
            obj.OuterDiameterSmall = PIPE_OD[small]; obj.WallSmall = WALL_SCH40[small]
            obj.Length = FL.REDUCER_H[(big, small)]
            FL.record(obj, 'reducer_concentric', preset, FL.REDUCER_SOURCES + PIPE_SOURCES, FL.REDUCER_REVISION + ' | ' + PIPE_NOTE)
            return
        obj.OuterDiameter = PIPE_OD[preset]; obj.Wall = WALL_SCH40[preset]
        if k == 'elbow90lr':
            obj.CenterToEnd = FL.ELBOW_90_LR_A[preset]; obj.BendRadius = FL.ELBOW_90_LR_A[preset]
            FL.record(obj, k, preset, FL.ELBOW_90_LR_SOURCES + PIPE_SOURCES, FL.ELBOW_90_LR_REVISION + ' | ' + PIPE_NOTE)
        elif k == 'elbow90sr':
            obj.CenterToEnd = FL.ELBOW_90_SR_A[preset]; obj.BendRadius = FL.ELBOW_90_SR_A[preset]
            FL.record(obj, k, preset, FL.ELBOW_90_SR_SOURCES + PIPE_SOURCES, FL.ELBOW_90_SR_REVISION + ' | ' + PIPE_NOTE)
        elif k == 'elbow45':
            obj.CenterToEnd = FL.ELBOW_45_LR_B[preset]; obj.BendRadius = FL.ELBOW_90_LR_A[preset]
            FL.record(obj, k, preset, FL.ELBOW_45_LR_SOURCES + PIPE_SOURCES,
                      FL.ELBOW_45_LR_REVISION + ' | bend radius = long-radius A of same size, straight ends added to reach B (model choice) | ' + PIPE_NOTE)
        elif k == 'tee_eq':
            c, m = FL.TEE_EQ_CM[preset]
            obj.RunCenterToEnd = c; obj.OutletCenterToEnd = m
            FL.record(obj, k, preset, FL.TEE_EQ_SOURCES + PIPE_SOURCES, FL.TEE_EQ_REVISION + ' | ' + PIPE_NOTE)
        elif k == 'flange150':
            f = FL.FLANGE_CL150[preset]
            obj.FlangeOD = f['od']; obj.BoltCircle = f['bolt_circle']; obj.BoltHoleDiameter = f['hole_dia']
            obj.Thickness = f['thickness_min']; obj.RaisedFaceDiameter = f['rf_dia']
            obj.RaisedFaceHeight = FL.FLANGE_RF_HEIGHT; obj.Bore = PIPE_OD[preset]; obj.BoltHoles = f['holes']
            FL.record(obj, k, preset, FL.FLANGE_SOURCES + PIPE_SOURCES,
                      FL.FLANGE_REVISION + ' | slip-on style, bore = pipe OD (model choice) | ' + PIPE_NOTE)

    def onChanged(self, obj, prop):
        if prop == 'SizePreset' and not obj.Document.Restoring and hasattr(self, 'kind') and obj.SizePreset in presets(self.kind):
            if getattr(obj, 'FittingPreset', obj.SizePreset) != obj.SizePreset:
                self.load(obj, obj.SizePreset)

    def execute(self, obj):
        k = self.kind
        if k.startswith('elbow'):
            ro = obj.OuterDiameter.Value / 2.0; ri = ro - obj.Wall.Value
            R = obj.BendRadius.Value; A = obj.CenterToEnd.Value
            ang = 45.0 if k == 'elbow45' else 90.0
            if ri <= 0 or R <= ro:
                raise ValueError('Need wall < radius and bend radius > pipe radius')
            t = A - R * math.tan(math.radians(ang / 2.0))
            if k == 'elbow45':
                if t < 0:
                    raise ValueError('Center-to-end is shorter than the bend allows')
            else:
                t = max(0.0, A - R)
            obj.Shape = build_elbow(ro, ri, R, ang, t)
        elif k == 'tee_eq':
            ro = obj.OuterDiameter.Value / 2.0; ri = ro - obj.Wall.Value
            c = obj.RunCenterToEnd.Value; m = obj.OutletCenterToEnd.Value
            if ri <= 0 or c < ro or m < ro:
                raise ValueError('Invalid tee dimensions')
            res = []
            for r in (ro, ri):
                run = Part.makeCylinder(r, 2 * c, V(-c, 0, 0), V(1, 0, 0))
                br = Part.makeCylinder(r, m, V(0, 0, 0), V(0, 1, 0))
                res.append(run.fuse(br))
            outer, inner = res
            obj.Shape = outer.cut(inner).removeSplitter()
        elif k == 'reducer':
            r1 = obj.OuterDiameterLarge.Value / 2.0; r2 = obj.OuterDiameterSmall.Value / 2.0
            i1 = r1 - obj.WallLarge.Value; i2 = r2 - obj.WallSmall.Value; h = obj.Length.Value
            if h <= 0 or i1 <= 0 or i2 <= 0 or r2 > r1:
                raise ValueError('Invalid reducer dimensions')
            outer = Part.makeCone(r1, r2, h, V(0, 0, 0), V(0, 0, 1))
            inner = Part.makeCone(i1, i2, h, V(0, 0, 0), V(0, 0, 1))
            obj.Shape = outer.cut(inner).removeSplitter()
        else:
            od = obj.FlangeOD.Value; t = obj.Thickness.Value; rf = obj.RaisedFaceDiameter.Value
            rh = obj.RaisedFaceHeight.Value; bore = obj.Bore.Value
            n = int(obj.BoltHoles); bc = obj.BoltCircle.Value; hd = obj.BoltHoleDiameter.Value
            if min(od, t, rf, bore, bc, hd) <= 0 or n < 1 or bore >= rf or bc + hd >= od or bc - hd <= rf:
                raise ValueError('Invalid flange dimensions')
            s = Part.makeCylinder(od / 2.0, t, V(0, 0, 0), V(0, 0, 1))
            s = s.fuse(Part.makeCylinder(rf / 2.0, rh, V(0, 0, t), V(0, 0, 1)))
            s = s.cut(Part.makeCylinder(bore / 2.0, t + rh, V(0, 0, 0), V(0, 0, 1)))
            for i in range(n):
                a = 2 * math.pi * i / n
                s = s.cut(Part.makeCylinder(hd / 2.0, t, V(bc / 2.0 * math.cos(a), bc / 2.0 * math.sin(a), 0), V(0, 0, 1)))
            obj.Shape = s.removeSplitter()


def expected_volume(obj):
    """Independent analytic volume (Pappus / frustum / disc formulas) for CI checks. None for the tee."""
    k = obj.FittingKind
    if k.startswith('elbow'):
        ro = obj.OuterDiameter.Value / 2.0; ri = ro - obj.Wall.Value
        R = obj.BendRadius.Value; A = obj.CenterToEnd.Value
        ang = 45.0 if k == 'elbow45' else 90.0
        t = A - R * math.tan(math.radians(ang / 2.0)) if k == 'elbow45' else max(0.0, A - R)
        return math.pi * (ro * ro - ri * ri) * (R * math.radians(ang) + 2 * t)
    if k == 'reducer':
        r1 = obj.OuterDiameterLarge.Value / 2.0; r2 = obj.OuterDiameterSmall.Value / 2.0
        i1 = r1 - obj.WallLarge.Value; i2 = r2 - obj.WallSmall.Value; h = obj.Length.Value
        fr = lambda a, b: math.pi * h / 3.0 * (a * a + a * b + b * b)
        return fr(r1, r2) - fr(i1, i2)
    if k == 'flange150':
        od = obj.FlangeOD.Value; t = obj.Thickness.Value; rf = obj.RaisedFaceDiameter.Value; rh = obj.RaisedFaceHeight.Value
        b = obj.Bore.Value; hd = obj.BoltHoleDiameter.Value; n = int(obj.BoltHoles)
        q = math.pi / 4.0
        return q * (od * od - b * b) * t + q * (rf * rf - b * b) * rh - n * q * hd * hd * t
    return None


def create(doc, kind, preset):
    obj = doc.addObject('Part::FeaturePython', 'Fit_' + kind)
    Fitting3D(obj, kind, preset)
    obj.Label = NAMES[kind] + ' ' + preset
    doc.recompute()
    return obj
