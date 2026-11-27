
# ---- v63 (UNTESTED) IEC-style passive and electronic family: resistors, capacitors, diodes, transistors ----
# APPEND this block to the end of patches/v60/elec_lib_data.py (it uses _rect, LIB, math from that module).
# HONEST SCOPE: original line/circle/arc drawings that follow the general IEC 60617 look (rectangle resistor,
# two-plate capacitor, triangle-and-bar diode, circle-envelope bipolar transistor). Not copied from the standard and
# not checked against it. Coordinates are FreeCAD-style (y up). Never run in CI yet.
import math as _m


def _arrow(tx, ty, dx, dy, size=6, spread=25):
    """arrowhead (two lines) with tip at (tx,ty), pointing along direction (dx,dy)"""
    n = _m.hypot(dx, dy)
    dx, dy = dx / n, dy / n
    out = []
    for s in (spread, -spread):
        a = _m.radians(180 + s)
        c, sn = _m.cos(a), _m.sin(a)
        bx, by = dx * c - dy * sn, dx * sn + dy * c
        out.append(('L', [(tx + bx * size, ty + by * size), (tx, ty)]))
    return out


def _diag_arrow(x0, y0, x1, y1):
    return [('L', [(x0, y0), (x1, y1)])] + _arrow(x1, y1, x1 - x0, y1 - y0)


def _lead(x0, x1):
    return ('L', [(x0, 0), (x1, 0)])


def _diode_body():
    return [_lead(-40, -10), ('L', [(-10, -14), (-10, 14), (12, 0), (-10, -14)]), _lead(12, 40)]


def _bar_plain():
    return ('L', [(12, -14), (12, 14)])


def _light_arrows(out):
    """two parallel arrows near the diode: out=True leaves the diode (LED), False points at it (photodiode)"""
    res = []
    for ox in (-6, 4):
        if out:
            res += _diag_arrow(ox, 18, ox + 10, 30)
        else:
            res += _diag_arrow(ox + 10, 30, ox, 18)
    return res


def _bjt(npn):
    prims = [('C', 0, 0, 26), _lead(-40, -8), ('L', [(-8, -14), (-8, 14)]),
             ('L', [(-8, 6), (12, 20), (12, 40)]), ('L', [(-8, -6), (12, -20), (12, -40)])]
    if npn:  # emitter arrow points away from base
        prims += _arrow(7, -16.0, 20, -14)
    else:    # emitter arrow points toward base
        prims += _arrow(-3, -9.0, -20, 14)
    return prims


def _mosfet(n_channel):
    prims = [_lead(-40, -14), ('L', [(-14, -14), (-14, 14)]),
             ('L', [(-8, 16), (-8, 10)]), ('L', [(-8, 4), (-8, -4)]), ('L', [(-8, -10), (-8, -16)]),
             ('L', [(-8, 13), (12, 13), (12, 40)]), ('L', [(-8, -13), (12, -13), (12, -40)]),
             ('L', [(12, 0), (12, -13)]), ('L', [(12, 0), (-8, 0)])]
    # N-channel: arrow on body line points toward the channel; P-channel: away from it
    prims += _arrow(-8, 0, -1, 0) if n_channel else _arrow(12, 0, 1, 0)
    return prims


_RES_BODY = [_lead(-40, -20), _rect(-20, -7, 20, 7), _lead(20, 40)]

IEC_PASSIVE = {
 'Resistor (IEC-style)': ('مقاومة (IEC)', ('1', '2'), list(_RES_BODY)),
 'Variable resistor (IEC-style)': ('مقاومة متغيرة (IEC)', ('1', '2'), _RES_BODY + _diag_arrow(-14, -16, 14, 16)),
 'Potentiometer (IEC-style)': ('مقاومة ذات ممرر (IEC)', ('1', '2', '3'), _RES_BODY + [('L', [(0, 28), (0, 12)])] + _arrow(0, 7, 0, -1)),
 'NTC thermistor (IEC-style)': ('مقاومة حرارية NTC (IEC)', ('1', '2'), _RES_BODY + [('L', [(-14, -14), (-8, -14), (14, 14)])]),
 'LDR photoresistor (IEC-style)': ('مقاومة ضوئية LDR (IEC)', ('1', '2'), _RES_BODY + _diag_arrow(-10, 26, -2, 12) + _diag_arrow(2, 26, 10, 12)),
 'Varistor VDR (IEC-style)': ('فاريستور VDR (IEC)', ('1', '2'), _RES_BODY + [('L', [(-14, -14), (14, 14)])]),
 'Capacitor (IEC-style)': ('مكثف (IEC)', ('1', '2'), [_lead(-40, -4), ('L', [(-4, -16), (-4, 16)]), ('L', [(4, -16), (4, 16)]), _lead(4, 40)]),
 'Polarized capacitor (IEC-style)': ('مكثف قطبي (IEC)', ('+', '-'), [_lead(-40, -4), ('L', [(-4, -16), (-4, 16)]), _rect(2, -16, 6, 16), _lead(6, 40),
                                                                  ('L', [(-16, 10), (-10, 10)]), ('L', [(-13, 7), (-13, 13)])]),
 'Variable capacitor (IEC-style)': ('مكثف متغير (IEC)', ('1', '2'), [_lead(-40, -4), ('L', [(-4, -16), (-4, 16)]), ('L', [(4, -16), (4, 16)]), _lead(4, 40)] + _diag_arrow(-14, -20, 14, 20)),
 'Diode (IEC-style)': ('دايود (IEC)', ('A', 'K'), _diode_body() + [_bar_plain()]),
 'Zener diode (IEC-style)': ('دايود زينر (IEC)', ('A', 'K'), _diode_body() + [('L', [(7, -14), (12, -14), (12, 14), (17, 14)])]),
 'Schottky diode (IEC-style)': ('دايود شوتكي (IEC)', ('A', 'K'), _diode_body() + [('L', [(7, 8), (7, 14), (12, 14), (12, -14), (17, -14), (17, -8)])]),
 'LED (IEC-style)': ('دايود مضيء LED (IEC)', ('A', 'K'), _diode_body() + [_bar_plain()] + _light_arrows(True)),
 'Photodiode (IEC-style)': ('دايود ضوئي (IEC)', ('A', 'K'), _diode_body() + [_bar_plain()] + _light_arrows(False)),
 'NPN transistor (IEC-style)': ('ترانزستور NPN (IEC)', ('B', 'C', 'E'), _bjt(True)),
 'PNP transistor (IEC-style)': ('ترانزستور PNP (IEC)', ('B', 'C', 'E'), _bjt(False)),
 'N-MOSFET enhancement (IEC-style)': ('موسفت N معزز (IEC)', ('G', 'D', 'S'), _mosfet(True)),
 'P-MOSFET enhancement (IEC-style)': ('موسفت P معزز (IEC)', ('G', 'D', 'S'), _mosfet(False)),
}
# NOTE for the integrator: terminal ORDER is only labels here, same as the existing LIB. Real terminal anchor points
# (lead ends) are: 2-lead parts (-40,0),(40,0); potentiometer wiper (0,28); BJT B(-40,0) C(12,40) E(12,-40);
# MOSFET G(-40,0) D(12,40) S(12,-40). If item 1 (terminal dots) lands, use those.
LIB.update(IEC_PASSIVE)
