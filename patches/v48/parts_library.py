# SPDX-License-Identifier: GPL-3.0-or-later
"""Editable parametric mechanical parts library.

Every generator builds a FeaturePython object whose dimensions are ordinary editable
properties: the engineer picks a standard preset OR types any diameter/dimension freely.
Preset rows are nominal millimetre values transcribed from the fetched published sources
listed per table (fetched 2026-11-26, each table cross-checked against two independent
sources; agreement notes in PARTS-LIBRARY-SOURCES.md). These are dimensional values only:
no strength, grade, material, tolerance or design approval is inherited. Threads are not
modeled (cosmetic note only); bearing internals are simplified to inner/outer rings.
"""

import math
import FreeCAD as App
import Part

SCOPE = ('Nominal dimensions from recorded published sources; editable parametric model. '
         'No strength, grade, material, tolerance or design approval inherited. '
         'A human engineer must verify any real use.')

# --- ISO 4032 style-1 hex nuts: pitch P, across-flats s (max), across-corners e min, thickness m max ---
# S1 https://www.fasteners.eu/standards/iso/4032/ ; S2 https://mechcodex.com/reference/hex-nut-dimensions-metric (identical values)
NUTS_ISO4032 = {
    'M4': (0.7, 7.0, 7.66, 3.2), 'M5': (0.8, 8.0, 8.79, 4.7), 'M6': (1.0, 10.0, 11.05, 5.2),
    'M8': (1.25, 13.0, 14.38, 6.8), 'M10': (1.5, 16.0, 17.77, 8.4), 'M12': (1.75, 18.0, 20.03, 10.8),
    'M14': (2.0, 21.0, 23.36, 12.8), 'M16': (2.0, 24.0, 26.75, 14.8), 'M18': (2.5, 27.0, 29.56, 15.8),
    'M20': (2.5, 30.0, 32.95, 18.0), 'M24': (3.0, 36.0, 39.55, 21.5), 'M30': (3.5, 46.0, 50.85, 25.6),
    'M36': (4.0, 55.0, 60.79, 31.0)}
NUT_SOURCES = ['https://www.fasteners.eu/standards/iso/4032/',
               'https://mechcodex.com/reference/hex-nut-dimensions-metric']
NUT_REVISION = 'ISO 4032 style 1 as published by both sources, fetched 2026-11-26'

# --- ISO 4014/4017 hex head bolts: nominal s (ISO values), nominal k ---
# S1 https://www.wermac.org/bolts/metricBDC.html (limits; nominal=max) ; S2 https://mechcodex.com/reference/hex-bolt-dimensions-metric
# Both note ISO vs DIN s differences at M10/M12/M14/M22; the ISO s values below are recorded.
BOLTS_ISO4014 = {
    'M5': (8.0, 3.5), 'M6': (10.0, 4.0), 'M8': (13.0, 5.3), 'M10': (16.0, 6.4),
    'M12': (18.0, 7.5), 'M14': (21.0, 8.8), 'M16': (24.0, 10.0), 'M18': (27.0, 11.5),
    'M20': (30.0, 12.5), 'M22': (34.0, 14.0), 'M24': (36.0, 15.0), 'M27': (41.0, 17.0),
    'M30': (46.0, 18.7), 'M33': (50.0, 21.0), 'M36': (55.0, 22.5), 'M42': (65.0, 26.0),
    'M48': (75.0, 30.0), 'M56': (85.0, 35.0), 'M64': (95.0, 40.0)}
BOLT_SOURCES = ['https://www.wermac.org/bolts/metricBDC.html',
                'https://mechcodex.com/reference/hex-bolt-dimensions-metric']
BOLT_REVISION = 'ISO 4014/4017 nominal s (ISO variant) and k as published by both sources, fetched 2026-11-26'

# --- ISO 7089 plain washers, normal series: hole d1, outside d2, thickness h ---
# S1 https://boltnote.net/en/lib/iso-7089-7090 ; S2 https://partxt.com/standards/iso-7089/ (identical values)
WASHERS_ISO7089 = {
    'M4': (4.3, 9.0, 0.8), 'M5': (5.3, 10.0, 1.0), 'M6': (6.4, 12.0, 1.6), 'M8': (8.4, 16.0, 1.6),
    'M10': (10.5, 20.0, 2.0), 'M12': (13.0, 24.0, 2.5), 'M14': (15.0, 28.0, 2.5),
    'M16': (17.0, 30.0, 3.0), 'M18': (19.0, 34.0, 3.0), 'M20': (21.0, 37.0, 3.0),
    'M24': (25.0, 44.0, 4.0), 'M30': (31.0, 56.0, 4.0), 'M36': (37.0, 66.0, 5.0)}
WASHER_SOURCES = ['https://boltnote.net/en/lib/iso-7089-7090',
                  'https://partxt.com/standards/iso-7089/']
WASHER_REVISION = 'ISO 7089 normal series as published by both sources, fetched 2026-11-26'

# --- Deep groove ball bearings 62xx, boundary dims to ISO 15: bore d, OD D, width B, chamfer r min ---
# S1 https://normtorial.com/bearings/6200-series-ball-bearing/ ; S2 https://nbkbearingusa.com/single-row-deep-groove-ball-bearings-62-series/ (d/D/B identical)
BEARINGS_62 = {
    '6200': (10, 30, 9, 0.6), '6201': (12, 32, 10, 0.6), '6202': (15, 35, 11, 0.6),
    '6203': (17, 40, 12, 0.6), '6204': (20, 47, 14, 1.0), '6205': (25, 52, 15, 1.0),
    '6206': (30, 62, 16, 1.0), '6207': (35, 72, 17, 1.1), '6208': (40, 80, 18, 1.1),
    '6209': (45, 85, 19, 1.1), '6210': (50, 90, 20, 1.1), '6211': (55, 100, 21, 1.5),
    '6212': (60, 110, 22, 1.5), '6213': (65, 120, 23, 1.5), '6214': (70, 125, 24, 1.5),
    '6215': (75, 130, 25, 1.5), '6216': (80, 140, 26, 2.0), '6217': (85, 150, 28, 2.0),
    '6218': (90, 160, 30, 2.0), '6219': (95, 170, 32, 2.1), '6220': (100, 180, 34, 2.1)}
BEARING_SOURCES = ['https://normtorial.com/bearings/6200-series-ball-bearing/',
                   'https://nbkbearingusa.com/single-row-deep-groove-ball-bearings-62-series/']
BEARING_REVISION = 'ISO 15 boundary dimensions as published by both sources, fetched 2026-11-26'

# --- IPE sections: h, b, tw, tf, r ---
# S1 https://indumor.com/en/tables/ipe-beam-dimensions.php ; S2 https://normtorial.com/profiles/ipe/ (identical values)
IPE = {
    'IPE 80': (80, 46, 3.8, 5.2, 5), 'IPE 100': (100, 55, 4.1, 5.7, 7),
    'IPE 120': (120, 64, 4.4, 6.3, 7), 'IPE 140': (140, 73, 4.7, 6.9, 7),
    'IPE 160': (160, 82, 5.0, 7.4, 9), 'IPE 180': (180, 91, 5.3, 8.0, 9),
    'IPE 200': (200, 100, 5.6, 8.5, 12), 'IPE 220': (220, 110, 5.9, 9.2, 12),
    'IPE 240': (240, 120, 6.2, 9.8, 15), 'IPE 270': (270, 135, 6.6, 10.2, 15),
    'IPE 300': (300, 150, 7.1, 10.7, 15), 'IPE 330': (330, 160, 7.5, 11.5, 18),
    'IPE 360': (360, 170, 8.0, 12.7, 18), 'IPE 400': (400, 180, 8.6, 13.5, 21),
    'IPE 450': (450, 190, 9.4, 14.6, 21)}
IPE_SOURCES = ['https://indumor.com/en/tables/ipe-beam-dimensions.php',
               'https://normtorial.com/profiles/ipe/']
IPE_REVISION = 'IPE section dims as published by both sources, fetched 2026-11-26'

# Coarse thread pitch per ISO 261 for bolt generator (subset matching BOLTS_ISO4014 keys)
PITCH = {'M5': 0.8, 'M6': 1.0, 'M8': 1.25, 'M10': 1.5, 'M12': 1.75, 'M14': 2.0, 'M16': 2.0,
         'M18': 2.5, 'M20': 2.5, 'M22': 2.5, 'M24': 3.0, 'M27': 3.0, 'M30': 3.5, 'M33': 3.5,
         'M36': 4.0, 'M42': 4.5, 'M48': 5.0, 'M56': 5.5, 'M64': 6.0}


def _nominal(size):
    """Nominal thread diameter in mm from an 'M12'-style size key."""
    return float(size[1:].replace(',', '.'))


def _stamp(obj, family, preset, sources, revision):
    for key, group in (('PartFamily', 'Provenance'), ('PartPreset', 'Provenance'),
                       ('DimensionSource', 'Provenance'), ('DimensionRevision', 'Provenance'),
                       ('DimensionScope', 'Provenance'), ('ThreadNote', 'Provenance')):
        if not hasattr(obj, key):
            obj.addProperty('App::PropertyString', key, group)
    obj.PartFamily = family
    obj.PartPreset = preset
    obj.DimensionSource = ' | '.join(sources)
    obj.DimensionRevision = revision
    obj.DimensionScope = SCOPE
    obj.ThreadNote = 'Threads not modeled; shown as plain shanks/bores'
    for key in ('PartFamily', 'PartPreset', 'DimensionSource', 'DimensionRevision', 'DimensionScope', 'ThreadNote'):
        obj.setEditorMode(key, 1)


def _hex_prism(s, height):
    r = s / math.sqrt(3.0)
    pts = [App.Vector(r * math.cos(math.radians(60 * i + 30)), r * math.sin(math.radians(60 * i + 30)), 0) for i in range(6)]
    return Part.makePolygon(pts + [pts[0]])


class HexBolt(object):
    """ISO 4014-style hex head bolt; every dimension editable. Threads not modeled."""

    def __init__(self, obj, size='M12', length=60.0):
        obj.addProperty('App::PropertyEnumeration', 'SizePreset', 'Bolt').SizePreset = list(BOLTS_ISO4014)
        obj.SizePreset = size
        d = _nominal(size)
        s, k = BOLTS_ISO4014[size]
        for name, val, grp in (('NominalDiameter', d, 'Bolt'), ('AcrossFlats', s, 'Bolt'),
                               ('HeadHeight', k, 'Bolt'), ('Length', length, 'Bolt'),
                               ('Pitch', PITCH[size], 'Bolt')):
            obj.addProperty('App::PropertyLength' if grp == 'Bolt' and name != 'Pitch' else 'App::PropertyLength', name, grp)
            setattr(obj, name, val)
        obj.Proxy = self

    def execute(self, obj):
        d = obj.NominalDiameter.Value
        s = obj.AcrossFlats.Value
        k = obj.HeadHeight.Value
        L = obj.Length.Value
        if min(d, s, k, L) <= 0:
            raise ValueError('All dimensions must be positive')
        head = Part.Face(Part.Wire(_hex_prism(s, 1).Edges)).extrude(App.Vector(0, 0, k))
        shank = Part.makeCylinder(d / 2.0, L, App.Vector(0, 0, -L))
        obj.Shape = head.fuse(shank)
        _stamp(obj, 'hex_bolt_iso4014', obj.SizePreset, BOLT_SOURCES, BOLT_REVISION)


class HexNut(object):
    """ISO 4032 style-1 hex nut; every dimension editable. Threads not modeled."""

    def __init__(self, obj, size='M12'):
        obj.addProperty('App::PropertyEnumeration', 'SizePreset', 'Nut').SizePreset = list(NUTS_ISO4032)
        obj.SizePreset = size
        p, s, e, m = NUTS_ISO4032[size]
        for name, val in (('NominalDiameter', _nominal(size)), ('Pitch', p),
                          ('AcrossFlats', s), ('Thickness', m)):
            obj.addProperty('App::PropertyLength', name, 'Nut')
            setattr(obj, name, val)
        obj.Proxy = self

    def execute(self, obj):
        d = obj.NominalDiameter.Value
        s = obj.AcrossFlats.Value
        m = obj.Thickness.Value
        if min(d, s, m) <= 0 or d / 2.0 >= s / math.sqrt(3.0):
            raise ValueError('Bore must fit inside the hex')
        hexo = Part.Face(Part.Wire(_hex_prism(s, 1).Edges)).extrude(App.Vector(0, 0, m))
        obj.Shape = hexo.cut(Part.makeCylinder(d / 2.0, m))
        _stamp(obj, 'hex_nut_iso4032', obj.SizePreset, NUT_SOURCES, NUT_REVISION)


class Washer(object):
    """ISO 7089 normal-series plain washer; every dimension editable."""

    def __init__(self, obj, size='M12'):
        obj.addProperty('App::PropertyEnumeration', 'SizePreset', 'Washer').SizePreset = list(WASHERS_ISO7089)
        obj.SizePreset = size
        d1, d2, h = WASHERS_ISO7089[size]
        for name, val in (('InnerDiameter', d1), ('OuterDiameter', d2), ('Thickness', h)):
            obj.addProperty('App::PropertyLength', name, 'Washer')
            setattr(obj, name, val)
        obj.Proxy = self

    def execute(self, obj):
        d1 = obj.InnerDiameter.Value
        d2 = obj.OuterDiameter.Value
        h = obj.Thickness.Value
        if min(d1, d2, h) <= 0 or d1 >= d2:
            raise ValueError('Require 0 < inner < outer, positive thickness')
        obj.Shape = Part.makeCylinder(d2 / 2.0, h).cut(Part.makeCylinder(d1 / 2.0, h))
        _stamp(obj, 'washer_iso7089', obj.SizePreset, WASHER_SOURCES, WASHER_REVISION)


class Bearing62(object):
    """62xx deep groove ball bearing, boundary dims to ISO 15; simplified to two rings."""

    def __init__(self, obj, designation='6205'):
        obj.addProperty('App::PropertyEnumeration', 'SizePreset', 'Bearing').SizePreset = list(BEARINGS_62)
        obj.SizePreset = designation
        d, D, B, r = BEARINGS_62[designation]
        for name, val in (('BoreDiameter', d), ('OuterDiameter', D), ('Width', B)):
            obj.addProperty('App::PropertyLength', name, 'Bearing')
            setattr(obj, name, val)
        obj.Proxy = self

    def execute(self, obj):
        d = obj.BoreDiameter.Value
        D = obj.OuterDiameter.Value
        B = obj.Width.Value
        if min(d, D, B) <= 0 or d >= D:
            raise ValueError('Require 0 < bore < outer, positive width')
        wall = (D - d) / 4.0
        outer = Part.makeCylinder(D / 2.0, B).cut(Part.makeCylinder(D / 2.0 - wall, B))
        inner = Part.makeCylinder(d / 2.0 + wall, B).cut(Part.makeCylinder(d / 2.0, B))
        obj.Shape = outer.fuse(inner)
        _stamp(obj, 'bearing_62xx', obj.SizePreset, BEARING_SOURCES, BEARING_REVISION)


class IpeSection(object):
    """IPE I-section extruded to an editable length; fillet radius approximated by chamfer-free profile."""

    def __init__(self, obj, designation='IPE 200', length=1000.0):
        obj.addProperty('App::PropertyEnumeration', 'SizePreset', 'Section').SizePreset = list(IPE)
        obj.SizePreset = designation
        h, b, tw, tf, r = IPE[designation]
        for name, val in (('Height', h), ('FlangeWidth', b), ('WebThickness', tw),
                          ('FlangeThickness', tf), ('Length', length)):
            obj.addProperty('App::PropertyLength', name, 'Section')
            setattr(obj, name, val)
        obj.Proxy = self

    def execute(self, obj):
        h = obj.Height.Value
        b = obj.FlangeWidth.Value
        tw = obj.WebThickness.Value
        tf = obj.FlangeThickness.Value
        L = obj.Length.Value
        if min(h, b, tw, tf, L) <= 0 or tw >= b or 2 * tf >= h:
            raise ValueError('Invalid section proportions')
        hb, hw = b / 2.0, tw / 2.0
        y0, y1, y2 = -h / 2.0, -h / 2.0 + tf, h / 2.0 - tf
        y3 = h / 2.0
        pts = [(-hb, y0), (hb, y0), (hb, y1), (hw, y1), (hw, y2), (hb, y2), (hb, y3),
               (-hb, y3), (-hb, y2), (-hw, y2), (-hw, y1), (-hb, y1)]
        wire = Part.makePolygon([App.Vector(x, y, 0) for x, y in pts] + [App.Vector(*pts[0], 0)])
        obj.Shape = Part.Face(wire).extrude(App.Vector(0, 0, L))
        _stamp(obj, 'ipe_section', obj.SizePreset, IPE_SOURCES, IPE_REVISION)


class SpurGear(object):
    """Involute spur gear from module, teeth, 20 deg pressure angle. Pure formula, no table source."""

    def __init__(self, obj, module=2.0, teeth=20, thickness=10.0):
        for name, val in (('Module', module), ('Thickness', thickness)):
            obj.addProperty('App::PropertyLength', name, 'Gear')
            setattr(obj, name, val)
        obj.addProperty('App::PropertyInteger', 'Teeth', 'Gear').Teeth = teeth
        obj.addProperty('App::PropertyAngle', 'PressureAngle', 'Gear').PressureAngle = 20.0
        obj.Proxy = self

    def execute(self, obj):
        m = obj.Module.Value
        z = int(obj.Teeth)
        pa = math.radians(float(obj.PressureAngle))
        b = obj.Thickness.Value
        if m <= 0 or z < 8 or b <= 0:
            raise ValueError('Require module > 0, teeth >= 8, thickness > 0')
        rp = m * z / 2.0
        rb = rp * math.cos(pa)
        ra = rp + m
        rd = rp - 1.25 * m
        inv_pa = math.tan(pa) - pa

        def theta(r):
            ar = math.acos(min(1.0, rb / r))
            return math.pi / (2.0 * z) + inv_pa - (math.tan(ar) - ar)

        r_start = max(rd, rb)
        th_start = theta(r_start)
        steps = 8
        radii = [r_start + (ra - r_start) * i / steps for i in range(steps + 1)]
        step = 2.0 * math.pi / z

        def pt(r, ang):
            return App.Vector(r * math.cos(ang), r * math.sin(ang), 0)

        edges = []
        for k in range(z):
            phi = step * k
            path = []
            if rd < rb:
                path.append(pt(rd, phi - th_start))
            path += [pt(r, phi - theta(r)) for r in radii]
            path.append(pt(ra, phi + theta(ra)))
            path += [pt(r, phi + theta(r)) for r in reversed(radii)]
            if rd < rb:
                path.append(pt(rd, phi + th_start))
            for i in range(len(path) - 1):
                edges.append(Part.makeLine(path[i], path[i + 1]))
            a0 = phi + th_start
            a1 = phi + step - th_start
            mid = (a0 + a1) / 2.0
            edges.append(Part.Arc(pt(rd, a0), pt(rd, mid), pt(rd, a1)).toShape())
        obj.Shape = Part.Face(Part.Wire(edges)).extrude(App.Vector(0, 0, b))
        _stamp(obj, 'spur_gear_involute', 'm=%s z=%s' % (obj.Module.Value, z),
               ['formula-based: standard involute, pressure angle 20 deg; no table source'], 'computed')


def create(doc, family, preset=None):
    table = {'hex_bolt': (HexBolt, 'M12'), 'hex_nut': (HexNut, 'M12'), 'washer': (Washer, 'M12'),
             'bearing': (Bearing62, '6205'), 'ipe': (IpeSection, 'IPE 200'), 'gear': (SpurGear, None)}
    cls, default = table[family]
    obj = doc.addObject('Part::FeaturePython', family)
    cls(obj, preset or default) if default else cls(obj)
    doc.recompute()
    return obj


def families():
    return {'hex_bolt': len(BOLTS_ISO4014), 'hex_nut': len(NUTS_ISO4032), 'washer': len(WASHERS_ISO7089),
            'bearing': len(BEARINGS_62), 'ipe': len(IPE), 'gear': 'parametric (module x teeth)'}
