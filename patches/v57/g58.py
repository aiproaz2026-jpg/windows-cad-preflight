import os,json,traceback,math
import FreeCAD as App, FreeCADGui as Gui
from PySide import QtCore, QtWidgets
OUT='@@OUT@@'
os.makedirs(OUT,exist_ok=True)
R={'stage':'start'}
def w():
    with open(OUT+'/gui-result.json','w',encoding='utf-8') as f: f.write(json.dumps(R,ensure_ascii=True,indent=1,default=str))
def pump(n=30):
    for _ in range(n):
        QtWidgets.QApplication.processEvents(); QtCore.QThread.msleep(20)
def step(name,fn):
    R['stage']=name; w()
    try: R[name]=fn()
    except Exception: R[name]={'error':traceback.format_exc()[-1200:]}
    w()
V=App.Vector
def rot(pts,deg):
    c,s=math.cos(math.radians(deg)),math.sin(math.radians(deg)); return [V(p.x*c-p.y*s,p.x*s+p.y*c,0) for p in pts]
P=lambda *t:[V(x,y,0) for x,y in t]
PATHS={'L':P((0,0),(800,0),(800,500)),'L_rev':P((800,500),(800,0),(0,0)),'L_rot45':rot(P((0,0),(800,0),(800,500)),45),
 'L_rot137':rot(P((0,0),(800,0),(800,500)),137),'U':P((0,0),(0,400),(300,400),(300,0)),'Z':P((0,0),(600,0),(0,300),(600,300)),
 'stair':P((0,0),(400,0),(400,200),(200,200),(200,400),(0,400))}
def hit(p,q,r,t):
    # strict: interior crossings or collinear interior overlap; endpoint grazes are not crossings
    def o(a,b,c):return (b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x)
    d1,d2,d3,d4=o(p,q,r),o(p,q,t),o(r,t,p),o(r,t,q)
    if ((d1>1e-9 and d2<-1e-9) or (d1<-1e-9 and d2>1e-9)) and ((d3>1e-9 and d4<-1e-9) or (d3<-1e-9 and d4>1e-9)):return True
    def between(a,b,c):return min(a.x,b.x)-1e-9<=c.x<=max(a.x,b.x)+1e-9 and min(a.y,b.y)-1e-9<=c.y<=max(a.y,b.y)+1e-9
    if abs(d1)<=1e-9 and abs(d2)<=1e-9:
        for c in (r,t):
            if between(p,q,c) and (c-p).Length>1e-7 and (c-q).Length>1e-7:return True
        for c in (p,q):
            if between(r,t,c) and (c-r).Length>1e-7 and (c-t).Length>1e-7:return True
    return False
def count(doc,obj,dims):
    pts=[v.Point for v in obj.Shape.Vertexes]
    pathsegs=[(pts[i],pts[i+1]) for i in range(len(pts)-1)]
    allx=[]
    for k,dm in enumerate(dims):
        a,b=dm.Start,dm.End;v=b-a;v.normalize();sd=V(0,0,1).cross(v);off=(dm.Dimline-(a+b)*0.5).dot(sd)
        allx.append((k,[(a+sd*off,b+sd*off),(a,a+sd*off),(b,b+sd*off)]))
    path_bad=0; dim_bad=0
    for k,mine in allx:
        for idx,seg in enumerate(mine):
            for o in pathsegs:
                if idx>0 and ((seg[0]-o[0]).Length<1e-7 or (seg[0]-o[1]).Length<1e-7):continue
                if hit(seg[0],seg[1],o[0],o[1]):path_bad+=1
        for k2,m2 in allx:
            if k2==k:continue
            for seg in mine:
                for s2 in m2:
                    if (seg[0]-s2[0]).Length<1e-7:continue
                    if hit(seg[0],seg[1],s2[0],s2[1]):dim_bad+=1
    return {'path':path_bad,'dim':dim_bad//2}
def grab(name):
    pump(40); Gui.getMainWindow().grab().save(OUT+'/'+name+'.png'); R.setdefault('images',[]).append(name+'.png'); w()
def run():
    try:
        Gui.activateWorkbench('DeltaWorkbench'); pump(60)
        try:
            from DeltaEngineering import library_commands as LC
            R['lib_cmds']=[k for k in LC.command_keys() if k in Gui.listCommands()]
            d0=App.newDocument('LibCmd'); made={}
            for fam,_t,_p in LC.FAMILIES:
                sz=LC.sizes(fam); o=LC.make_part(d0,fam,sz[0] if sz else None)
                made[fam]=bool(o.Shape.isValid() and o.Shape.Volume>0)
            R['lib_cmd_make']=made
            R['toolbars']=str(getattr(Gui.getWorkbench('DeltaWorkbench'),'listToolbars',lambda:'n/a')())
        except Exception as e:
            import traceback; R['lib_cmd_error']=traceback.format_exc()[-600:]
        try:
            from DeltaEngineering import fittings3d as F3, fit_commands as FC
            pump(60); R['window_title']=Gui.getMainWindow().windowTitle(); R['workbench_menutext']=Gui.getWorkbench('DeltaWorkbench').MenuText
            R['fit_cmds']=[k for k in FC.command_keys() if k in Gui.listCommands()]
            d3=App.newDocument('Fit3D'); App.setActiveDocument(d3.Name)
            res={}; objs=[]; x=0.0
            for kind in F3.KINDS:
                for pr in F3.presets(kind):
                    o=F3.create(d3,kind,pr); sh=o.Shape
                    ev=F3.expected_volume(o); bb=sh.BoundBox
                    ent={'valid':bool(sh.isValid()),'solids':len(sh.Solids),'vol':round(sh.Volume,3),'closed':bool(sh.isClosed()),
                         'exp':None if ev is None else round(ev,3),'rel_err':None if ev is None else abs(sh.Volume-ev)/ev,
                         'bbox':[round(bb.XLength,2),round(bb.YLength,2),round(bb.ZLength,2)],'prov':bool(o.DimensionSource)}
                    res[kind+'|'+pr]=ent
                    if pr==F3.presets(kind)[-1]:
                        o.Placement.Base=App.Vector(x,0,0); x+=300; objs.append(o)
                    else:
                        d3.removeObject(o.Name)
            d3.recompute()
            R['fit3d']=res
            bad=[k for k,v in res.items() if not v['valid'] or v['solids']!=1 or v['vol']<=0 or (v['rel_err'] is not None and v['rel_err']>1e-6)]
            R['fit3d_bad']=bad; R['fit3d_count']=len(res)
            tee=[v for k,v in res.items() if k.startswith('tee_eq|')]
            R['fit3d_tee_bbox_ok']=all(abs(v['bbox'][0]-2*F3.FL.TEE_EQ_CM[k.split('|')[1]][0])<1e-6 for k,v in res.items() if k.startswith('tee_eq|'))
            # edit test: change a diameter and a preset
            e=objs[3]; od0=e.Shape.Volume; e.OuterDiameter=100; d3.recompute(); R['fit3d_edit_od_changes_volume']=abs(e.Shape.Volume-od0)>1.0
            e.SizePreset='2'; d3.recompute(); R['fit3d_preset_reload']=[e.OuterDiameter.Value,e.RunCenterToEnd.Value]
            fp=OUT+'/fit3d.FCStd'; d3.saveAs(fp); App.closeDocument(d3.Name)
            d4=App.openDocument(fp); d4.recompute(); R['fit3d_reopen']=[(o.Label,bool(o.Shape.isValid()),round(o.Shape.Volume,1)) for o in d4.Objects]
            App.setActiveDocument(d4.Name); pump(40)
            vv=Gui.ActiveDocument.ActiveView; vv.viewIsometric(); vv.fitAll(); pump(80); grab('fit3d_iso')
            App.closeDocument(d4.Name)
        except Exception as e:
            import traceback; R['fit3d_error']=traceback.format_exc()[-900:]
        try:
            from DeltaEngineering import equipment3d as E3, eq_commands as EC, fittings3d as F3b
            R['eq_cmds']=[k for k in EC.command_keys() if k in Gui.listCommands()]
            d5=App.newDocument('Eq3D'); App.setActiveDocument(d5.Name)
            res5={}
            for kind in E3.KINDS:
                for pr in E3.presets(kind):
                    o=E3.create(d5,kind,pr); sh=o.Shape; bb=sh.BoundBox
                    ev=E3.expected_volume(o)
                    ent={'valid':bool(sh.isValid()),'solids':len(sh.Solids),'vol':round(sh.Volume,2),'exp':None if ev is None else round(ev,2),
                         'rel_err':None if ev is None else abs(sh.Volume-ev)/ev,'bbox':[round(bb.XLength,2),round(bb.YLength,2),round(bb.ZLength,2)],
                         'generic_note':bool(getattr(o,'GenericNote','')) if kind in ('gate_valve','ball_valve','check_valve','pump') else None}
                    if kind in E3.VALVE_FF: ent['ff_ok']=abs(bb.XLength-E3.VALVE_FF[kind][pr])<1e-6
                    res5[kind+'|'+pr]=ent
                    d5.removeObject(o.Name)
            R['eq3d']=res5; R['eq3d_count']=len(res5)
            R['eq3d_bad']=[k for k,v in res5.items() if not v['valid'] or v['solids']!=1 or v['vol']<=0 or (v['rel_err'] is not None and v['rel_err']>1e-6) or v.get('ff_ok') is False]
            # schedules
            e2=F3b.create(d5,'elbow90lr','2'); v40=e2.Shape.Volume; e2.Schedule='SCH 80'; d5.recompute()
            R['sched_wall_80']=e2.Wall.Value; R['sched_vol_changes']=e2.Shape.Volume<v40*0.9 or e2.Shape.Volume>v40*1.1
            e2.SizePreset='4'; d5.recompute(); R['sched_after_size_change']=[e2.Schedule,e2.Wall.Value,e2.OuterDiameter.Value]
            e3=F3b.create(d5,'tee_eq','3 1/2'); e3.Schedule='SCH 160'; d5.recompute(); R['sched_3half_160_ignored']=e3.Wall.Value
            # route insertion
            Vv=App.Vector
            PR={'L90':[Vv(0,0,0),Vv(800,0,0),Vv(800,500,0)],
                'U':[Vv(0,0,0),Vv(0,600,0),Vv(500,600,0),Vv(500,0,0)],
                'stair3d':[Vv(0,0,0),Vv(600,0,0),Vv(600,0,500),Vv(600,400,500),Vv(1200,400,500)],
                'bend45':[Vv(0,0,0),Vv(700,0,0),Vv(700+400*0.70710678118,400*0.70710678118,0)],
                'straight':[Vv(0,0,0),Vv(0,0,0)+Vv(1000,0,0)]}
            rr={}
            for nm,pts in PR.items():
                for nps,sch in (('2','SCH 40'),('4','SCH 80')):
                    dd=App.newDocument('R'); App.setActiveDocument(dd.Name)
                    try:
                        o=E3.route_fittings(dd,pts,nps,sch)
                        okv=all(x.Shape.isValid() and x.Shape.Volume>0 for x in o['pipes']+o['elbows'])
                        rr[nm+'|'+nps+'|'+sch]={'pipes':len(o['pipes']),'elbows':len(o['elbows']),'max_joint_gap_mm':o['max_joint_gap_mm'],'all_valid':bool(okv)}
                    except Exception as ex:
                        rr[nm+'|'+nps+'|'+sch]={'error':str(ex)[:200]}
                    App.closeDocument(dd.Name)
            try:
                dd=App.newDocument('R'); E3.route_fittings(dd,[Vv(0,0,0),Vv(500,0,0),Vv(500+250,433,0)],'2'); rr['bend60']={'error':'NOT REFUSED'}
            except ValueError as ex:
                rr['bend60']={'refused':str(ex)[:120]}
            try:
                dd=App.newDocument('R'); E3.route_fittings(dd,[Vv(0,0,0),Vv(100,0,0),Vv(100,100,0)],'4'); rr['tooshort']={'error':'NOT REFUSED'}
            except ValueError as ex:
                rr['tooshort']={'refused':str(ex)[:120]}
            R['route']=rr
            R['route_bad']=[k for k,v in rr.items() if (('|' in k) and (('error' in v) or v['max_joint_gap_mm']>1e-6 or not v['all_valid'])) or (k in ('bend60','tooshort') and 'refused' not in v)]
            # showcase
            ds=App.newDocument('EqShow'); App.setActiveDocument(ds.Name)
            E3.route_fittings(ds,PR['U'],'2')
            for i,(kd,pr) in enumerate((('gate_valve','2'),('ball_valve','2'),('check_valve','2'),('weldneck150','2'),('pump','2 1/2 x 2'))):
                o=E3.create(ds,kd,pr); o.Placement.Base=Vv(900+i*450 if kd!='pump' else 2600,-300 if kd!='pump' else 0,0)
            ds.recompute(); pump(40)
            nvis=0
            for o in ds.Objects:
                try:
                    if o.isDerivedFrom('Part::Feature') or hasattr(o,'Shape'):
                        o.ViewObject.Visibility=True; nvis+=1
                except Exception: pass
            pump(40); R['eq3d_show_visible']=nvis
            fq=OUT+'/eqshow.FCStd'; ds.saveAs(fq); App.closeDocument(ds.Name)
            ds=App.openDocument(fq); ds.recompute(); App.setActiveDocument(ds.Name); pump(60)
            R['eq3d_reopen_valid']=[bool(o.Shape.isValid()) for o in ds.Objects if hasattr(o,'Shape')]
            vw=Gui.ActiveDocument.ActiveView; vw.viewIsometric(); vw.fitAll(); pump(120); grab('eq3d_iso')
            allo=[o for o in ds.Objects if hasattr(o,'Shape')]
            for nm,key in (('eq3d_gate','gate'),('eq3d_ball','ball'),('eq3d_pump','pump'),('eq3d_flange','weld'),('eq3d_route','')):
                try:
                    for o in allo:
                        lab=o.Label.lower(); isr=('pipe' in o.Name.lower() or 'elbow' in o.Name.lower() or 'route' in o.Name.lower())
                        o.ViewObject.Visibility = (key in o.Name.lower() or key in lab) if key else isr
                    pump(30); vw.viewIsometric(); vw.fitAll(); pump(80); grab(nm)
                except Exception as e2:
                    R['eq3d_closeup_err_'+nm]=str(e2)[:120]
            R['eq3d_object_names']=[o.Name for o in allo]
            for o in allo:
                try: o.ViewObject.Visibility=True
                except Exception: pass
            App.closeDocument(ds.Name); App.closeDocument(d5.Name)
        except Exception as e:
            import traceback; R['eq3d_error']=traceback.format_exc()[-1200:]
        try:
            from DeltaEngineering import threads3d as T3
            import math as _m
            tr={}; dt=App.newDocument('Thr')
            for kind,pre in (('metric','M6'),('metric','M10'),('metric','M20'),('npt','1/2'),('npt','1'),('npt','2')):
                o=T3.create(dt,kind,pre); sh=o.Shape
                ent={'valid':bool(sh.isValid()),'solids':len(sh.Solids),'vol':round(sh.Volume,2),'mode':o.ThreadModeUsed,'bbox':[round(sh.BoundBox.XLength,3),round(sh.BoundBox.YLength,3),round(sh.BoundBox.ZLength,3)],'pitch':round(o.Pitch.Value,4)}
                if kind=='metric':
                    mm=T3.metric_dims(pre); ex=_m.pi*(mm['d2']/2.0)**2*o.Length.Value
                    ent['ratio_to_pitch_cylinder']=round(sh.Volume/ex,4); ent['bbox_ok']=abs(ent['bbox'][0]-mm['d'])<0.05 and abs(ent['bbox'][2]-o.Length.Value)<1e-6
                else:
                    od,tpi,e0,l2=T3.NPT[pre]; ent['bbox_ok']=abs(ent['bbox'][2]-(o.BodyLength.Value+l2*25.4))<1e-3
                tr[kind+'|'+pre]=ent
            e=dt.getObject('Thr_metric'); e.SizePreset='M8'; dt.recompute(); tr['edit_M8_pitch']=round(e.Pitch.Value,4)
            e.ThreadMode='Cosmetic'; dt.recompute(); tr['edit_cosmetic_mode_used']=e.ThreadModeUsed
            e.ThreadMode='Modeled'; e.SizePreset='M10'; dt.recompute()
            R['threads']=tr
            R['thread_bad']=[k for k,v in tr.items() if isinstance(v,dict) and 'valid' in v and (not v['valid'] or v['solids']!=1 or v['mode']!='Modeled' or not v.get('bbox_ok') or (k.startswith('metric') and not (0.85<v['ratio_to_pitch_cylinder']<1.15)))]
            fq=OUT+'/threads.FCStd'; dt.saveAs(fq); App.closeDocument(dt.Name)
            dt=App.openDocument(fq); dt.recompute(); App.setActiveDocument(dt.Name); pump(60)
            alls=[o for o in dt.Objects if hasattr(o,'Shape')]
            vw=Gui.ActiveDocument.ActiveView
            for nm,key in (('thread_metric','metric'),('thread_npt','npt')):
                for o in alls:
                    o.ViewObject.Visibility=(key in o.Name.lower())
                pump(30); vw.viewIsometric(); vw.fitAll(); pump(80); grab(nm)
            App.closeDocument(dt.Name)
        except Exception as e:
            import traceback; R['thread_error']=traceback.format_exc()[-1200:]
        try:
            import re
            from PySide import QtGui
            lat=re.compile(r'[A-Za-z]{2,}')
            found={}
            def add(txt,kind,cls,wb):
                if txt and lat.search(txt):
                    found.setdefault(txt,{'kinds':set(),'wbs':set()}); found[txt]['kinds'].add(kind+':'+cls); found[txt]['wbs'].add(wb)
            def scan(wb):
                mw=Gui.getMainWindow()
                add(mw.windowTitle(),'title','main',wb)
                for a in mw.findChildren(QtGui.QAction):
                    add(a.text().replace('&',''),'action',a.objectName()[:30],wb); add(a.toolTip(),'tooltip',a.objectName()[:30],wb); add(a.statusTip(),'status',a.objectName()[:30],wb)
                for m in mw.findChildren(QtWidgets.QMenu): add(m.title().replace('&',''),'menu','',wb)
                for t in mw.findChildren(QtWidgets.QToolBar): add(t.windowTitle(),'toolbar','',wb)
                for d in mw.findChildren(QtWidgets.QDockWidget): add(d.windowTitle(),'dock','',wb)
                for c in (QtWidgets.QLabel,QtWidgets.QPushButton,QtWidgets.QCheckBox,QtWidgets.QGroupBox,QtWidgets.QRadioButton):
                    for w2 in mw.findChildren(c):
                        t2=w2.title() if c is QtWidgets.QGroupBox else w2.text()
                        add(t2,'widget',c.__name__,wb)
                for tb in mw.findChildren(QtWidgets.QTabBar):
                    for k in range(tb.count()): add(tb.tabText(k),'tab','',wb)
            wbl=[]
            for wb in ('DeltaWorkbench','PartWorkbench','PartDesignWorkbench','SketcherWorkbench','DraftWorkbench','TechDrawWorkbench','AssemblyWorkbench','StartWorkbench'):
                try:
                    Gui.activateWorkbench(wb); pump(40); scan(wb); wbl.append(wb)
                except Exception as e2:
                    R.setdefault('ui_wb_err',{})[wb]=str(e2)[:80]
            R['ui_wbs']=wbl
            out=[{'text':k,'kinds':sorted(v['kinds'])[:4],'wbs':sorted(v['wbs'])} for k,v in found.items()]
            open(OUT+'/ui-strings.json','w',encoding='utf-8').write(json.dumps(out,ensure_ascii=False))
            R['ui_en_count']=len(out)
            Gui.activateWorkbench('DeltaWorkbench'); pump(60)
            try:
                from DeltaEngineering import ar_layer as AR
                R['sweep_changed_now']=AR.sweep(); pump(20)
                R['sweep_changed_again']=AR.sweep()
                R['ar_translator_installed']=bool(AR._keep)
                grab('delta_ar_ui')
                from DeltaEngineering.core import create_demo
                dd=create_demo('LabelCheck'); R['demo_labels']=[o.Label for o in dd.Objects]
                R['demo_labels_latin']=[l for l in R['demo_labels'] if re.search('[A-Za-z]{3,}',l)]
            except Exception as e3:
                import traceback; R['ar_layer_error']=traceback.format_exc()[-600:]
        except Exception as e:
            import traceback; R['ui_scan_error']=traceback.format_exc()[-600:]
        from DeltaEngineering.drafting import make_path,linked_dimension,export_dimensioned
        import inspect
        R['default_placement']=inspect.signature(linked_dimension).parameters['placement'].default
        def layouts():
            res={}
            for name,pts in PATHS.items():
                d=App.newDocument('P'); App.setActiveDocument(d.Name)
                path=make_path(d,pts)
                dims=[linked_dimension(d,path,i,i+1,100) for i in range(len(pts)-1)]
                res[name]={'crossings_path':count(d,path,dims)['path'],'crossings_dim':count(d,path,dims)['dim'],'values':[round(x.Distance.Value,4) for x in dims],
                           'placements':[str(getattr(x,'PlacementMode','default')) for x in dims],'offsets':[round((x.Dimline-(x.Start+x.End)*0.5).Length,1) for x in dims]}
                if name in ('Z','stair'):
                    try:
                        import DeltaEngineering.drafting as DR
                        offs=lambda: [round((x.Dimline-(x.Start+x.End)*0.5).Length,1) for x in dims]
                        dg={'lg':[repr(x.LinkedGeometry)[:140] for x in dims],'collected':len(DR._collect_dims(d,path)),'has_links_to':hasattr(DR,'_links_to'),'before':offs()}
                        try:
                            DR._repair_dims(d,path,[v.Point for v in path.Shape.Vertexes]); d.recompute()
                        except Exception:
                            dg['err']=traceback.format_exc()[-600:]
                        dg['after']=offs(); dg['after_count']=count(d,path,dims)
                        pts_=[v.Point for v in path.Shape.Vertexes]; ps_=[(pts_[i],pts_[i+1]) for i in range(len(pts_)-1)]
                        sg_=[]
                        for x in dims:
                            a_,b_=x.Start,x.End; v_=b_-a_; v_.normalize(); sd_=V(0,0,1).cross(v_); of_=(x.Dimline-(a_+b_)*0.5).dot(sd_)
                            sg_.append(DR._dimension_segments(a_,b_,sd_,of_))
                        dg['strict_path_hits_incl_overlap']=sum(1 for i_,m_ in enumerate(sg_) for s_ in m_ for k_,pp in enumerate(ps_) if k_!=i_ and DR._seg_hit_strict(s_[0],s_[1],pp[0],pp[1]))
                        dg['strict_dim_hits']=sum(1 for i_,m_ in enumerate(sg_) for j_,n_ in enumerate(sg_) if j_>i_ for s_ in m_ for t_ in n_ if DR._seg_hit_strict(s_[0],s_[1],t_[0],t_[1]))
                        dg['sides_offsets']=offs()
                        res[name]['diag']=dg
                    except Exception:
                        res[name]['diag']={'err':traceback.format_exc()[-600:]}
                if name in ('Z','L_rot45','L'):
                    f=OUT+'/dim_%s_mm.pdf'%name
                    try:
                        export_dimensioned(d,path,f,unit='mm'); res[name]['pdf_mm']=os.path.getsize(f)
                    except Exception as e: res[name]['pdf_err']=str(e)[:200]
                if name=='Z':
                    d.recompute(); v=Gui.ActiveDocument.ActiveView; v.viewTop(); v.fitAll(); pump(60); grab('z_layout_v9')
                App.closeDocument(d.Name)
            return res
        step('layouts_default',layouts)
    except Exception:
        R['error']=traceback.format_exc()[-1500:]
    R['done']=True; w()
QtCore.QTimer.singleShot(9000,run)
