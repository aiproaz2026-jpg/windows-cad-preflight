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
            import re
            lat=re.compile(r'[A-Za-z]{2,}')
            found={}
            def add(txt,kind,cls,wb):
                if txt and lat.search(txt):
                    found.setdefault(txt,{'kinds':set(),'wbs':set()}); found[txt]['kinds'].add(kind+':'+cls); found[txt]['wbs'].add(wb)
            def scan(wb):
                mw=Gui.getMainWindow()
                add(mw.windowTitle(),'title','main',wb)
                for a in mw.findChildren(QtWidgets.QAction):
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
            Gui.activateWorkbench('DeltaWorkbench'); pump(40)
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
