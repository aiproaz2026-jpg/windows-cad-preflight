import os,json,traceback
import FreeCAD as App
OUT='@@OUT@@'
os.makedirs(OUT,exist_ok=True)
R={'stage':'start'}
def w():
    with open(OUT+'/libs-result.json','w',encoding='utf-8') as f: f.write(json.dumps(R,ensure_ascii=True,indent=1,default=str))
def run():
    try:
        try:
            from DeltaEngineering import parts_library as PL
        except ImportError:
            import sys,glob
            for p in glob.glob(os.path.expandvars(r'%LOCALAPPDATA%/Programs/DeltaEngineering/Mod/*'))+glob.glob(r'C:/DeltaLic/Mod/*'):
                if os.path.isdir(p) and p not in sys.path: sys.path.append(p)
            from DeltaEngineering import parts_library as PL
        from DeltaEngineering import fittings_library as FL
        d=App.newDocument('Libs')
        res={'parts':{},'fittings':{},'edit_test':{},'stamps':{}}
        # 1. every size of every parametric family
        families={'hex_bolt':(PL.HexBolt,list(PL.BOLTS_ISO4014)),'hex_nut':(PL.HexNut,list(PL.NUTS_ISO4032)),
                  'washer':(PL.Washer,list(PL.WASHERS_ISO7089)),'bearing':(PL.Bearing62,list(PL.BEARINGS_62)),
                  'ipe':(PL.IpeSection,list(PL.IPE))}
        for fam,(cls,sizes) in families.items():
            ok=0;bad=[]
            for sz in sizes:
                o=d.addObject('Part::FeaturePython',fam)
                try:
                    cls(o,sz);o.recompute()
                    sh=o.Shape
                    if sh.isNull() or not sh.isValid() or sh.Volume<=0:bad.append((sz,'invalid shape'))
                    elif not getattr(o,'DimensionSource',''):bad.append((sz,'no provenance'))
                    else:ok+=1
                except Exception as e:bad.append((sz,str(e)[:120]))
            res['parts'][fam]={'ok':ok,'bad':bad}
        # gears: parametric formula family
        ok=0;bad=[]
        for m,z in ((1.5,12),(2,20),(3,40),(4,60),(2.5,96)):
            o=d.addObject('Part::FeaturePython','gear')
            try:
                PL.SpurGear(o,m,z,10.0);o.recompute()
                sh=o.Shape
                if sh.isNull() or not sh.isValid() or sh.Volume<=0:bad.append(((m,z),'invalid shape'))
                else:ok+=1
            except Exception as e:bad.append(((m,z),str(e)[:120]))
        res['parts']['gear']={'ok':ok,'bad':bad}
        # 2. editability: user-set dimensions must re-execute without errors
        o=d.addObject('Part::FeaturePython','hex_nut')
        PL.HexNut(o,'M12');o.recompute()
        o.Thickness=20.0;o.NominalDiameter=15.0;o.recompute()
        res['edit_test']['nut_edited_valid']=bool((not o.Shape.isNull()) and o.Shape.isValid() and abs(o.Shape.BoundBox.ZLength-20.0)<1e-6)
        g=d.addObject('Part::FeaturePython','gear2')
        PL.SpurGear(g,2.0,20,10.0);g.recompute()
        g.Teeth=33;g.recompute()
        res['edit_test']['gear_teeth_edited_valid']=bool((not g.Shape.isNull()) and g.Shape.isValid())
        # 3. fittings library data integrity (tables + stamps)
        fit={}
        fit['elbows_lr90']=len(FL.ELBOW_90_LR_A);fit['elbows_45']=len(FL.ELBOW_45_LR_B);fit['elbows_sr90']=len(FL.ELBOW_90_SR_A)
        fit['tees']=len(FL.TEE_EQ_CM);fit['reducers']=len(FL.REDUCER_H);fit['flanges']=len(FL.FLANGE_CL150)
        st=FL.status('elbow_90_lr','2')
        fit['status_has_sources']=bool(st['sources'] and st['revision'] and st['dimensions_mm']==76)
        fl=FL.FLANGE_CL150['2']
        fit['flange_nps2_check']=bool(abs(fl['od']-152.4)<1e-9 and fl['holes']==4 and abs(fl['thickness_min']-17.5)<1e-9)
        res['fittings']=fit
        # 4. provenance stamp sample
        res['stamps']['bolt_sample']={'family':o.PartFamily if hasattr(o,'PartFamily') else None}
        R['libs']=res
    except Exception:
        R['error']=traceback.format_exc()[-1500:]
    R['done']=True; w()
run()
