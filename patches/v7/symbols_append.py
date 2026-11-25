

# ---- v7 additions: original illustrative power-circuit symbols (not IEC/ANSI, terminal labels are generic) ----
TEMPLATES.update({
 'Breaker concept':('قاطع ثلاثي الأقطاب توضيحي، غير قياسي',('1','2','3','4','5','6')),
 'Contactor concept':('كونتاكتور توضيحي، غير قياسي',('1','2','3','4','5','6','A1','A2')),
 'Overload concept':('حمل زائد حراري توضيحي، غير قياسي',('1','2','3','4','5','6')),
 'Fuse concept':('فيوز توضيحي، غير قياسي',('1','2')),
 'Pushbutton concept':('ضاغط توضيحي، غير قياسي',('1','2'))})
_outline_v6 = outline


def outline(device):
    kind = device.SymbolTemplate
    p = device.Position

    def v(x, y):
        return p + App.Vector(x, y, 0)

    def line(a, b):
        return Part.makeLine(v(*a), v(*b))

    def poly(points):
        return Part.makePolygon([v(x, y) for x, y in points])
    if kind == 'Breaker concept':
        return [poly([(-45, -30), (-45, 30), (45, 30), (45, -30), (-45, -30)]), line((-25, -15), (15, 15)), line((-25, 0), (-5, 0))]
    if kind == 'Contactor concept':
        return [poly([(-45, -30), (-45, 30), (45, 30), (45, -30), (-45, -30)]), line((-30, -20), (-30, 20)), line((0, -20), (0, 20)), line((30, -20), (30, 20)),
                line((-30, 0), (-20, 8)), line((0, 0), (10, 8)), line((30, 0), (40, 8))]
    if kind == 'Overload concept':
        return [poly([(-45, -30), (-45, 30), (45, 30), (45, -30), (-45, -30)]), poly([(-30, -15), (-20, 15), (-10, -15), (0, 15), (10, -15), (20, 15), (30, -15)])]
    if kind == 'Fuse concept':
        return [poly([(-35, -12), (-35, 12), (35, 12), (35, -12), (-35, -12)]), line((-50, 0), (50, 0))]
    if kind == 'Pushbutton concept':
        return [line((-35, 0), (-15, 0)), line((-15, 0), (20, 18)), line((25, 0), (35, 0)), line((5, 9), (5, 35)), line((-8, 35), (18, 35))]
    return _outline_v6(device)
