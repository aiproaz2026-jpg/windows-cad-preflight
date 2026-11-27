"""Straight pipe, weld-neck flange, generic valves and a generic pump, plus automatic fitting insertion on a route.
GPL-3.0-or-later. Table values: see fittings_library.py and fittings3d.py. Valve and pump body proportions are
GENERIC editable defaults (not a manufacturer or standard part); only valve face-to-face lengths and flange
connection dimensions come from published tables."""
import math
import FreeCAD as App
import Part
from . import fittings_library as FL
from . import fittings3d as F3

V = App.Vector
KINDS = ['pipe', 'weldneck150', 'gate_valve', 'ball_valve', 'check_valve', 'pump']
NAMES = {'pipe': 'ماسورة مستقيمة', 'weldneck150': 'فلنجة لحام عنق كلاس ١٥٠', 'gate_valve': 'محبس بوابة (عام)',
         'ball_valve': 'محبس كرة (عام)', 'check_valve': 'محبس عدم رجوع (عام)', 'pump': 'طلمبة طرد مركزي (عامة)'}
# NPS -> (hub diameter X, length through hub Y) mm. S1 teshigroup.com/dimensional-standards/asme-b16-5-class-150-weld-neck-flange-dimensions/
# S2 apiint.com/flange-dimensions/weld-neck-flange-dimensions/class-150-weld-neck/ (inches converted, agree within 0.5 mm rounding).
WN_XY = {'1': (49, 54), '1 1/4': (59, 56), '1 1/2': (65, 60), '2': (78, 62), '2 1/2': (90, 68), '3': (108, 68), '3 1/2': (122, 70), '4': (135, 75)}
WN_SOURCES = ['https://teshigroup.com/dimensional-standards/asme-b16-5-class-150-weld-neck-flange-dimensions/',
              'https://apiint.com/flange-dimensions/weld-neck-flange-dimensions/class-150-weld-neck/']
# Valve face-to-face, class 150 flanged, mm (ASME B16.10 as printed). S1 wermac.org/valves/dim_valves_ff.html (gate), S2 blog.projectmaterials.com/valves/asme-b16-10-valve-face-to-face/
# (gate, ball long pattern, globe and swing check). NPS 3 1/2 is not printed, so it is not offered for valves.
VALVE_FF = {
    'gate_valve':  {'1': 127, '1 1/4': 140, '1 1/2': 165, '2': 178, '2 1/2': 190, '3': 203, '4': 229},
    'ball_valve':  {'1': 127, '1 1/4': 140, '1 1/2': 165, '2': 178, '2 1/2': 190, '3': 203, '4': 229},
    'check_valve': {'1': 127, '1 1/4': 140, '1 1/2': 165, '2': 203, '2 1/2': 216, '3': 241, '4': 292},
}
VALVE_SOURCES = ['https://www.wermac.org/valves/dim_valves_ff.html', 'https://blog.projectmaterials.com/valves/asme-b16-10-valve-face-to-face/',
                 'https://citizenvalves.com/valve-face-to-face-dimension-asme-b1610-valve-end-to-end.html']
GENERIC_NOTE = ('GENERIC model: body, bonnet, stem, handwheel/lever and pump proportions are illustrative editable defaults, '
                'not a manufacturer or standard part. Only the face-to-face length and flange connection dimensions come from published tables. '
                'Not for procurement or design.')


def presets(kind):
    if kind in VALVE_FF:
        return list(VALVE_FF[kind])
    if kind == 'pump':
        return ['%s x %s' % k for k in FL.REDUCER_H]
    return list(FL.NPS_RANGE)


def _L(obj, name, val, grp='Dimensions'):
    obj.addProperty('App::PropertyLength', name, grp)
    setattr(obj, name, val)


def _cyl(r, h, p, d):
    return Part.makeCylinder(r, h, p, d)


def _flange(od, t, rf, rh, bore, n, bc, hd):
    """Flange along +Z: RF below z=0 (if rh>0), disc 0..t, bore through. Returns solid."""
    s = _cyl(od / 2.0, t, V(0, 0, 0), V(0, 0, 1))
    if rh > 0:
        s = s.fuse(_cyl(rf / 2.0, rh, V(0, 0, -rh), V(0, 0, 1)))
    if bore > 0.5:
        s = s.cut(_cyl(bore / 2.0, t + rh, V(0, 0, -rh), V(0, 0, 1)))
    for i in range(int(n)):
        a = 2 * math.pi * i / n
        s = s.cut(_cyl(hd / 2.0, t, V(bc / 2.0 * math.cos(a), bc / 2.0 * math.sin(a), 0), V(0, 0, 1)))
    return s


def _stamp(obj, kind, preset, sources, revision, generic):
    FL.record(obj, kind, preset, sources + F3.PIPE_SOURCES, revision + ' | ' + F3.PIPE_NOTE)
    if generic:
        if not hasattr(obj, 'GenericNote'):
            obj.addProperty('App::PropertyString', 'GenericNote', 'Dimensional provenance')
        obj.GenericNote = GENERIC_NOTE
        obj.setEditorMode('GenericNote', 1)


class Equip3D(object):
    def __init__(self, obj, kind, preset):
        self.kind = kind
        obj.addProperty('App::PropertyString', 'FittingKind', 'Fitting').FittingKind = kind
        obj.setEditorMode('FittingKind', 1)
        obj.addProperty('App::PropertyEnumeration', 'SizePreset', 'Fitting')
        obj.SizePreset = presets(kind)
        obj.SizePreset = preset
        self.fields(obj)
        self.load(obj, preset)
        obj.Proxy = self

    def fields(self, obj):
        k = self.kind
        if k != 'pump':
            _L(obj, 'OuterDiameter', 1)
            _L(obj, 'Wall', 1)
            obj.addProperty('App::PropertyEnumeration', 'Schedule', 'Dimensions')
            obj.Schedule = F3.SCHEDULES
        if k == 'pipe':
            _L(obj, 'Length', 1000.0)
        elif k == 'weldneck150':
            for n in ('FlangeOD', 'Thickness', 'RaisedFaceDiameter', 'RaisedFaceHeight', 'BoltCircle', 'BoltHoleDiameter', 'HubDiameter', 'LengthThroughHub'):
                _L(obj, n, 1)
            obj.addProperty('App::PropertyInteger', 'BoltHoles', 'Dimensions')
        elif k in VALVE_FF:
            for n in ('FaceToFace', 'FlangeOD', 'FlangeThickness', 'BoltCircle', 'BoltHoleDiameter', 'Bore', 'BodyDiameter',
                      'BonnetDiameter', 'BonnetHeight', 'StemDiameter', 'StemHeight', 'HandwheelDiameter', 'HandwheelThickness', 'LeverLength', 'LeverWidth'):
                _L(obj, n, 1, 'Dimensions' if n in ('FaceToFace', 'FlangeOD', 'FlangeThickness', 'BoltCircle', 'BoltHoleDiameter', 'Bore') else 'Generic proportions')
            obj.addProperty('App::PropertyInteger', 'BoltHoles', 'Dimensions')
        elif k == 'pump':
            for n in ('SuctionOD', 'SuctionWall', 'DischargeOD', 'DischargeWall', 'SuctionFlangeOD', 'SuctionFlangeThickness', 'SuctionBoltCircle', 'SuctionBoltHoleDiameter',
                      'DischargeFlangeOD', 'DischargeFlangeThickness', 'DischargeBoltCircle', 'DischargeBoltHoleDiameter'):
                _L(obj, n, 1)
            for n in ('SuctionStubLength', 'VoluteDiameter', 'VoluteLength', 'MotorDiameter', 'MotorLength', 'DischargeHeight', 'BasePlateThickness', 'BasePlateWidth', 'BasePlateMargin'):
                _L(obj, n, 1, 'Generic proportions')
            obj.addProperty('App::PropertyInteger', 'SuctionBoltHoles', 'Dimensions')
            obj.addProperty('App::PropertyInteger', 'DischargeBoltHoles', 'Dimensions')

    def load(self, obj, preset):
        k = self.kind
        if k == 'pump':
            big, small = preset.split(' x ')
            fb, fs = FL.FLANGE_CL150[big], FL.FLANGE_CL150[small]
            obj.SuctionOD = F3.PIPE_OD[big]; obj.SuctionWall = F3.WALL_SCH40[big]
            obj.DischargeOD = F3.PIPE_OD[small]; obj.DischargeWall = F3.WALL_SCH40[small]
            obj.SuctionFlangeOD = fb['od']; obj.SuctionFlangeThickness = fb['thickness_min']; obj.SuctionBoltCircle = fb['bolt_circle']
            obj.SuctionBoltHoleDiameter = fb['hole_dia']; obj.SuctionBoltHoles = fb['holes']
            obj.DischargeFlangeOD = fs['od']; obj.DischargeFlangeThickness = fs['thickness_min']; obj.DischargeBoltCircle = fs['bolt_circle']
            obj.DischargeBoltHoleDiameter = fs['hole_dia']; obj.DischargeBoltHoles = fs['holes']
            so = F3.PIPE_OD[big]
            obj.SuctionStubLength = round(1.5 * so, 1); obj.VoluteDiameter = round(3.0 * so, 1); obj.VoluteLength = round(2.0 * so, 1)
            obj.MotorDiameter = round(2.2 * so, 1); obj.MotorLength = round(5.0 * so, 1)
            obj.DischargeHeight = round(1.5 * so + 1.5 * F3.PIPE_OD[small], 1)
            obj.BasePlateThickness = 20.0; obj.BasePlateMargin = 40.0; obj.BasePlateWidth = round(3.0 * so + 80.0, 1)
            _stamp(obj, 'pump_generic', preset, FL.FLANGE_SOURCES, FL.FLANGE_REVISION + ' | flange connections only', True)
            return
        obj.OuterDiameter = F3.PIPE_OD[preset]; obj.Wall = F3.WALL_SCH40[preset]; obj.Schedule = 'SCH 40'
        f = FL.FLANGE_CL150[preset]
        if k == 'pipe':
            _stamp(obj, 'pipe_straight', preset, [], 'ASME B36.10 OD and wall as printed by the cited sources', False)
        elif k == 'weldneck150':
            x, y = WN_XY[preset]
            obj.FlangeOD = f['od']; obj.Thickness = f['thickness_min']; obj.RaisedFaceDiameter = f['rf_dia']; obj.RaisedFaceHeight = FL.FLANGE_RF_HEIGHT
            obj.BoltCircle = f['bolt_circle']; obj.BoltHoleDiameter = f['hole_dia']; obj.BoltHoles = f['holes']
            obj.HubDiameter = x; obj.LengthThroughHub = y
            _stamp(obj, k, preset, FL.FLANGE_SOURCES + WN_SOURCES, FL.FLANGE_REVISION + ' | hub X and length Y from the two weld-neck sources; Y measured from the raised face (model choice); bore = pipe inside diameter', False)
        else:
            ff = VALVE_FF[k][preset]
            od = F3.PIPE_OD[preset]; ro = od / 2.0; ri = ro - F3.WALL_SCH40[preset]
            obj.FaceToFace = ff; obj.FlangeOD = f['od']; obj.FlangeThickness = f['thickness_min']; obj.BoltCircle = f['bolt_circle']
            obj.BoltHoleDiameter = f['hole_dia']; obj.BoltHoles = f['holes']; obj.Bore = 2 * ri
            bd = round(1.5 * od, 1)
            obj.BodyDiameter = bd; obj.StemDiameter = max(6.0, round(0.2 * 2 * ri, 1))
            if k == 'gate_valve':
                obj.BonnetDiameter = round(0.7 * bd, 1); obj.BonnetHeight = round(0.8 * bd, 1); obj.StemHeight = round(1.2 * bd, 1)
                obj.HandwheelDiameter = round(min(2.0 * bd, 0.9 * ff), 1); obj.HandwheelThickness = 8.0; obj.LeverLength = 10.0; obj.LeverWidth = 10.0
            elif k == 'ball_valve':
                obj.BonnetDiameter = round(0.5 * bd, 1); obj.BonnetHeight = round(0.3 * bd, 1); obj.StemHeight = round(0.4 * bd, 1)
                obj.HandwheelDiameter = 10.0; obj.HandwheelThickness = 8.0; obj.LeverLength = round(2.5 * bd, 1); obj.LeverWidth = 20.0
            else:
                obj.BonnetDiameter = round(0.8 * bd, 1); obj.BonnetHeight = round(0.6 * bd, 1); obj.StemHeight = 5.0
                obj.HandwheelDiameter = 10.0; obj.HandwheelThickness = 8.0; obj.LeverLength = 10.0; obj.LeverWidth = 10.0
            _stamp(obj, k, preset, VALVE_SOURCES + FL.FLANGE_SOURCES, 'ASME B16.10 face-to-face as printed by the cited sources (class 150 flanged); flange per B16.5 table; flat faces modeled', True)

    def onChanged(self, obj, prop):
        if obj.Document is None or obj.Document.Restoring or not hasattr(self, 'kind'):
            return
        if prop == 'Schedule' and hasattr(obj, 'Wall') and obj.SizePreset in F3.PIPE_OD:
            w = F3.WALL_SCH.get(obj.Schedule, {}).get(obj.SizePreset)
            if w is not None:
                obj.Wall = w
                if self.kind == 'weldneck150':
                    pass
        elif prop == 'SizePreset' and obj.SizePreset in presets(self.kind) and getattr(obj, 'FittingPreset', obj.SizePreset) != obj.SizePreset:
            self.load(obj, obj.SizePreset)

    def execute(self, obj):
        pl = App.Placement(obj.Placement)
        self._build(obj)
        obj.Placement = pl

    def _build(self, obj):
        k = self.kind
        if k == 'pipe':
            ro = obj.OuterDiameter.Value / 2.0; ri = ro - obj.Wall.Value; L = obj.Length.Value
            if ri <= 0 or L <= 0:
                raise ValueError('Invalid pipe')
            obj.Shape = _cyl(ro, L, V(0, 0, 0), V(1, 0, 0)).cut(_cyl(ri, L, V(0, 0, 0), V(1, 0, 0))).removeSplitter()
        elif k == 'weldneck150':
            od = obj.FlangeOD.Value; t = obj.Thickness.Value; rf = obj.RaisedFaceDiameter.Value; rh = obj.RaisedFaceHeight.Value
            bc = obj.BoltCircle.Value; hd = obj.BoltHoleDiameter.Value; n = int(obj.BoltHoles)
            x = obj.HubDiameter.Value; y = obj.LengthThroughHub.Value; pod = obj.OuterDiameter.Value; bore = pod - 2 * obj.Wall.Value
            hh = y - rh - t
            if min(od, t, rf, rh, bc, hd, x, y, bore) <= 0 or hh <= 0 or bore >= rf or bc - hd <= rf or bc + hd >= od or x < pod:
                raise ValueError('Invalid weld-neck flange dimensions')
            s = _flange(od, t, rf, rh, 0, n, bc, hd)
            s = s.fuse(Part.makeCone(x / 2.0, pod / 2.0, hh, V(0, 0, t), V(0, 0, 1)))
            s = s.cut(_cyl(bore / 2.0, y + 1.0, V(0, 0, -rh - 0.5), V(0, 0, 1)))
            obj.Shape = s.removeSplitter()
        elif k in VALVE_FF:
            self.exec_valve(obj, k)
        else:
            self.exec_pump(obj)

    def exec_valve(self, obj, k):
        ff = obj.FaceToFace.Value; od = obj.FlangeOD.Value; t = obj.FlangeThickness.Value; bc = obj.BoltCircle.Value; hd = obj.BoltHoleDiameter.Value
        n = int(obj.BoltHoles); bore = obj.Bore.Value; bd = obj.BodyDiameter.Value
        if ff <= 2 * t or bore <= 0 or bd <= bore + 2 or bd > od or bc + hd >= od or 0.9 * bd / 2.0 <= bore / 2.0 + 1:
            raise ValueError('Invalid valve dimensions')
        fl = _flange(od, t, 0, 0, 0, n, bc, hd)
        left = fl.copy(); left.rotate(V(0, 0, 0), V(0, 1, 0), 90)
        right = fl.copy(); right.rotate(V(0, 0, 0), V(0, 1, 0), 90); right.translate(V(ff - t, 0, 0))
        s = left.fuse(right).fuse(_cyl(bd / 2.0, ff - 2 * t, V(t, 0, 0), V(1, 0, 0)))
        cx = ff / 2.0
        z0 = 0.9 * bd / 2.0
        bdia = obj.BonnetDiameter.Value; bh = obj.BonnetHeight.Value; sd = obj.StemDiameter.Value; sh = obj.StemHeight.Value
        s = s.fuse(_cyl(bdia / 2.0, bh, V(cx, 0, z0), V(0, 0, 1)))
        top = z0 + bh
        s = s.fuse(_cyl(sd / 2.0, sh + 1.0, V(cx, 0, top - 1.0), V(0, 0, 1)))
        top2 = top + sh
        if k == 'gate_valve':
            hw = obj.HandwheelDiameter.Value; ht = obj.HandwheelThickness.Value
            s = s.fuse(_cyl(hw / 2.0, ht, V(cx, 0, top2 - ht / 2.0), V(0, 0, 1)))
        elif k == 'ball_valve':
            ll = obj.LeverLength.Value; lw = obj.LeverWidth.Value; ht = obj.HandwheelThickness.Value
            s = s.fuse(Part.makeBox(lw, ll, ht, V(cx - lw / 2.0, -0.2 * ll, top2 - ht / 2.0)))
        s = s.cut(_cyl(bore / 2.0, ff, V(0, 0, 0), V(1, 0, 0)))
        obj.Shape = s.removeSplitter()

    def exec_pump(self, obj):
        so = obj.SuctionOD.Value; sw = obj.SuctionWall.Value; do = obj.DischargeOD.Value; dw = obj.DischargeWall.Value
        sl = obj.SuctionStubLength.Value; vd = obj.VoluteDiameter.Value; vl = obj.VoluteLength.Value; md = obj.MotorDiameter.Value; ml = obj.MotorLength.Value
        dh = obj.DischargeHeight.Value; bt = obj.BasePlateThickness.Value; bw = obj.BasePlateWidth.Value; mg = obj.BasePlateMargin.Value
        sfo = obj.SuctionFlangeOD.Value; sft = obj.SuctionFlangeThickness.Value; dfo = obj.DischargeFlangeOD.Value; dft = obj.DischargeFlangeThickness.Value
        if min(so, do, sl, vd, vl, md, ml, dh, bt, bw) <= 0 or so / 2 - sw <= 0 or do / 2 - dw <= 0 or vd < so + 4 or dh <= vd / 2.0 or sl <= sft or vd > bw or md > bw:
            raise ValueError('Invalid pump dimensions')
        s = _cyl(so / 2.0, sl + 1.0, V(0, 0, 0), V(1, 0, 0))
        fs = _flange(sfo, sft, 0, 0, 0, int(obj.SuctionBoltHoles), obj.SuctionBoltCircle.Value, obj.SuctionBoltHoleDiameter.Value)
        fs.rotate(V(0, 0, 0), V(0, 1, 0), 90)
        s = s.fuse(fs)
        s = s.fuse(_cyl(vd / 2.0, vl, V(sl, 0, 0), V(1, 0, 0)))
        xv = sl + vl / 2.0
        s = s.fuse(_cyl(do / 2.0, dh, V(xv, 0, 0), V(0, 0, 1)))
        fd = _flange(dfo, dft, 0, 0, 0, int(obj.DischargeBoltHoles), obj.DischargeBoltCircle.Value, obj.DischargeBoltHoleDiameter.Value)
        fd.translate(V(xv, 0, dh - dft))
        s = s.fuse(fd)
        s = s.fuse(_cyl(md / 2.0, ml, V(sl + vl - 1.0, 0, 0), V(1, 0, 0)))
        low = max(vd, md) / 2.0
        top = -low + 5.0
        total = sl + vl + ml
        s = s.fuse(Part.makeBox(total + 2 * mg, bw, bt, V(-mg, -bw / 2.0, top - bt)))
        s = s.fuse(Part.makeBox(0.6 * ml, 0.6 * md, (-md / 2.0 + 5.0) - top + 1.0, V(sl + vl + 0.2 * ml, -0.3 * md, top - 1.0)))
        s = s.cut(_cyl(so / 2.0 - sw, sl + vl / 2.0 + 1.0, V(-1.0, 0, 0), V(1, 0, 0)))
        s = s.cut(_cyl(do / 2.0 - dw, dh + 1.0, V(xv, 0, 0), V(0, 0, 1)))
        obj.Shape = s.removeSplitter()


def expected_volume(obj):
    k = obj.FittingKind
    q = math.pi / 4.0
    if k == 'pipe':
        o = obj.OuterDiameter.Value; i = o - 2 * obj.Wall.Value
        return q * (o * o - i * i) * obj.Length.Value
    if k == 'weldneck150':
        od = obj.FlangeOD.Value; t = obj.Thickness.Value; rf = obj.RaisedFaceDiameter.Value; rh = obj.RaisedFaceHeight.Value
        x = obj.HubDiameter.Value; y = obj.LengthThroughHub.Value; a = obj.OuterDiameter.Value; b = a - 2 * obj.Wall.Value
        hh = y - rh - t
        hub = math.pi * hh / 12.0 * (x * x + x * a + a * a)
        return q * od * od * t + q * rf * rf * rh + hub - q * b * b * y - int(obj.BoltHoles) * q * obj.BoltHoleDiameter.Value ** 2 * t
    return None


def create(doc, kind, preset):
    obj = doc.addObject('Part::FeaturePython', 'Eq_' + kind)
    Equip3D(obj, kind, preset)
    obj.Label = NAMES[kind] + ' ' + preset
    doc.recompute()
    return obj


# ---------------- automatic insertion on a route ----------------
def ordered_points(shape):
    try:
        return [v.Point for v in shape.Wires[0].OrderedVertexes]
    except Exception:
        return [v.Point for v in shape.Vertexes]


def _frame(d_in, d_out=None):
    x = V(d_in); x.normalize()
    if d_out is None:
        tmp = V(0, 0, 1) if abs(x.z) < 0.9 else V(0, 1, 0)
        y = tmp - x * tmp.dot(x)
    else:
        y = d_out - x * d_out.dot(x)
    y.normalize()
    z = x.cross(y)
    m = App.Matrix(x.x, y.x, z.x, 0, x.y, y.y, z.y, 0, x.z, y.z, z.z, 0, 0, 0, 0, 1)
    return App.Rotation(m)


def route_fittings(doc, pts, nps, schedule='SCH 40', tol_deg=0.5):
    """Place straight pipes and 90/45 degree elbows along a polyline. Returns dict with objects and joint check."""
    if len(pts) < 2:
        raise ValueError('Path needs at least two points')
    dirs = []
    for i in range(len(pts) - 1):
        d = pts[i + 1] - pts[i]
        if d.Length < 1e-6:
            raise ValueError('Zero-length segment %d' % (i + 1))
        d.normalize(); dirs.append(d)
    setback = [0.0] * len(pts); kinds = [None] * len(pts); angs = [0.0] * len(pts)
    for i in range(1, len(pts) - 1):
        c = max(-1.0, min(1.0, dirs[i - 1].dot(dirs[i])))
        ang = math.degrees(math.acos(c))
        angs[i] = ang
        if abs(ang) < tol_deg:
            continue
        if abs(ang - 90.0) <= tol_deg:
            kinds[i] = 'elbow90lr'; setback[i] = FL.ELBOW_90_LR_A[nps]
        elif abs(ang - 45.0) <= tol_deg:
            kinds[i] = 'elbow45'; setback[i] = FL.ELBOW_45_LR_B[nps]
        else:
            raise ValueError('Bend %d is %.1f degrees; only 90 and 45 degree bends have fittings' % (i, ang))
    out = {'pipes': [], 'elbows': [], 'joints': []}
    for i, kind in enumerate(kinds):
        if kind is None:
            continue
        e = F3.create(doc, kind, nps)
        e.Schedule = schedule
        doc.recompute()
        e.Placement = App.Placement(pts[i] - dirs[i - 1] * setback[i], _frame(dirs[i - 1], dirs[i]))
        out['elbows'].append(e)
    for i in range(len(pts) - 1):
        a = setback[i]; b = setback[i + 1]
        L = (pts[i + 1] - pts[i]).Length - a - b
        if L <= 1e-6:
            raise ValueError('Segment %d is too short (%.1f mm) for the fittings at its ends' % (i + 1, L + a + b))
        p = create(doc, 'pipe', nps)
        p.Schedule = schedule; p.Length = L
        doc.recompute()
        p.Placement = App.Placement(pts[i] + dirs[i] * a, _frame(dirs[i]))
        out['pipes'].append(p)
    # joint check: every pipe end must coincide with an elbow end (or path end)
    ends = []
    for e in out['elbows']:
        pl = e.Placement
        ends.append(pl.multVec(V(0, 0, 0)))
        ang = 45.0 if e.FittingKind == 'elbow45' else 90.0
        R = e.BendRadius.Value; A = e.CenterToEnd.Value
        t = A - R * math.tan(math.radians(ang / 2.0)) if e.FittingKind == 'elbow45' else max(0.0, A - R)
        a = math.radians(ang)
        ends.append(pl.multVec(V(t + R * math.sin(a) + t * math.cos(a), R - R * math.cos(a) + t * math.sin(a), 0)))
    ends += [pts[0], pts[-1]]
    worst = 0.0
    for p in out['pipes']:
        pl = p.Placement; L = p.Length.Value
        for q in (pl.multVec(V(0, 0, 0)), pl.multVec(V(L, 0, 0))):
            worst = max(worst, min((q - e).Length for e in ends))
    out['max_joint_gap_mm'] = worst
    return out
