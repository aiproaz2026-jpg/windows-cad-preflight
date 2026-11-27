"""Parametric 3D threads: ISO metric external thread (bolt/stud shank) and NPT male pipe thread (nipple end).
GPL-3.0-or-later.

Standards and limits (be honest with the user):
 * Metric: ISO 68-1 basic profile (60 degrees, H=0.866P, minor d1=d-1.0825P, pitch d2=d-0.6495P). Coarse pitches follow ISO 261 as printed by
   https://boltport.com/threads/metric-coarse-threads/ and https://protorfq.com/metric-thread-chart/ (they agree). No tolerance class is applied
   (basic size, like 6H/6g mean values are NOT modeled).
 * NPT: ANSI/ASME B1.20.1 as printed by https://amesweb.info/Screws/NPT-Thread-Chart.aspx and https://www.engineersedge.com/hardware/taper-pipe-threads.htm
   (TPI, pipe OD, pitch diameter E0 at the small end of the external thread, effective thread length L2; they agree). Taper 1:16 on diameter.
   The ridge profile is a simplified 60 degree trapezoid (thread height 0.8P); crest/root truncation is NOT taken from the standard's tables.
   The thread is modeled over the effective length L2 only (no vanish thread). Not for gauging or certification.
 * Internal (female) threads are NOT modeled. Left-hand threads are not offered.
 * If the helical solid cannot be built in the CAD kernel, the object falls back to a plain core cylinder/cone at pitch diameter and says so in ThreadModeUsed.
"""
import math
import FreeCAD as App
import Part

V = App.Vector
# nominal diameter d (mm) -> coarse pitch P (mm)
METRIC_COARSE = {'M3': (3.0, 0.5), 'M4': (4.0, 0.7), 'M5': (5.0, 0.8), 'M6': (6.0, 1.0), 'M8': (8.0, 1.25), 'M10': (10.0, 1.5), 'M12': (12.0, 1.75),
                 'M14': (14.0, 2.0), 'M16': (16.0, 2.0), 'M20': (20.0, 2.5), 'M24': (24.0, 3.0), 'M30': (30.0, 3.5), 'M36': (36.0, 4.0)}
# NPS -> (pipe OD in, TPI, E0 in, effective thread length L2 in)
NPT = {'1/8': (0.405, 27, 0.36351, 0.2639), '1/4': (0.540, 18, 0.47739, 0.4018), '3/8': (0.675, 18, 0.61201, 0.4078),
       '1/2': (0.840, 14, 0.75843, 0.5337), '3/4': (1.050, 14, 0.96768, 0.5457), '1': (1.315, 11.5, 1.21363, 0.6828),
       '1 1/4': (1.660, 11.5, 1.55713, 0.7068), '1 1/2': (1.900, 11.5, 1.79609, 0.7235), '2': (2.375, 11.5, 2.26902, 0.7565),
       '2 1/2': (2.875, 8, 2.71953, 1.1375), '3': (3.500, 8, 3.34062, 1.2000), '4': (4.500, 8, 4.33438, 1.3000)}
IN = 25.4
SOURCES = ['https://boltport.com/threads/metric-coarse-threads/', 'https://protorfq.com/metric-thread-chart/',
           'https://amesweb.info/Screws/NPT-Thread-Chart.aspx', 'https://www.engineersedge.com/hardware/taper-pipe-threads.htm']
NOTE = ('Metric: ISO 68-1 basic profile, ISO 261 coarse pitch, no tolerance class. NPT: ANSI B1.20.1 table values, simplified ridge profile, effective length only. '
        'No internal threads, no left-hand threads. Illustrative model, not for gauging or certification.')
KINDS = ['metric', 'npt']
NAMES = {'metric': 'قلاووظ متري (ISO) على ساق مسمار', 'npt': 'قلاووظ ماسورة NPT على طرف نيبل'}
MODES = ['Modeled', 'Cosmetic']


def presets(kind):
    return list(METRIC_COARSE) if kind == 'metric' else list(NPT)


def metric_dims(preset):
    d, p = METRIC_COARSE[preset]
    return {'d': d, 'P': p, 'd1': d - 1.0825 * p, 'd2': d - 0.6495 * p}


def _ridge(r_base, h, w0, wc, z0=0.0):
    """Trapezoid in the XZ plane at the helix start; base slightly embedded in the core."""
    e = 0.04 * h
    t = (w0 / 2.0 - wc / 2.0) / h
    wb = w0 / 2.0 + e * t
    pts = [V(r_base - e, 0, z0 - wb), V(r_base + h, 0, z0 - wc / 2.0), V(r_base + h, 0, z0 + wc / 2.0), V(r_base - e, 0, z0 + wb)]
    return Part.Wire(Part.makePolygon(pts + [pts[0]]))


def _metric_shape(d, P, L, modeled):
    d1 = d - 1.0825 * P
    r1 = d1 / 2.0
    core = Part.makeCylinder(r1, L)
    if not modeled:
        return Part.makeCylinder((d - 0.6495 * P) / 2.0, L), False
    h = (d - d1) / 2.0
    H = L + 3.0 * P
    helix = Part.makeHelix(P, H, r1)
    prof = _ridge(r1, h, 0.75 * P, 0.125 * P)
    sweep = Part.Wire(helix).makePipeShell([prof], True, True)
    sweep.translate(V(0, 0, -1.5 * P))
    box = Part.makeCylinder(d / 2.0 + 0.01, L)
    s = core.fuse(sweep).common(box)
    s = s.removeSplitter() if hasattr(s, 'removeSplitter') else s
    return s, True


def _npt_shape(nps, modeled, body_len):
    od_in, tpi, e0_in, l2_in = NPT[nps]
    P = IN / tpi
    e0 = e0_in * IN
    L = l2_in * IN
    D = od_in * IN
    k = 1.0 / 32.0  # radius change per unit length (taper 1:16 on diameter)
    h = 0.8 * P
    rp0 = e0 / 2.0                      # pitch radius at the small end
    rcore0 = rp0 - h / 2.0
    rcore1 = rcore0 + k * L
    if not modeled:
        core = Part.makeCone(rp0, rp0 + k * L, L)
    else:
        core = Part.makeCone(rcore0, rcore1, L)
        H = L + 3.0 * P
        ang = math.degrees(math.atan(k))
        helix = Part.makeHelix(P, H, rcore0 - k * 1.5 * P, ang)
        prof = _ridge(rcore0 - k * 1.5 * P, h, 0.95 * P, 0.026 * P)
        sweep = Part.Wire(helix).makePipeShell([prof], True, True)
        sweep.translate(V(0, 0, -1.5 * P))
        env = Part.makeCone(rp0 + h / 2.0 + 0.01, rp0 + h / 2.0 + 0.01 + k * L, L)
        core = core.fuse(sweep).common(env)
    # local frame: z=0 small end. Final: free (small) end at the top of a plain body of OD D.
    core.rotate(V(0, 0, 0), V(1, 0, 0), 180)
    core.translate(V(0, 0, body_len + L))
    body = Part.makeCylinder(D / 2.0, body_len)
    s = body.fuse(core)
    s = s.removeSplitter() if hasattr(s, 'removeSplitter') else s
    return s, modeled


class Thread3D(object):
    def __init__(self, obj, kind, preset):
        self.kind = kind
        obj.addProperty('App::PropertyString', 'ThreadKind', 'Thread').ThreadKind = kind
        obj.setEditorMode('ThreadKind', 1)
        obj.addProperty('App::PropertyEnumeration', 'SizePreset', 'Thread')
        obj.SizePreset = presets(kind)
        obj.SizePreset = preset
        obj.addProperty('App::PropertyEnumeration', 'ThreadMode', 'Thread')
        obj.ThreadMode = MODES
        obj.ThreadMode = 'Modeled'
        obj.addProperty('App::PropertyString', 'ThreadModeUsed', 'Thread')
        obj.setEditorMode('ThreadModeUsed', 1)
        obj.addProperty('App::PropertyString', 'Standard', 'Thread')
        obj.setEditorMode('Standard', 1)
        obj.addProperty('App::PropertyString', 'Limits', 'Thread')
        obj.setEditorMode('Limits', 1)
        obj.Limits = NOTE
        obj.addProperty('App::PropertyStringList', 'Sources', 'Thread')
        obj.Sources = SOURCES
        obj.setEditorMode('Sources', 1)
        for n in ('Pitch', 'MajorDiameter', 'MinorDiameter', 'PitchDiameter'):
            obj.addProperty('App::PropertyLength', n, 'Thread values (read only)')
            obj.setEditorMode(n, 1)
        if kind == 'metric':
            obj.addProperty('App::PropertyLength', 'Length', 'Dimensions').Length = 30.0
        else:
            obj.addProperty('App::PropertyLength', 'BodyLength', 'Dimensions').BodyLength = 40.0
            obj.addProperty('App::PropertyLength', 'ThreadLength', 'Thread values (read only)')
            obj.setEditorMode('ThreadLength', 1)
        obj.Proxy = self
        self._values(obj)

    def _values(self, obj):
        if self.kind == 'metric':
            m = metric_dims(obj.SizePreset)
            obj.Pitch = m['P']; obj.MajorDiameter = m['d']; obj.MinorDiameter = m['d1']; obj.PitchDiameter = m['d2']
            obj.Standard = 'ISO 68-1 / ISO 261 coarse, basic profile'
        else:
            od, tpi, e0, l2 = NPT[obj.SizePreset]
            obj.Pitch = IN / tpi; obj.MajorDiameter = od * IN; obj.PitchDiameter = e0 * IN
            obj.MinorDiameter = e0 * IN - 0.8 * IN / tpi
            obj.ThreadLength = l2 * IN
            obj.Standard = 'ANSI/ASME B1.20.1 NPT (table values), simplified profile'

    def onChanged(self, obj, prop):
        if obj.Document is None or obj.Document.Restoring or not hasattr(self, 'kind'):
            return
        if prop == 'SizePreset' and obj.SizePreset in presets(self.kind):
            self._values(obj)

    def execute(self, obj):
        pl = App.Placement(obj.Placement)
        modeled = obj.ThreadMode == 'Modeled'
        used = 'Modeled'
        try:
            if self.kind == 'metric':
                m = metric_dims(obj.SizePreset)
                s, ok = _metric_shape(m['d'], m['P'], obj.Length.Value, modeled)
            else:
                s, ok = _npt_shape(obj.SizePreset, modeled, obj.BodyLength.Value)
            if modeled and (not s.isValid() or len(s.Solids) != 1 or s.Volume <= 0):
                raise RuntimeError('helical solid invalid')
            used = 'Modeled' if (modeled and ok) else 'Cosmetic'
        except Exception as ex:
            used = 'Cosmetic (modeling failed: %s)' % str(ex)[:60]
            if self.kind == 'metric':
                m = metric_dims(obj.SizePreset)
                s, _ = _metric_shape(m['d'], m['P'], obj.Length.Value, False)
            else:
                s, _ = _npt_shape(obj.SizePreset, False, obj.BodyLength.Value)
        obj.ThreadModeUsed = used
        obj.Shape = s
        obj.Placement = pl


def create(doc, kind, preset):
    obj = doc.addObject('Part::FeaturePython', 'Thr_' + kind)
    Thread3D(obj, kind, preset)
    obj.Label = NAMES[kind] + ' ' + preset
    doc.recompute()
    return obj
