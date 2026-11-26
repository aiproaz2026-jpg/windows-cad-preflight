# SPDX-License-Identifier: GPL-3.0-or-later
"""Native Draft geometry and linked vertex dimensions. Model units: mm."""
import math
import FreeCAD as App


def checked_points(points):
    if len(points)<2:raise ValueError('At least two points required')
    for p in points:
        if not all(math.isfinite(v) for v in (p.x,p.y,p.z)):raise ValueError('Coordinates must be finite')
    if any((b-a).Length<1e-7 for a,b in zip(points,points[1:])):raise ValueError('Consecutive points must differ')
    return points


def make_path(doc,points,closed=False):
    import Draft
    checked_points(points)
    if App.ActiveDocument!=doc:raise ValueError('Activate the target document')
    if closed and len(points)<3:raise ValueError('Closed path needs three points')
    doc.openTransaction('Draw editable polyline')
    try:
        obj=Draft.make_wire(points,closed=closed,face=False)
        obj.Label='مسار مرسوم'
        from .documents import add_to
        add_to(doc,'DrawingSystem',obj)
        doc.recompute();doc.commitTransaction();return obj
    except Exception:doc.abortTransaction();doc.recompute();raise


def update_path(doc,obj,points):
    checked_points(points)
    if obj.Document!=doc:raise ValueError('Path belongs to a different document')
    if not hasattr(obj,'Points'):raise ValueError('Select an editable Draft path')
    if getattr(obj,'Closed',False) and len(points)<3:raise ValueError('Closed path needs three points')
    # Prevent dangling index dimensions. Index identity is not geometric intent.
    linked=[o for o in doc.Objects if hasattr(o,'LinkedGeometry') and any(entry[0]==obj for entry in o.LinkedGeometry)]
    if len(points)!=len(obj.Points) and linked:raise ValueError('Remove linked dimensions before changing vertex count')
    doc.openTransaction('Edit polyline coordinates')
    try:
        obj.Points=points;doc.recompute()
        for dependent in doc.Objects:
            if (getattr(dependent,'SourcePath',None)==obj or getattr(dependent,'Profile',None)==obj) and dependent.Shape.isNull():
                raise ValueError('Path edit rejected: '+dependent.Validation)
        from .validation import valid_document
        valid_document(doc)
        doc.commitTransaction()
    except Exception:doc.abortTransaction();doc.recompute();raise


def _seg_hit(p,q,r,t):
    """True when planar segments pq and rt properly cross or touch (XY only)."""
    def o(a,b,c):return (b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x)
    def on(a,b,c):return min(a.x,b.x)-1e-9<=c.x<=max(a.x,b.x)+1e-9 and min(a.y,b.y)-1e-9<=c.y<=max(a.y,b.y)+1e-9
    d1,d2,d3,d4=o(p,q,r),o(p,q,t),o(r,t,p),o(r,t,q)
    if ((d1>1e-9 and d2<-1e-9) or (d1<-1e-9 and d2>1e-9)) and ((d3>1e-9 and d4<-1e-9) or (d3<-1e-9 and d4>1e-9)):return True
    for a,b,c,d in ((p,q,r,d1),(p,q,t,d2),(r,t,p,d3),(r,t,q,d4)):
        if abs(d)<=1e-9 and on(a,b,c):return True
    return False


def _dimension_segments(a,b,side,offset):
    da,db=a+side*offset,b+side*offset
    return [(da,db),(a,da),(b,db)]


def _choose_side(doc,obj,points,start,end,mid,side,offset,placement):
    # returns (side, offset used); search only ever increases the requested offset
    centroid=App.Vector(sum(p.x for p in points)/len(points),sum(p.y for p in points)/len(points),sum(p.z for p in points)/len(points))
    first=side if (mid-centroid).dot(side)>=0 else side*-1
    if placement=='centroid' or max(abs(p.z-points[0].z) for p in points)>1e-6:return first,offset
    # Search: prefer the outer side, flip only when the other side is collision free and this one is not.
    a,b=points[start],points[end]
    others=[]
    for i in range(len(points)-1):
        if i!=min(start,end) or abs(start-end)!=1:others.append((points[i],points[i+1]))
    if getattr(obj,'Closed',False) and len(points)>2 and not (set((start,end))=={0,len(points)-1}):others.append((points[-1],points[0]))
    for dim in doc.Objects:
        if hasattr(dim,'LinkedGeometry') and any(e[0]==obj for e in dim.LinkedGeometry):
            try:
                da,db=dim.Start,dim.End;v=db-da
                if v.Length>1e-7:
                    v.normalize();sd=App.Vector(0,0,1).cross(v);off=(dim.Dimline-(da+db)*0.5).dot(sd)
                    others.extend(_dimension_segments(da,db,sd,off))
            except Exception:pass
    def clean(sd,off):
        n=0
        for k,seg in enumerate(_dimension_segments(a,b,sd,off)):
            for o in others:
                if k>0 and ((seg[0]-o[0]).Length<1e-7 or (seg[0]-o[1]).Length<1e-7):continue
                if _seg_hit(seg[0],seg[1],o[0],o[1]):n+=1
        return n
    best=None
    for mult in (1,2,3,4):
        for sd in (first,first*-1):
            n=clean(sd,offset*mult)
            if best is None or n<best[0]:best=(n,sd,offset*mult)
            if n==0:return sd,offset*mult
    return best[1],best[2]


def linked_dimension(doc,obj,start,end,offset=100,placement='centroid'):
    import Draft
    from .documents import require_root_frame
    require_root_frame(obj,'Linked dimension')
    if obj.Document!=doc:raise ValueError('Dimension source belongs to a different document')
    if not math.isfinite(float(offset)):raise ValueError('Dimension offset must be finite')
    points=[v.Point for v in obj.Shape.Vertexes]
    if start==end or min(start,end)<0 or max(start,end)>=len(points):raise ValueError('Invalid vertex indices')
    direction=points[end]-points[start]
    if direction.Length<1e-7:raise ValueError('Coincident vertices')
    normal=App.Vector(0,0,1)
    side=normal.cross(direction)
    if side.Length<1e-7:side=App.Vector(1,0,0)
    side.normalize()
    mid=(points[start]+points[end])*0.5
    if placement not in ('legacy','centroid','search'):raise ValueError('Unknown dimension placement')
    offset=float(offset)
    if placement!='legacy':side,offset=_choose_side(doc,obj,points,start,end,mid,side,offset,placement)
    dimpoint=mid+side*offset
    doc.openTransaction('Add linked dimension')
    try:
        # Use native Draft proxy directly with an explicit plane normal. This avoids
        # Draft's current-view lookup race immediately after opening a document.
        from draftobjects.dimension import LinearDimension
        dim=doc.addObject('App::FeaturePython','Dimension');LinearDimension(dim)
        dim.LinkedGeometry=[(obj,'Vertex'+str(start+1)),(obj,'Vertex'+str(end+1))]
        dim.Support=obj;dim.Normal=normal;dim.Dimline=dimpoint
        if App.GuiUp:
            from draftviewproviders.view_dimension import ViewProviderLinearDimension
            ViewProviderLinearDimension(dim.ViewObject)
        dim.Label='بعد مرتبط بالرسم'
        from .documents import add_to
        add_to(doc,'DrawingSystem',dim)
        doc.recompute();doc.commitTransaction();return dim
    except Exception:doc.abortTransaction();doc.recompute();raise


def export_dimensioned(doc,obj,target,unit='mm'):
    """Current XY path plus linked dimensions. Vector PDF, fit-to-page only."""
    import os,tempfile,Part
    from .export import projection_svg,_page,path_for_python
    from .validation import valid_document
    valid_document(doc)
    from .documents import require_root_frame
    require_root_frame(obj,'Dimensioned path export')
    points=[v.Point for v in obj.Shape.Vertexes]
    if not points or max(p.z for p in points)-min(p.z for p in points)>1e-6:
        raise ValueError('Dimensioned PDF currently supports XY-plane paths only')
    dimensions=[o for o in doc.Objects if hasattr(o,'LinkedGeometry') and any(e[0]==obj for e in o.LinkedGeometry)]
    shapes=[obj.Shape];labels=[]
    for dim in dimensions:
        a,b=dim.Start,dim.End
        vector=b-a
        if abs(vector.z)>1e-6 or vector.Length<1e-7:raise ValueError('Invalid planar dimension')
        vector.normalize();side=App.Vector(0,0,1).cross(vector)
        delta=dim.Dimline-(a+b)*0.5
        offset=delta.dot(side)
        da,db=a+side*offset,b+side*offset
        for start,end in ((a,da),(b,db),(da,db)):
            if (end-start).Length>1e-7:shapes.append(Part.makeLine(start,end))
        arrow=min(20,(db-da).Length*0.05)
        for tip,direction in ((da,vector),(db,-vector)):
            for sign in (-1,1):
                shapes.append(Part.makeLine(tip,tip+direction*arrow+side*arrow*0.35*sign))
        middle=(da+db)*0.5
        if unit=='in':label=str(round(dim.Distance.Value/25.4,4))+' in ('+str(round(dim.Distance.Value,3))+' mm)'
        elif unit=='mm':label=str(round(dim.Distance.Value,3))+' mm'
        else:raise ValueError('Unit must be mm or in')
        outward=side*(1 if offset>=0 else -1)
        if abs(outward.x)>abs(outward.y):labels.append((label,middle.x,middle.y,'right' if outward.x>0 else 'left'))
        else:labels.append((label,middle.x-20,middle.y+15,'right'))
    svg=projection_svg(Part.makeCompound(shapes),App.Vector(0,0,1))
    parent=os.path.dirname(os.path.abspath(target))
    directory=path_for_python(parent)
    fd,temp=tempfile.mkstemp(suffix=b'.pdf' if isinstance(directory,bytes) else '.pdf',dir=directory);os.close(fd)
    path=temp.decode('utf-8') if isinstance(temp,bytes) else temp
    try:
        _page(path,'الرسم والأبعاد | '+obj.Label,[svg],annotations=labels,single=True,subtitle=('رسم وأبعاد مرتبطة | بوصة (والمليمتر بين قوسين)' if unit=='in' else None))
        with open(path_for_python(path),'rb') as f:
            if f.read(5)!=b'%PDF-':raise IOError('PDF output failed')
        os.replace(path_for_python(path),path_for_python(target))
    finally:
        if os.path.exists(path_for_python(path)):os.remove(path_for_python(path))
    return {'dimensions':len(dimensions),'values_mm':[o.Distance.Value for o in dimensions],'fit_to_page':True}
