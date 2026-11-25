import os, sys, json, math, time, traceback
OUT = os.environ.get('DELTA_OUT', 'C:/fit11')
PKG = os.environ.get('DELTA_PKG_PARENT')
if PKG and PKG not in sys.path:
    sys.path.insert(0, PKG)
os.makedirs(OUT, exist_ok=True)
res = {'steps': {}, 'done': False}


def save():
    open(OUT + '/fittings-result.json', 'w', encoding='utf-8').write(json.dumps(res, ensure_ascii=False, indent=1, default=str))


def run(name, fn):
    t = time.time()
    try:
        d = fn()
        res['steps'][name] = {'ok': True, 'secs': round(time.time() - t, 2), 'detail': d}
    except Exception:
        res['steps'][name] = {'ok': False, 'secs': round(time.time() - t, 2), 'error': traceback.format_exc()}
    save()


def rel(a, b):
    return abs(a - b) / max(abs(b), 1e-12)


try:
    import FreeCAD as App, Part
    from DeltaEngineering import fittings as F
    from DeltaEngineering.tube_library import PRESETS
    doc = App.newDocument('Station')
    doc.UndoMode = 1
    P = PRESETS

    def r_of(nps):
        return P[nps]['od_mm'] / 2, P[nps]['od_mm'] / 2 - P[nps]['wall_mm']

    def s_formula():
        out = {}
        # reducer NPS 4 -> 2, independent frustum formula
        red = F.create_fitting(doc, 'reducer', '4', '2')
        R1, r1 = r_of('4'); R2, r2 = r_of('2'); h = red.Length.Value
        exp = math.pi * h / 3 * ((R1 * R1 + R1 * R2 + R2 * R2) - (r1 * r1 + r1 * r2 + r2 * r2))
        out['reducer_volume'] = red.Shape.Volume; out['reducer_expected'] = exp
        assert rel(red.Shape.Volume, exp) < 1e-6, 'reducer volume vs formula'
        # flange, independent annulus formula
        fl = F.create_fitting(doc, 'flange', '3')
        R, r = r_of('3'); fod = 1.6 * P['3']['od_mm'] + 20.0; t = fl.Length.Value
        exp2 = math.pi * t * ((fod / 2) ** 2 - r * r)
        out['flange_volume'] = fl.Shape.Volume; out['flange_expected'] = exp2
        assert rel(fl.Shape.Volume, exp2) < 1e-6, 'flange volume vs formula'
        for k in ('gate_valve', 'ball_valve', 'check_valve'):
            v = F.create_fitting(doc, k, '2')
            assert v.Shape.isValid() and len(v.Shape.Solids) == 1, k
            bb = v.Shape.BoundBox
            c0, c1 = v.PortCenters
            assert bb.XMin <= c0.x + 1e-6 and bb.XMax >= c1.x - 1e-6, k + ' ports inside bbox'
            out[k + '_volume'] = round(v.Shape.Volume, 1)
        pump = F.create_fitting(doc, 'pump', '3', '2')
        assert pump.Shape.isValid() and len(pump.Shape.Solids) == 1
        out['pump_ports'] = [[round(c.x, 2), round(c.y, 2), round(c.z, 2)] for c in pump.PortCenters]
        for o in list(doc.Objects):
            if hasattr(o, 'FittingKind'):
                doc.removeObject(o.Name)
        doc.recompute()
        return out
    run('formula_volumes_and_validity', s_formula)

    chain = {}

    def s_station():
        pump = F.create_fitting(doc, 'pump', '3', '2')
        pump.Placement = App.Placement(App.Vector(1000, -400, 250), App.Rotation(App.Vector(1, 2, 3), 37))
        doc.recompute()
        chain['pump'] = pump
        joints = []

        f1 = F.create_fitting(doc, 'flange', '2'); F.snap(doc, f1, 0, pump, 1); joints.append((f1, pump))
        v1 = F.create_fitting(doc, 'gate_valve', '2'); F.snap(doc, v1, 0, f1, 1); joints.append((v1, f1))
        f2 = F.create_fitting(doc, 'flange', '2'); F.snap(doc, f2, 0, v1, 1); joints.append((f2, v1))
        rd = F.create_fitting(doc, 'reducer', '2', '4'); F.snap(doc, rd, 0, f2, 1); joints.append((rd, f2))
        bv = F.create_fitting(doc, 'ball_valve', '4'); F.snap(doc, bv, 0, rd, 1); joints.append((bv, rd))
        # suction side: pump.0 (NPS 3)
        s1 = F.create_fitting(doc, 'flange', '3'); F.snap(doc, s1, 0, pump, 0); joints.append((s1, pump))
        cv = F.create_fitting(doc, 'check_valve', '3'); F.snap(doc, cv, 0, s1, 1); joints.append((cv, s1))
        chain.update(dict(f1=f1, v1=v1, f2=f2, rd=rd, bv=bv, s1=s1, cv=cv, joints=joints))
        # independent geometric verification of every joint using Placement math only
        worst_d = 0.0; worst_a = 0.0
        for a, b in joints:
            pa = F.ports(a); pb = F.ports(b)
            best = None
            for ca, da, oa in pa:
                for cb, db, ob in pb:
                    d = (ca - cb).Length
                    if best is None or d < best[0]:
                        best = (d, da.dot(db), abs(oa - ob))
            worst_d = max(worst_d, best[0]); worst_a = max(worst_a, abs(best[1] + 1))
            assert best[2] < 1e-6
        assert worst_d < 0.01 and worst_a < 1e-6, (worst_d, worst_a)
        rep = F.check_continuity(doc)
        assert rep['ok'], rep
        assert len(rep['connected']) == 7, rep
        assert len(rep['open_ports']) == 2, rep['open_ports']
        return {'joints': len(rep['connected']), 'open_ports': rep['open_ports'], 'worst_center_gap_mm': worst_d,
                'worst_direction_error': worst_a, 'errors': rep['errors']}
    run('station_snap_rotated_continuity', s_station)

    def s_mismatch():
        rd = chain['rd']
        before = App.Placement(chain['bv'].Placement)
        fl4 = F.create_fitting(doc, 'flange', '4')
        place_before = App.Placement(fl4.Placement)
        refused = ''
        try:
            F.snap(doc, fl4, 0, chain['f1'], 1)  # NPS4 flange against NPS2 flange port
        except ValueError as e:
            refused = str(e)
        assert 'mismatch' in refused, refused
        assert fl4.Placement.isSame(place_before, 1e-9)
        doc.removeObject(fl4.Name); doc.recompute()
        # deliberately broken chain: move a flange by 5 mm along its axis -> open ports and no silent pass
        v = chain['v1']; old = App.Placement(v.Placement)
        v.Placement = App.Placement(old.Base + App.Vector(5, 0, 0), old.Rotation); doc.recompute()
        rep = F.check_continuity(doc)
        broken_open = len(rep['open_ports'])
        v.Placement = old; doc.recompute()
        rep2 = F.check_continuity(doc)
        assert broken_open > 2 and rep2['ok'] and len(rep2['open_ports']) == 2, (broken_open, rep2)
        return {'mismatch_message': refused, 'placement_unchanged': True, 'open_ports_when_displaced_5mm': broken_open}
    run('mismatch_refused_and_displacement_detected', s_mismatch)

    def s_overlap():
        ov = F.create_fitting(doc, 'gate_valve', '2')
        ov.Placement = App.Placement(chain['pump'].Placement.Base, chain['pump'].Placement.Rotation); doc.recompute()
        rep = F.check_continuity(doc)
        found = [e for e in rep['errors'] if e.startswith('Overlap')]
        doc.removeObject(ov.Name); doc.recompute()
        rep2 = F.check_continuity(doc)
        assert found and rep2['ok'], (found, rep2)
        return {'overlap_reports': len(found)}
    run('overlap_detected_then_cleared', s_overlap)

    def s_undo():
        nf = F.create_fitting(doc, 'flange', '2')
        p0 = App.Placement(nf.Placement)
        # snap to the free end of pump suction check valve (NPS3) would mismatch; use free end of ball valve (NPS4)
        nf4 = F.create_fitting(doc, 'flange', '4'); q0 = App.Placement(nf4.Placement)
        F.snap(doc, nf4, 0, chain['bv'], 1)
        moved = not nf4.Placement.isSame(q0, 1e-6)
        doc.undo(); doc.recompute()
        restored = nf4.Placement.isSame(q0, 1e-9)
        doc.redo(); doc.recompute()
        redone = not nf4.Placement.isSame(q0, 1e-6)
        assert moved and restored and redone, (moved, restored, redone)
        chain['end_flange'] = nf4
        doc.removeObject(nf.Name); doc.recompute()
        return {'moved': moved, 'undo_restored': restored, 'redo_reapplied': redone}
    run('snap_undo_redo', s_undo)

    expected_bom = {}

    def s_bom():
        rows = F.takeoff(doc)
        got = {(r['kind'], r['size']): r['qty'] for r in rows}
        exp = {('pump', 'NPS 3 x NPS 2'): 1, ('flange', 'NPS 2'): 2, ('gate_valve', 'NPS 2'): 1, ('reducer', 'NPS 2 x NPS 4'): 1,
               ('ball_valve', 'NPS 4'): 1, ('flange', 'NPS 3'): 1, ('check_valve', 'NPS 3'): 1, ('flange', 'NPS 4'): 1}
        assert got == exp, (got, exp)
        path = OUT + '/takeoff.csv'
        F.takeoff_csv(doc, path)
        text = open(path, encoding='utf-8-sig').read()
        assert 'Matching port diameter is geometric continuity only' in text and 'item,kind,size,qty,unit' in text
        return {'rows': rows, 'csv_has_scope_notice': True}
    run('quantity_takeoff_matches_independent_list', s_bom)

    def s_reopen_step():
        folder = OUT + '/مشروع محطة'
        os.makedirs(folder, exist_ok=True)
        path = folder + '/محطة.FCStd'
        names = [o.Name for o in doc.Objects if hasattr(o, 'FittingKind')]
        vols = {n: doc.getObject(n).Shape.Volume for n in names}
        doc.saveAs(path)
        App.closeDocument(doc.Name)
        d2 = App.openDocument(path)
        d2.recompute()
        diffs = max(abs(d2.getObject(n).Shape.Volume - v) for n, v in vols.items())
        rep = F.check_continuity(d2)
        assert diffs < 1e-6 and rep['ok'] and len(rep['connected']) == 8, (diffs, rep)
        step = OUT + '/station.step'
        objs = [d2.getObject(n) for n in names]
        Part.export(objs, step)
        imp = Part.read(step)
        total = sum(vols.values())
        assert rel(imp.Volume, total) < 1e-5, (imp.Volume, total)
        res['_doc2'] = d2.Name
        return {'objects': len(names), 'max_volume_diff_after_reopen': diffs, 'connections_after_reopen': len(rep['connected']),
                'ok_after_reopen': rep['ok'], 'step_volume': imp.Volume, 'sum_volume': total, 'step_bytes': os.path.getsize(step)}
    run('arabic_path_save_reopen_and_step', s_reopen_step)

    def s_scale():
        d3 = App.newDocument('Scale')
        t0 = time.time()
        first = F.create_fitting(d3, 'flange', '2')
        prev = first; n = 1
        kinds = ['gate_valve', 'flange', 'check_valve', 'flange']
        while n < 60:
            o = F.create_fitting(d3, kinds[n % 4], '2'); F.snap(d3, o, 0, prev, 1); prev = o; n += 1
        t1 = time.time()
        rep = F.check_continuity(d3)
        t2 = time.time()
        assert rep['ok'] and len(rep['connected']) == 59 and len(rep['open_ports']) == 2, rep
        return {'fittings': n, 'build_snap_secs': round(t1 - t0, 2), 'continuity_secs': round(t2 - t1, 2), 'scope': 'one CI run, 60 generic fittings in a chain, not a requirement or memory claim'}
    run('chain_of_60_fittings', s_scale)
except Exception:
    res['error'] = traceback.format_exc()
res['done'] = True
save()
