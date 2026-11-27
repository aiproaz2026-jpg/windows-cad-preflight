# -*- coding: utf-8 -*-
"""IEC-style electrical symbol library data (editable). GPL-3.0-or-later.

HONEST SCOPE: every shape below is an ORIGINAL drawing, built from lines, circles and arcs, that follows the
general drafting conventions of IEC 60617-style schematics (rectangle resistor, slanted-blade contacts with
small contact circles, circle instruments, two-circle transformer, crossed breaker contact, decreasing-line
earth). These are NOT copies of the published IEC 60617 database, NOT taken from any standard document, and
are not certified symbols; proportions and details are approximations drawn by the project.
Terminal designations follow the markings documented by ABB for contactors, auxiliary contacts and overload
relays (main poles 1L1/3L2/5L3 to 2T1/4T2/6T3, coil A1/A2, auxiliary NO 13-14, NC 21-22, overload NC 95-96
and NO 97-98), source: ABB Low Voltage Products catalogue, section "Terminal Marking and Positioning"
(IEC 60445, IEC 60947-1, EN 50005, EN 50011, EN 50012 referenced there),
https://files.kempstoncontrols.com/files/6cc38b9721026dca8234783b3beacbbc/1SBN010010R1001.pdf
Always take real terminal numbers and ratings from the device nameplate and datasheet.

Same format as elec_lib_data.py: KEY -> (arabic_label, terminals, primitives)
  primitive 'L': ('L', [(x,y), ...])            open polyline
  primitive 'C': ('C', cx, cy, r)               circle
  primitive 'A': ('A', cx, cy, r, a0_deg, a1_deg) arc, counter-clockwise from a0 to a1

Keys end in '(IEC-style)'. They live next to the '(illustr.)' set: symbols_append3 merges LIB_IEC into
V60_LIB, so the existing renderer, the library editor and the term_ends terminal-dot table pick them up
unchanged. Sizes and lead positions match the '(illustr.)' set (two-terminal symbols span x -40..+40,
coils/contacts span y -40..+40) so demo sheets can swap key names without rewiring.
"""


def _rect(x0, y0, x1, y1):
    return ('L', [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)])


def _contact_no(x, y0=-20, y1=20):
    """vertical normally-open contact: lead, gap, slanted blade (IEC 60617 contact convention)"""
    return [('L', [(x, y0), (x, y0 + 10)]), ('L', [(x, y0 + 10), (x + 10, y1 - 12)]), ('L', [(x, y1 - 8), (x, y1)])]


def _contact_nc(x, y0=-20, y1=20):
    """vertical normally-closed contact: NO contact with a diagonal slash through the blade (IEC convention)"""
    return _contact_no(x, y0, y1) + [('L', [(x, 2), (x + 10, -4)])]


def _switch_no():
    """horizontal NO switch with small open circles at the fixed contact points (IEC convention)"""
    return [('L', [(-35, 0), (-15, 0)]), ('C', -15, 0, 2), ('L', [(-15, 0), (20, 25)]), ('C', 25, 0, 2), ('L', [(25, 0), (35, 0)])]


def _switch_nc():
    """horizontal NC switch: closed blade between the contact circles (IEC convention)"""
    return [('L', [(-35, 0), (-15, 0)]), ('C', -15, 0, 2), ('L', [(-15, 0), (25, 0)]), ('C', 25, 0, 2), ('L', [(25, 0), (35, 0)])]


def _actuator_stem(x=5, y0=9, y1=35, bar=(-8, 18)):
    """pushbutton actuator: vertical stem with a horizontal bar on top (IEC 'push' marking)"""
    return [('L', [(x, y0), (x, y1)]), ('L', [(bar[0], y1), (bar[1], y1)])]


LIB_IEC = {
 'Resistor (IEC-style)': ('مقاومة (نمط IEC)', ('1', '2'), [('L', [(-40, 0), (-24, 0)]), _rect(-24, -9, 24, 9), ('L', [(24, 0), (40, 0)])]),
 'Variable resistor (IEC-style)': ('مقاومة متغيرة (نمط IEC)', ('1', '2'), [('L', [(-40, 0), (-24, 0)]), _rect(-24, -9, 24, 9), ('L', [(24, 0), (40, 0)]), ('L', [(-18, -20), (18, 20)]), ('L', [(11, 20), (18, 20), (18, 13)])]),
 'Capacitor (IEC-style)': ('مكثف (نمط IEC)', ('1', '2'), [('L', [(-40, 0), (-5, 0)]), ('L', [(-5, -16), (-5, 16)]), ('L', [(5, -16), (5, 16)]), ('L', [(5, 0), (40, 0)])]),
 'Inductor (IEC-style)': ('ملف حث (نمط IEC)', ('1', '2'), [('L', [(-40, 0), (-30, 0)]), ('A', -22.5, 0, 7.5, 0, 180), ('A', -7.5, 0, 7.5, 0, 180), ('A', 7.5, 0, 7.5, 0, 180), ('A', 22.5, 0, 7.5, 0, 180), ('L', [(30, 0), (40, 0)])]),
 'Diode (IEC-style)': ('دايود (نمط IEC)', ('A', 'K'), [('L', [(-40, 0), (-10, 0)]), ('L', [(-10, -14), (-10, 14), (12, 0), (-10, -14)]), ('L', [(12, -14), (12, 14)]), ('L', [(12, 0), (40, 0)])]),
 'LED (IEC-style)': ('دايود مضيء (نمط IEC)', ('A', 'K'), [('L', [(-40, 0), (-10, 0)]), ('L', [(-10, -14), (-10, 14), (12, 0), (-10, -14)]), ('L', [(12, -14), (12, 14)]), ('L', [(12, 0), (40, 0)]), ('L', [(-2, 18), (6, 28)]), ('L', [(6, 18), (14, 28)])]),
 'Battery (IEC-style)': ('بطارية (نمط IEC)', ('+', '-'), [('L', [(-40, 0), (-8, 0)]), ('L', [(-8, -18), (-8, 18)]), ('L', [(0, -9), (0, 9)]), ('L', [(8, -18), (8, 18)]), ('L', [(16, -9), (16, 9)]), ('L', [(16, 0), (40, 0)])]),
 'AC source (IEC-style)': ('مصدر تيار متردد (نمط IEC)', ('1', '2'), [('C', 0, 0, 22), ('L', [(-40, 0), (-22, 0)]), ('L', [(22, 0), (40, 0)]), ('A', -8, 0, 8, 0, 180), ('A', 8, 0, 8, 180, 360)]),
 'Lamp (IEC-style)': ('لمبة بيان (نمط IEC)', ('X1', 'X2'), [('C', 0, 0, 18), ('L', [(-40, 0), (-18, 0)]), ('L', [(18, 0), (40, 0)]), ('L', [(-12.7, -12.7), (12.7, 12.7)]), ('L', [(-12.7, 12.7), (12.7, -12.7)])]),
 'Buzzer (IEC-style)': ('جرس تنبيه (نمط IEC)', ('X1', 'X2'), [('L', [(-40, 0), (-14, 0)]), ('A', 0, 0, 14, 90, 270), ('L', [(0, 14), (0, -14)]), ('L', [(0, 14), (16, 14), (16, -14), (0, -14)]), ('L', [(16, 0), (40, 0)])]),
 'Ground (IEC-style)': ('أرضي (نمط IEC)', ('PE',), [('L', [(0, 28), (0, 0)]), ('L', [(-30, 0), (30, 0)]), ('L', [(-20, -10), (20, -10)]), ('L', [(-10, -20), (10, -20)])]),
 'Terminal (IEC-style)': ('كلمة توصيل (نمط IEC)', ('1',), [('C', 0, 0, 7), ('L', [(0, 7), (0, 25)])]),
 'Switch NO (IEC-style)': ('مفتاح مفتوح عادة (نمط IEC)', ('1', '2'), _switch_no()),
 'Switch NC (IEC-style)': ('مفتاح مغلق عادة (نمط IEC)', ('1', '2'), _switch_nc()),
 'Pushbutton NO (IEC-style)': ('ضاغط NO (نمط IEC)', ('13', '14'), _switch_no() + _actuator_stem(5, 12, 35)),
 'Pushbutton NC (IEC-style)': ('ضاغط NC (نمط IEC)', ('21', '22'), _switch_nc() + _actuator_stem(5, 2, 35)),
 'Emergency stop (IEC-style)': ('ضاغط طوارئ (نمط IEC)', ('21', '22'), _switch_nc() + [('L', [(5, 2), (5, 25)]), ('A', 5, 25, 14, 0, 180)]),
 'Selector switch (IEC-style)': ('مفتاح اختيار (نمط IEC)', ('1', '2', '3'), [('L', [(-35, 0), (-15, 0)]), ('C', -15, 0, 2), ('L', [(-15, 0), (20, 22)]), ('C', 25, 22, 2), ('L', [(25, 22), (35, 22)]), ('C', 25, -22, 2), ('L', [(25, -22), (35, -22)]), ('L', [(-6, 6), (-6, 30)]), ('L', [(-12, 30), (0, 30)])]),
 'Limit switch (IEC-style)': ('مفتاح نهاية شوط (نمط IEC)', ('13', '14'), _switch_no() + [('L', [(5, 12), (5, 28)]), ('C', 5, 34, 6)]),
 'Float switch (IEC-style)': ('مفتاح عوامة (نمط IEC)', ('1', '2'), _switch_no() + [('L', [(5, 12), (5, 26)]), ('A', 5, 34, 8, 0, 360)]),
 'Pressure switch (IEC-style)': ('مفتاح ضغط (نمط IEC)', ('1', '2'), _switch_no() + [('L', [(5, 12), (5, 24)]), ('L', [(-5, 24), (15, 24)]), ('L', [(-5, 24), (5, 40), (15, 24)])]),
 'Flow switch (IEC-style)': ('مفتاح سريان (نمط IEC)', ('1', '2'), _switch_no() + [('L', [(5, 12), (5, 26)]), ('L', [(-5, 26), (15, 26), (5, 40), (-5, 26)])]),
 'Relay coil (IEC-style)': ('ملف ريليه (نمط IEC)', ('A1', 'A2'), [('L', [(0, 40), (0, 20)]), _rect(-14, -20, 14, 20), ('L', [(0, -20), (0, -40)])]),
 'Contactor coil (IEC-style)': ('ملف كونتاكتور (نمط IEC)', ('A1', 'A2'), [('L', [(0, 40), (0, 20)]), _rect(-14, -20, 14, 20), ('L', [(-14, -20), (14, 20)]), ('L', [(0, -20), (0, -40)])]),
 'Timer coil ON-delay (IEC-style)': ('ملف مؤقت تأخير توصيل (نمط IEC)', ('A1', 'A2'), [('L', [(0, 40), (0, 20)]), _rect(-14, -20, 14, 20), ('L', [(-14, 0), (14, 0)]), ('L', [(0, -20), (0, -40)])]),
 'Solenoid valve coil (IEC-style)': ('ملف محبس كهرومغناطيسي (نمط IEC)', ('A1', 'A2'), [('L', [(0, 40), (0, 20)]), _rect(-14, -20, 14, 20), ('L', [(-14, 12), (14, 12)]), ('L', [(-14, -12), (14, -12)]), ('L', [(0, -20), (0, -40)])]),
 'Contact NO (IEC-style)': ('ملامس NO (نمط IEC)', ('13', '14'), _contact_no(0)),
 'Contact NC (IEC-style)': ('ملامس NC (نمط IEC)', ('21', '22'), _contact_nc(0)),
 'Fuse (IEC-style)': ('فيوز (نمط IEC)', ('1', '2'), [_rect(-24, -9, 24, 9), ('L', [(-40, 0), (40, 0)])]),
 'Breaker 1P (IEC-style)': ('قاطع قطب واحد (نمط IEC)', ('1', '2'), [('L', [(0, 40), (0, 20)]), ('C', 0, 20, 2), ('L', [(0, 20), (12, -12)]), ('C', 0, -12, 2), ('L', [(0, -12), (0, -40)]), ('L', [(-6, -6), (6, -18)]), ('L', [(-6, -18), (6, -6)])]),
 'Breaker 3P (IEC-style)': ('قاطع ثلاثي الأقطاب (نمط IEC)', ('1', '2', '3', '4', '5', '6'), [_rect(-45, -35, 45, 35), ('L', [(-38, -15), (-22, 15)]), ('L', [(-12, -15), (2, 15)]), ('L', [(14, -15), (28, 15)]), ('L', [(-11, 6), (1, -6)]), ('L', [(-11, -6), (1, 6)])]),
 'Contactor 3P (IEC-style)': ('كونتاكتور ثلاثي الأقطاب (نمط IEC)', ('1L1', '2T1', '3L2', '4T2', '5L3', '6T3', 'A1', 'A2'), [_rect(-45, -35, 45, 35), ('L', [(-30, -20), (-30, 20)]), ('L', [(0, -20), (0, 20)]), ('L', [(30, -20), (30, 20)]), ('L', [(-30, 0), (-20, 8)]), ('L', [(0, 0), (10, 8)]), ('L', [(30, 0), (40, 8)])]),
 'Overload relay (IEC-style)': ('ريليه حمل زائد حراري (نمط IEC)', ('1L1', '2T1', '3L2', '4T2', '5L3', '6T3', '95', '96'), [_rect(-45, -35, 45, 35), ('L', [(-30, -15), (-20, 15), (-10, -15), (0, 15), (10, -15), (20, 15), (30, -15)])]),
 'Motor 3-phase (IEC-style)': ('محرك ثلاثي الأطوار (نمط IEC)', ('U1', 'V1', 'W1', 'PE'), [('C', 0, 0, 35), ('A', -10, 0, 10, 0, 180), ('A', 10, 0, 10, 180, 360), ('L', [(-26, 14), (-26, 26)]), ('L', [(-32, 20), (-20, 20)])]),
 'Motor 1-phase (IEC-style)': ('محرك أحادي الطور (نمط IEC)', ('U1', 'U2', 'PE'), [('C', 0, 0, 30), ('A', -8, 0, 8, 0, 180), ('A', 8, 0, 8, 180, 360)]),
 'Transformer (IEC-style)': ('محول (نمط IEC)', ('1', '2', '3', '4'), [('C', -9, 0, 16), ('C', 9, 0, 16)]),
 'Voltmeter (IEC-style)': ('فولتميتر (نمط IEC)', ('1', '2'), [('C', 0, 0, 20), ('L', [(-40, 0), (-20, 0)]), ('L', [(20, 0), (40, 0)]), ('L', [(-9, 8), (0, -9), (9, 8)])]),
 'Ammeter (IEC-style)': ('أميتر (نمط IEC)', ('1', '2'), [('C', 0, 0, 20), ('L', [(-40, 0), (-20, 0)]), ('L', [(20, 0), (40, 0)]), ('L', [(-9, -9), (0, 9), (9, -9)]), ('L', [(-6, -2), (6, -2)])]),
 'Heater element (IEC-style)': ('سخان (نمط IEC)', ('1', '2'), [_rect(-24, -12, 24, 12), ('L', [(-40, 0), (-24, 0)]), ('L', [(24, 0), (40, 0)]), ('L', [(-16, -12), (-16, 12)]), ('L', [(0, -12), (0, 12)]), ('L', [(16, -12), (16, 12)])]),
 'VFD block (IEC-style)': ('مغير سرعة VFD (نمط IEC)', ('L1', 'L2', 'L3', 'U', 'V', 'W', 'PE'), [_rect(-55, -40, 55, 40), ('L', [(-55, -40), (55, 40)]), ('A', -28, 22, 6, 0, 180), ('A', -16, 22, 6, 180, 360), ('A', 28, -22, 6, 0, 180), ('A', 16, -22, 6, 180, 360)]),
 'PLC block (IEC-style)': ('وحدة PLC (نمط IEC)', ('L+', 'M', 'I0.0', 'I0.1', 'Q0.0', 'Q0.1'), [_rect(-60, -45, 60, 45), ('L', [(-60, 25), (60, 25)]), ('L', [(-60, -25), (60, -25)])]),
}
