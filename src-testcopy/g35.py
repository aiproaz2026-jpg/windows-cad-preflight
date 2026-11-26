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
    def o(a,b,c):return (b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x)
    d1,d2,d3,d4=o(p,q,r),o(p,q,t),o(r,t,p),o(r,t,q)
    return ((d1>1e-9 and d2<-1e-9) or (d1<-1e-9 and d2>1e-9)) and ((d3>1e-9 and d4<-1e-9) or (d3<-1e-9 and d4>1e-9))
def count(doc,obj,dims):
    pts=[v.Point for v in obj.Shape.Vertexes]
    pathsegs=[(pts[i],pts[i+1]) for i in range(len(pts)-1)]
    allx=[]
    for k,dm in enumerate(dims):
        a,b=dm.Start,dm.End;v=b-a;v.normalize();sd=V(0,0,1).cross(v);off=(dm.Dimline-(a+b)*0.5).dot(sd)
        allx.append((k,[(a+sd*off,b+sd*off),(a,a+sd*off),(b,b+sd*off)]))
    bad=0
    for k,mine in allx:
        for idx,seg in enumerate(mine):
            for o in pathsegs:
                if idx>0 and ((seg[0]-o[0]).Length<1e-7 or (seg[0]-o[1]).Length<1e-7):continue
                if hit(seg[0],seg[1],o[0],o[1]):bad+=1
        for k2,m2 in allx:
            if k2==k:continue
            for seg in mine:
                for s2 in m2:
                    if (seg[0]-s2[0]).Length<1e-7:continue
                    if hit(seg[0],seg[1],s2[0],s2[1]):bad+=1
    return bad
def titles():
    return [a.text().encode('ascii','backslashreplace').decode() for a in Gui.getMainWindow().menuBar().actions()]
def grab(name):
    pump(40); Gui.getMainWindow().grab().save(OUT+'/'+name+'.png'); R.setdefault('images',[]).append(name+'.png'); w()
def run():
    try:
        Gui.activateWorkbench('DeltaWorkbench'); pump(60)
        R['menus']={'t0':titles()}; w()
        from DeltaEngineering.drafting import make_path,linked_dimension,export_dimensioned
        def guidims():
            d=App.newDocument('DimDoc'); App.setActiveDocument(d.Name); pump(30)
            path=make_path(d,PATHS['L']); d1=linked_dimension(d,path,0,1,100); d2=linked_dimension(d,path,1,2,100)
            for x in (d1,d2):
                x.ViewObject.FontSize=30; x.ViewObject.TextSpacing=12
            d.recompute(); v=Gui.ActiveDocument.ActiveView; v.viewTop(); v.fitAll(); pump(60); grab('dims_gui_spacing12')
            d1.ViewObject.UnitOverride='in'; d2.ViewObject.UnitOverride='in'; d.recompute(); pump(60); grab('dims_gui_spacing12_in')
            return {'textspacing':str(x.ViewObject.TextSpacing)}
        step('gui_dims',guidims)
        def asm_menu():
            from DeltaEngineering.mechanical import make_assembly_example
            a=App.newDocument('AsmDoc'); App.setActiveDocument(a.Name); make_assembly_example(a); pump(60)
            v=Gui.ActiveDocument.ActiveView; v.viewIsometric(); v.fitAll(); pump(80)
            R['menus']['t3_after_assembly']=titles(); w(); grab('assembly_gui_repair')
            App.setActiveDocument('DimDoc'); pump(60); R['menus']['t4_back']=titles(); w()
            import DeltaEngineering.gui as dg
            R['has_repair']=hasattr(dg,'install_menu_repair'); return True
        step('assembly_menu',asm_menu)
        def layouts():
            res={}
            for name,pts in PATHS.items():
                res[name]={}
                for mode in ('legacy','centroid'):
                    d=App.newDocument('P'); App.setActiveDocument(d.Name)
                    path=make_path(d,pts)
                    dims=[linked_dimension(d,path,i,i+1,100,placement=mode) for i in range(len(pts)-1)]
                    res[name][mode]={'crossings':count(d,path,dims),'values':[round(x.Distance.Value,4) for x in dims]}
                    if mode=='centroid' and name in ('L','L_rev','L_rot45','Z','stair'):
                        for u in ('mm','in') if name=='L' else ('mm',):
                            f=OUT+'/dim_%s_%s.pdf'%(name,u)
                            try:
                                export_dimensioned(d,path,f,unit=u); res[name]['pdf_'+u]=os.path.getsize(f)
                            except Exception as e: res[name]['pdf_err_'+u]=str(e)[:200]
                    App.closeDocument(d.Name)
            return res
        step('layouts',layouts)
        def stored():
            # a dimension made with legacy placement must keep its stored Dimline when the module is the new one
            d=App.newDocument('S'); App.setActiveDocument(d.Name)
            path=make_path(d,PATHS['L']); dm=linked_dimension(d,path,1,2,100,placement='legacy')
            before=tuple(round(c,6) for c in dm.Dimline)
            p=OUT+'/stored.FCStd'; d.saveAs(p); App.closeDocument(d.Name)
            d=App.openDocument(p); d.recompute(); dm=[o for o in d.Objects if hasattr(o,'LinkedGeometry')][0]
            return {'dimline_before':before,'dimline_after_reopen':tuple(round(c,6) for c in dm.Dimline),'same':before==tuple(round(c,6) for c in dm.Dimline)}
        step('stored_dimension_preserved',stored)
        def solver():
            import JointObject
            from DeltaEngineering.mechanical import make_assembly_example
            a=App.newDocument('Asm'); App.setActiveDocument(a.Name); asm=make_assembly_example(a); pump(30)
            res={'solve_grounded_only':asm.solve()}
            joints=a.getObject('Joints'); lb=a.BaseInstance; ls=a.ShaftInstance
            before=[round(c,4) for c in ls.Placement.Base]
            j=joints.newObject('App::FeaturePython','FixedJoint'); JointObject.Joint(j,0)
            res['joint_types']=list(JointObject.JointTypes)[:8]
            j.Proxy.setJointConnectors(j,[[lb,['Face6','Vertex7']],[ls,['Face3','Vertex2']]])
            a.recompute(); res['solve_after_fixed']=asm.solve()
            res['shaft_base_before']=before; res['shaft_base_after']=[round(c,4) for c in ls.Placement.Base]
            res['shaft_rotation_axis_angle']=[tuple(round(c,4) for c in ls.Placement.Rotation.Axis),round(math.degrees(ls.Placement.Rotation.Angle),4)]
            # coincidence check: world position of the two referenced vertices
            def world(link,src,vname):
                s=src.Shape.copy(); s.Placement=link.Placement.multiply(s.Placement); return s.getElement(vname).Point
            pb=world(lb,a.AssemblyBase,'Vertex7'); ps=world(ls,a.AssemblyShaft,'Vertex2')
            res['vertex_gap_mm']=(pb-ps).Length; res['base_vertex7']=[round(c,4) for c in pb]; res['shaft_vertex2']=[round(c,4) for c in ps]
            # moving the base must carry the shaft
            lb.Placement=App.Placement(V(1000,0,0),lb.Placement.Rotation); a.recompute(); res['solve_after_move']=asm.solve()
            res['shaft_base_after_move_of_base_only']=[round(c,4) for c in ls.Placement.Base]
            pb=world(lb,a.AssemblyBase,'Vertex7'); ps=world(ls,a.AssemblyShaft,'Vertex2'); res['vertex_gap_after_move_mm']=(pb-ps).Length
            return res
        step('solver',solver)
    except Exception:
        R['error']=traceback.format_exc()[-1500:]
    R['done']=True; w()
QtCore.QTimer.singleShot(9000,run)
