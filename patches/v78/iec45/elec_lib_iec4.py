# -*- coding: utf-8 -*-
"""IEC-style electrical symbol library, power and protection family (breakers, fuses, switches, contactors).

HONEST SCOPE: every shape below is an ORIGINAL drawing built from lines, circles and arcs, drawn in the
general spirit of the IEC 60617 schematic conventions. They are NOT copies of the IEC 60617 standard,
not licensed IEC artwork, and not certified symbols. Terminal designations follow the markings documented
by ABB for contactors and protection devices (main poles 1L1/3L2/5L3 to 2T1/4T2/6T3, coil A1/A2,
auxiliary NO 13-14, NC 21-22), source: ABB Low Voltage Products catalogue, section "Terminal Marking and
Positioning", https://files.kempstoncontrols.com/files/6cc38b9721026dca8234783b3beacbbc/1SBN010010R1001.pdf
Always take real terminal numbers and ratings from the device nameplate and datasheet.

Same format as elec_lib_data.LIB: KEY -> (arabic_label, terminals, primitives)
  primitive 'L': ('L', [(x,y), ...])            open polyline
  primitive 'C': ('C', cx, cy, r)               circle
  primitive 'A': ('A', cx, cy, r, a0_deg, a1_deg) arc, counter-clockwise from a0 to a1

Two-terminal symbols keep their leads horizontal on y=0 ending at x=-35 and x=+35, so the v67
term_ends lead-end terminal table picks them up exactly like the stock two-terminal symbols.
Three-pole symbols keep the +-45 x / +-35 y envelope of the stock 3P symbols so the stock
multi-terminal layout lands the same way. GPL-3.0-or-later.
"""


def _rect(x0, y0, x1, y1):
    return ('L', [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)])


def _dot(x, y, r=2.5):
    """terminal/contact junction dot (outline circle; fill is not available in the primitive set)"""
    return ('C', x, y, r)


def _contact_no_h():
    """Horizontal IEC-style normally-open contact: lead, junction dot, open blade, dot, lead."""
    return [
        ('L', [(-35, 0), (-15, 0)]),
        _dot(-15, 0),
        ('L', [(-15, 0), (12, 16)]),      # open blade, hinged at the left dot
        _dot(15, 0),
        ('L', [(15, 0), (35, 0)]),
    ]


def _nc_tick(tip_x=12, tip_y=16):
    """short crossbar at the blade tip marking a normally-closed contact"""
    return ('L', [(tip_x - 2, tip_y + 3), (tip_x + 2, tip_y - 3)])


def _contactor_arc(tip_x=12, tip_y=16):
    """small semicircle at the blade tip marking a power-contactor contact"""
    return ('A', tip_x, tip_y, 4.5, -45, 135)


def _breaker_x(tip_x, tip_y):
    """X mark at the blade tip marking an automatic (circuit-breaker) contact"""
    return [('L', [(tip_x - 4, tip_y - 4), (tip_x + 4, tip_y + 4)]),
            ('L', [(tip_x - 4, tip_y + 4), (tip_x + 4, tip_y - 4)])]


def _pole_v(x, marker):
    """One vertical pole of a 3-pole device: upper lead, dot, blade down-left, marker at tip, lower dot and lead."""
    prims = [
        ('L', [(x, 35), (x, 12)]),
        _dot(x, 12),
        ('L', [(x, 12), (x - 10, -6)]),
        _dot(x, -10),
        ('L', [(x, -10), (x, -35)]),
    ]
    if marker == 'x':
        prims += _breaker_x(x - 10, -6)
    elif marker == 'arc':
        prims.append(_contactor_arc(x - 10, -6))
    return prims


_COUPLING = [('L', [(-38, 0), (-31, 0)]), ('L', [(-10, 0), (-3, 0)]), ('L', [(18, 0), (25, 0)])]  # dashed mechanical link


LIB_IEC = {
 # ---- fuses ----
 'Fuse (IEC)': ('فيوز (IEC)', ('1', '2'),
    [('L', [(-35, 0), (35, 0)]), _rect(-14, -5, 14, 5)]),
 # ---- switches ----
 'Switch NO (IEC)': ('مفتاح مفتوح عادة (IEC)', ('1', '2'), _contact_no_h()),
 'Switch NC (IEC)': ('مفتاح مغلق عادة (IEC)', ('1', '2'), _contact_no_h() + [_nc_tick()]),
 'Disconnector (IEC)': ('مفتاح فصل (IEC)', ('1', '2'),
    _contact_no_h() + [('L', [(12, 16), (12, 24)])]),   # open-contact blade with an end tick
 # ---- breakers ----
 'Breaker 1P (IEC)': ('قاطع قطب واحد (IEC)', ('1', '2'),
    _contact_no_h() + _breaker_x(12, 16)),
 'Motor protection breaker (IEC)': ('قاطع حماية محرك (IEC)', ('1', '2'),
    [('L', [(-35, 0), (-15, 0)]), _dot(-15, 0), ('L', [(-15, 0), (6, 14)])]
    + _breaker_x(6, 14)
    + [_dot(8, 0), ('L', [(8, 0), (12, 0)]), _rect(12, -4, 24, 4), ('L', [(24, 0), (35, 0)])]),
 'Breaker 3P (IEC)': ('قاطع ثلاثي الأقطاب (IEC)', ('1', '2', '3', '4', '5', '6'),
    [_rect(-45, -35, 45, 35)] + _pole_v(-28, 'x') + _pole_v(0, 'x') + _pole_v(28, 'x') + _COUPLING),
 # ---- contactors ----
 'Contactor NO contact (IEC)': ('ملامس كونتاكتور NO (IEC)', ('13', '14'),
    _contact_no_h() + [_contactor_arc()]),
 'Contactor NC contact (IEC)': ('ملامس كونتاكتور NC (IEC)', ('21', '22'),
    _contact_no_h() + [_nc_tick(), _contactor_arc()]),
 'Contactor 3P (IEC)': ('كونتاكتور ثلاثي الأقطاب (IEC)', ('1L1', '2T1', '3L2', '4T2', '5L3', '6T3', 'A1', 'A2'),
    [_rect(-45, -35, 45, 35)] + _pole_v(-28, 'arc') + _pole_v(0, 'arc') + _pole_v(28, 'arc') + _COUPLING),
}
