# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""IEC-style signalling and measuring symbols for the Delta Engineering electrical library
(v69 piece: lamps, buzzers and meters only - the power/protection family is a separate piece).

HONEST SCOPE: every shape below is an ORIGINAL drawing built from lines, circles and arcs, in the
general spirit of IEC 60617 signalling/measuring practice. These are NOT copies of IEC 60617
sheets, NOT certified symbols, and NOT a claim of standard compliance. Terminal names are generic;
always take real terminal numbers and ratings from the device nameplate and datasheet.

Same data format as elec_lib_data.py:
  KEY -> (arabic_label, terminals, primitives)
  primitive 'L': ('L', [(x,y), ...])           open polyline
  primitive 'C': ('C', cx, cy, r)              circle
  primitive 'A': ('A', cx, cy, r, a0_deg, a1_deg) arc, counter-clockwise from a0 to a1
"""


def _rect(x0, y0, x1, y1):
    return ('L', [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)])


def _lamp_body():
    """circle with diagonal cross, horizontal leads"""
    return [('L', [(-40, 0), (-18, 0)]), ('C', 0, 0, 18), ('L', [(18, 0), (40, 0)]),
            ('L', [(-12.7, -12.7), (12.7, 12.7)]), ('L', [(-12.7, 12.7), (12.7, -12.7)])]


def _meter_circle(letter_prims, r=20):
    """circle with horizontal leads plus letter primitives drawn from polylines"""
    return [('L', [(-40, 0), (-r, 0)]), ('C', 0, 0, r), ('L', [(r, 0), (40, 0)])] + letter_prims


LIB = {
 # ---- signalling ----
 'Signal lamp (IEC-style)': ('لمبة إشارة (نمط IEC)', ('X1', 'X2'), _lamp_body()),
 'Flashing beacon (IEC-style)': ('كشاف وامض (نمط IEC)', ('X1', 'X2'), _lamp_body() + [
    ('L', [(-16, 24), (-24, 34)]), ('L', [(0, 26), (0, 38)]), ('L', [(16, 24), (24, 34)])]),
 'Bell (IEC-style)': ('جرس (نمط IEC)', ('X1', 'X2'), [
    ('L', [(-40, 0), (-22, 0)]), ('A', 0, 0, 16, 0, 180), ('L', [(-22, 0), (22, 0)]),
    ('C', 0, -5, 2.5), ('L', [(22, 0), (40, 0)])]),
 'Buzzer (IEC-style)': ('بازر (نمط IEC)', ('X1', 'X2'), [
    ('L', [(-40, 0), (-22, 0)]), ('A', 0, 0, 16, 0, 180), ('L', [(-22, 0), (22, 0)]),
    ('L', [(22, 0), (40, 0)]), ('L', [(0, 16), (0, 22)]), ('L', [(-7, 22), (7, 28), (-7, 34), (7, 40)])]),
 'Horn (IEC-style)': ('بوق تنبيه (نمط IEC)', ('X1', 'X2'), [
    ('L', [(-40, 0), (-20, 0)]), ('L', [(-20, -8), (-20, 8), (6, 18), (6, -18), (-20, -8)]),
    ('L', [(6, 0), (40, 0)]), ('A', 14, 0, 10, 30, 90), ('A', 14, 0, 10, -90, -30)]),
 # ---- measuring ----
 'Voltmeter (IEC-style)': ('فولتميتر (نمط IEC)', ('1', '2'), _meter_circle([
    ('L', [(-8, 8), (0, -8), (8, 8)])])),
 'Ammeter (IEC-style)': ('أميتر (نمط IEC)', ('1', '2'), _meter_circle([
    ('L', [(-8, -8), (0, 9), (8, -8)]), ('L', [(-4.5, -1.5), (4.5, -1.5)])])),
 'Wattmeter (IEC-style)': ('واتميتر (نمط IEC)', ('1', '2'), _meter_circle([
    ('L', [(-9, 7), (-4.5, -7), (0, 2), (4.5, -7), (9, 7)])])),
 'Frequency meter (IEC-style)': ('مقياس التردد (نمط IEC)', ('1', '2'), _meter_circle([
    ('L', [(-12, -7), (-12, 7)]), ('L', [(-12, 0), (-4, 0)]), ('L', [(-4, -7), (-4, 7)]),
    ('L', [(0, 7), (8, 7), (0, -7), (8, -7)])], r=22)),
 'Energy meter kWh (IEC-style)': ('عداد طاقة كيلوواط ساعة (نمط IEC)', ('1', '2', '3', '4'), [
    ('L', [(-40, 0), (-20, 0)]), ('C', 0, 0, 20), ('L', [(20, 0), (40, 0)]), _rect(-7, -7, 7, 7)]),
 'Hour counter (IEC-style)': ('عداد ساعات تشغيل (نمط IEC)', ('1', '2'), [
    ('L', [(-40, 0), (-25, 0)]), _rect(-25, -15, 25, 15), ('L', [(25, 0), (40, 0)]),
    ('L', [(-5, 7), (-5, -7)]), ('A', 1, -7, 6, 0, 180), ('L', [(7, -1), (7, -7)])]),
}
