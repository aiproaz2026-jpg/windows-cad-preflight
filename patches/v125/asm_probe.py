# CI probe (headless FreeCAD 1.1.4): can the bundled Assembly module build an assembly with a grounded part
# and a revolute joint, solve it, and move a part? Records every step and error. Not a product feature yet.
import os, sys, json, traceback
import FreeCAD as App
OUT = '@@OUT@@'
os.makedirs(OUT, exist_ok=True)
R = {'steps': {}}
def save():
    open(OUT + '/asm-probe.json', 'w', encoding='utf-8').write(json.dumps(R, ensure_ascii=True, indent=1, default=str))
def step(name, fn):
    try:
        R['steps'][name] = {'ok': True, 'value': fn()}
    except Exception:
        R['steps'][name] = {'ok': False, 'error': traceback.format_exc()[-1500:]}
    save()
ctx = {}
def s_paths():
    base = App.getResourceDir()
    cands = [os.path.join(base, 'Mod', 'Assembly'), os.path.join(base, 'Mod', 'Assembly', 'Assembly')]
    for c in cands:
        if os.path.isdir(c) and c not in sys.path:
            sys.path.append(c)
    return {'resource': base, 'exists': [os.path.isdir(c) for c in cands], 'files': sorted(os.listdir(cands[0]))[:40] if os.path.isdir(cands[0]) else []}
step('paths', s_paths)
def s_import():
    import Assembly
    ctx['Assembly'] = Assembly
    return dir(Assembly)[:30]
step('import_Assembly', s_import)
def s_import_joint():
    import JointObject
    ctx['JO'] = JointObject
    return {'JointTypes': getattr(JointObject, 'JointTypes', None), 'has_Joint': hasattr(JointObject, 'Joint'), 'has_Grounded': hasattr(JointObject, 'GroundedJoint')}
step('import_JointObject', s_import_joint)
def s_build():
    import Part
    doc = App.newDocument('AsmProbe'); ctx['doc'] = doc
    asm = doc.addObject('Assembly::AssemblyObject', 'Assembly'); ctx['asm'] = asm
    joints = asm.newObject('Assembly::JointGroup', 'Joints'); ctx['joints'] = joints
    a = doc.addObject('Part::Box', 'BoxA'); b = doc.addObject('Part::Box', 'BoxB')
    a.Length = 100; a.Width = 20; a.Height = 20
    b.Length = 100; b.Width = 20; b.Height = 20
    b.Placement.Base = App.Vector(100, 0, 0)
    doc.recompute()
    for o in (a, b):
        asm.addObject(o)
    ctx['a'] = a; ctx['b'] = b
    return {'asm_group': [o.Name for o in asm.Group], 'type': asm.TypeId}
step('build_objects', s_build)
def s_ground():
    JO = ctx['JO']; joints = ctx['joints']
    g = joints.newObject('App::FeaturePython', 'GroundedJoint')
    JO.GroundedJoint(g, ctx['a'])
    ctx['doc'].recompute()
    return {'type': g.TypeId, 'ref': str(getattr(g, 'ObjectToGround', None))}
step('ground_first_part', s_ground)
def s_joint():
    JO = ctx['JO']; joints = ctx['joints']
    j = joints.newObject('App::FeaturePython', 'Revolute')
    JO.Joint(j, 1)  # index into JointTypes: expected Revolute, recorded below
    ctx['j'] = j
    a, b = ctx['a'], ctx['b']
    j.Reference1 = [a, ['Face6', 'Vertex7']]
    j.Reference2 = [b, ['Face5', 'Vertex1']]
    j.Placement1 = App.Placement(App.Vector(100, 0, 0), App.Rotation())
    j.Placement2 = App.Placement(App.Vector(0, 0, 0), App.Rotation())
    ctx['doc'].recompute()
    return {'JointType': getattr(j, 'JointType', None)}
step('add_joint', s_joint)
def s_solve():
    asm = ctx['asm']
    r = asm.solve()
    ctx['doc'].recompute()
    return {'solve_result': r, 'b_placement': str(ctx['b'].Placement), 'a_placement': str(ctx['a'].Placement)}
step('solve', s_solve)
def s_move():
    j = ctx['j']; asm = ctx['asm']; doc = ctx['doc']; b = ctx['b']
    out = {}
    # strategy 1: Angle property with limits enabled
    for ang in (0, 30, 60):
        try:
            j.EnableAngleMin = True; j.EnableAngleMax = True
            j.AngleMin = ang; j.AngleMax = ang; j.Angle = ang
            asm.solve(); doc.recompute()
            out['limits_angle_%d' % ang] = {'euler': str(b.Placement.Rotation.toEuler()), 'pos': str(b.Placement.Base)}
        except Exception as e:
            out['limits_error'] = str(e)[:200]; break
    # strategy 2: rotation offset about the joint axis through Offset2
    for ang in (0, 30, 60):
        try:
            j.EnableAngleMin = False; j.EnableAngleMax = False
            j.Offset2 = App.Placement(App.Vector(0, 0, 0), App.Rotation(App.Vector(0, 0, 1), ang))
            asm.solve(); doc.recompute()
            out['offset2_%d' % ang] = {'euler': str(b.Placement.Rotation.toEuler()), 'pos': str(b.Placement.Base)}
        except Exception as e:
            out['offset2_error'] = str(e)[:200]; break
    # strategy 3: slider joint with Distance
    try:
        import Part
        doc2 = ctx['doc']
        j.Offset2 = App.Placement()
        JO = ctx['JO']
        j.JointType = 'Slider'
        for dist in (0, 25, 50):
            j.Distance = dist
            asm.solve(); doc.recompute()
            out['slider_%d' % dist] = {'euler': str(b.Placement.Rotation.toEuler()), 'pos': str(b.Placement.Base)}
    except Exception as e:
        out['slider_error'] = str(e)[:300]
    return out
step('move_by_angle', s_move)
def s_props():
    return {'asm_props': ctx['asm'].PropertiesList, 'joint_props': ctx['j'].PropertiesList}
step('props', s_props)
R['done'] = True
save()
