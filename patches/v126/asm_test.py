# CI test (headless FreeCAD 1.1.4): the Delta simple-assembly helper. Evidence only.
import os, sys, json, math, traceback, glob
import FreeCAD as App
OUT = '@@OUT@@'
os.makedirs(OUT, exist_ok=True)
R = {'steps': {}}
def save():
    open(OUT + '/asm-test.json', 'w', encoding='utf-8').write(json.dumps(R, ensure_ascii=True, indent=1, default=str))
try:
    try:
        from DeltaEngineering import assembly_simple as AS
    except ImportError:
        for p in glob.glob(r'C:/DeltaTest/Mod/*') + glob.glob(r'C:/DeltaLic/Mod/*'):
            if os.path.isdir(p) and p not in sys.path: sys.path.append(p)
        from DeltaEngineering import assembly_simple as AS
    import Part
    doc = App.newDocument('AsmTest')
    a = doc.addObject('Part::Box', 'BoxA'); b = doc.addObject('Part::Box', 'BoxB')
    for o in (a, b):
        o.Length = 100; o.Width = 20; o.Height = 20
    b.Placement.Base = App.Vector(100, 0, 0)
    doc.recompute()
    info = AS.make_assembly(doc, a, b, 'Revolute', 'Z', App.Vector(100, 10, 0))
    R['steps']['make'] = {'solve_result': info['solve_result'], 'a_pos': str(a.Placement.Base), 'b_pos0': str(b.Placement.Base)}
    save()
    rows = []
    for ang in (0, 30, 60, -45):
        code = AS.move(info, ang)
        yaw = b.Placement.Rotation.toEuler()[0]
        # world position of the joint point on B: B placement applied to the local origin of B's joint frame
        pt = b.Placement.multVec(App.Vector(0, 0, 0))
        rows.append({'angle_set': ang, 'solve': code, 'b_yaw_deg': yaw, 'b_origin': str(pt),
                     'pivot_dev_mm': (pt - App.Vector(100, 10, 0)).Length, 'a_moved': (a.Placement.Base - App.Vector(0, 0, 0)).Length})
    R['steps']['revolute'] = rows
    R['revolute_rotation_ok'] = all(abs(abs(r['b_yaw_deg']) - abs(r['angle_set'])) < 1e-6 for r in rows) and all(r['solve'] == 0 for r in rows)
    R['pivot_ok'] = all(r['pivot_dev_mm'] < 1e-3 for r in rows)
    save()
    # slider (recorded, not asserted)
    doc2 = App.newDocument('AsmTest2')
    c = doc2.addObject('Part::Box', 'BoxC'); d = doc2.addObject('Part::Box', 'BoxD')
    for o in (c, d):
        o.Length = 100; o.Width = 20; o.Height = 20
    d.Placement.Base = App.Vector(100, 0, 0)
    doc2.recompute()
    i2 = AS.make_assembly(doc2, c, d, 'Slider', 'X', App.Vector(100, 0, 0))
    srows = []
    for dist in (0, 25, 50):
        code = AS.move(i2, dist)
        srows.append({'shift_set': dist, 'solve': code, 'd_pos': str(d.Placement.Base)})
    R['steps']['slider'] = srows
except Exception:
    R['error'] = traceback.format_exc()[-2500:]
R['done'] = True
save()
