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


def _seg_hit_strict(p,q,r,t):
    """True only for interior-interior crossings or collinear interior overlap.

    Endpoint grazes (T-junctions where a dimension line meets the path at one of
    its own endpoints) are normal drafting and do not count as crossings.
    """
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


def _dimension_segments(a,b,side,offset):
    da,db=a+side*offset,b+side*offset
    return [(da,db),(a,da),(b,db)]


_SEARCH_MULTS=(1,1.5,2,3,4,6,8,12,16,0.75,0.5,0.3)


def _dim_key(dim):
    """(start,end) vertex indices of a linked dimension, or None."""
    try:
        out=[]
        for _obj,sub in dim.LinkedGeometry:
            # FreeCAD returns sub-names either as a string or as a tuple/list of strings.
            if not isinstance(sub,str):
                sub=sub[0] if len(sub)>0 else ''
            if not sub.startswith('Vertex'):return None
            out.append(int(sub[6:])-1)
        return tuple(out) if len(out)==2 else None
    except Exception:return None


def _score_segments(mine,others):
    path_hits=0;dim_hits=0
    for seg in mine:
        for kind,o in others:
            if _seg_hit_strict(seg[0],seg[1],o[0],o[1]):
                if kind=='path':path_hits+=1
                else:dim_hits+=1
    return 1000*path_hits+dim_hits


def _best_placement(a,b,first,offset,others):
    best=None
    for mult in _SEARCH_MULTS:
        for sd in (first,first*-1):
            score=_score_segments(_dimension_segments(a,b,sd,offset*mult),others)
            if best is None or score<best[0]:best=(score,sd,offset*mult)
            if score==0:return best
    return best


def _collect_dims(doc,obj):
    dims=[]
    for dim in doc.Objects:
        if hasattr(dim,'LinkedGeometry') and any(e[0]==obj for e in dim.LinkedGeometry):
            key=_dim_key(dim)
            if key is not None:dims.append((dim,key))
    return dims


def _obstacles(points,pathsegs,dims,skip):
    others=[('path',seg) for i,seg in enumerate(pathsegs) if i!=skip]
    for dim,(s,e) in dims:
        if (s,e)==(skip,skip+1) or (e,s)==(skip,skip+1):continue
        a,b=points[s],points[e]
        v=b-a
        if v.Length<1e-7:continue
        v.normalize();sd=App.Vector(0,0,1).cross(v)
        off=(dim.Dimline-(a+b)*0.5).dot(sd)
        for seg in _dimension_segments(a,b,sd,off):others.append(('dim',seg))
    return others


def _first_side(points,start,end,mid,side):
    centroid=App.Vector(sum(p.x for p in points)/len(points),sum(p.y for p in points)/len(points),sum(p.z for p in points)/len(points))
    return side if (mid-centroid).dot(side)>=0 else side*-1


def _choose_side(doc,obj,points,start,end,mid,side,offset,placement):
    # returns (side, offset used)
    if placement=='centroid' or max(abs(p.z-points[0].z) for p in points)>1e-6:
        return _first_side(points,start,end,mid,side),offset
    # Search: score candidates; crossings of the measured path weigh 1000x crossings
    # of other dimensions; extension-line segments take part in the collision test.
    pathsegs=[(points[i],points[i+1]) for i in range(len(points)-1)]
    a,b=points[start],points[end]
    first=_first_side(points,start,end,mid,side)
    dims=_collect_dims(doc,obj)
    others=_obstacles(points,pathsegs,dims,start)
    _score,sd,off=_best_placement(a,b,first,offset,others)
    return sd,off


def _repair_dims(doc,obj,points):
    """Re-place linked dimensions until no dimension segment properly crosses the
    measured path or another dimension (endpoint grazes allowed). One new dimension
    can invalidate an earlier placement, so earlier dims join the re-search.
    Bounded: at most 5 passes over the set, each dim moved at most once per pass."""
    if max(abs(p.z-points[0].z) for p in points)>1e-6:return
    pathsegs=[(points[i],points[i+1]) for i in range(len(points)-1)]
    def total():
        dims=_collect_dims(doc,obj)
        t=0
        placed=[]
        for dim,(s,e) in dims:
            a,b=points[s],points[e]
            v=b-a
            if v.Length<1e-7:continue
            v.normalize();sd=App.Vector(0,0,1).cross(v)
            off=(dim.Dimline-(a+b)*0.5).dot(sd)
            mine=_dimension_segments(a,b,sd,off)
            others=[('path',seg) for seg in pathsegs]
            for prev in placed:others.extend(prev)
            t+=_score_segments(mine,others)
            placed.append([('dim',seg) for seg in mine])
        return t
    for _pass in range(5):
        if total()==0:return
        moved=False
        for dim,(s,e) in _collect_dims(doc,obj):
            a,b=points[s],points[e]
            v=b-a
            if v.Length<1e-7:continue
            v.normalize();side=App.Vector(0,0,1).cross(v)
            mid=(a+b)*0.5
            first=_first_side(points,s,e,mid,side)
            dims=_collect_dims(doc,obj)
            others=_obstacles(points,pathsegs,dims,s)
            score,sd,off=_best_placement(a,b,first,100.0,others)
            cur=(dim.Dimline-mid).dot(side)
            cur_score=_score_segments(_dimension_segments(a,b,side,cur),others)
            if score<cur_score:
                dim.Dimline=mid+sd*off
                moved=True
        if not moved:break
    if total()==0:return
    # Deterministic fallback: exhaustive joint search over side and offset multiples.
    dims=_collect_dims(doc,obj)
    items=[];ref=[]
    for dim,(sx,ex) in dims:
        a,b=points[sx],points[ex]
        v=b-a
        if v.Length<1e-7:continue
        v.normalize();side=App.Vector(0,0,1).cross(v)
        items.append((a,b,_first_side(points,sx,ex,(a+b)*0.5,side),sx));ref.append((dim,a,b))
    res=_joint_search(items,pathsegs)
    if res is None:return
    for (dim,a,b),(sd,off) in zip(ref,res):dim.Dimline=(a+b)*0.5+sd*off



def _joint_search(items,pathsegs):
    """Deterministic exhaustive placement for up to 4 dimensions.
    items: list of (a,b,first_side,skip_index). Returns [(side,offset)] with the lowest
    (path crossings*1000 + dim crossings, total offset), or None when too many dimensions."""
    n=len(items)
    if n==0 or n>4:return None
    cands=[]
    for a,b,first,skip in items:
        lst=[]
        for mult in _SEARCH_MULTS:
            for sd in (first,first*-1):lst.append((sd,100.0*mult))
        cands.append(lst)
    path_sc=[]
    for (a,b,first,skip),lst in zip(items,cands):
        others=[('path',seg) for i,seg in enumerate(pathsegs) if i!=skip]
        path_sc.append([_score_segments(_dimension_segments(a,b,sd,off),others) for sd,off in lst])
    pair={}
    for i in range(n):
        for j in range(i+1,n):
            tab=[]
            for sd1,o1 in cands[i]:
                seg1=_dimension_segments(items[i][0],items[i][1],sd1,o1)
                row=[]
                for sd2,o2 in cands[j]:
                    seg2=[('dim',x) for x in _dimension_segments(items[j][0],items[j][1],sd2,o2)]
                    row.append(_score_segments(seg1,seg2))
                tab.append(row)
            pair[(i,j)]=tab
    import itertools
    best=None
    for combo in itertools.product(*[range(len(c)) for c in cands]):
        sc=sum(path_sc[i][combo[i]] for i in range(n))
        for i in range(n):
            for j in range(i+1,n):sc+=pair[(i,j)][combo[i]][combo[j]]
        tot=sum(cands[i][combo[i]][1] for i in range(n))
        key=(sc,tot)
        if best is None or key<best[0]:best=(key,combo)
    return [cands[i][best[1][i]] for i in range(n)]


def linked_dimension(doc,obj,start,end,offset=100,placement='search'):
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
        doc.recompute()
        if placement=='search':_repair_dims(doc,obj,points)
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
        xs=[p.x for p in points];ys=[p.y for p in points]
        gap=max(12.0,0.035*math.hypot(max(xs)-min(xs),max(ys)-min(ys)))
        anchor=middle+outward*gap
        labels.append((label,anchor.x,anchor.y,'right' if outward.x>=0 else 'left'))
    svg=projection_svg(Part.makeCompound(shapes),App.Vector(0,0,1))
    parent=os.path.dirname(os.path.abspath(target))
    directory=path_for_python(parent)
    fd,temp=tempfile.mkstemp(suffix=b'.pdf' if isinstance(directory,bytes) else '.pdf',dir=directory);os.close(fd)
    path=temp.decode('utf-8') if isinstance(temp,bytes) else temp
    try:
        import inspect
        title='الرسم والأبعاد | '+obj.Label
        sub=('رسم وأبعاد مرتبطة | بوصة (والمليمتر بين قوسين)' if unit=='in' else None)
        if 'subtitle' in inspect.signature(_page).parameters:
            _page(path,title,[svg],annotations=labels,single=True,subtitle=sub)
        else:
            _page(path,title+((' | '+sub) if sub else ''),[svg],annotations=labels,single=True)
        with open(path_for_python(path),'rb') as f:
            if f.read(5)!=b'%PDF-':raise IOError('PDF output failed')
        os.replace(path_for_python(path),path_for_python(target))
    finally:
        if os.path.exists(path_for_python(path)):os.remove(path_for_python(path))
    return {'dimensions':len(dimensions),'values_mm':[o.Distance.Value for o in dimensions],'fit_to_page':True}
