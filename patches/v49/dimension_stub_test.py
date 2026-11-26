import sys,types,math,importlib.util
class V:
    def __init__(s,x=0,y=0,z=0):s.x,s.y,s.z=float(x),float(y),float(z)
    def __add__(s,o):return V(s.x+o.x,s.y+o.y,s.z+o.z)
    def __sub__(s,o):return V(s.x-o.x,s.y-o.y,s.z-o.z)
    def __mul__(s,k):return V(s.x*k,s.y*k,s.z*k)
    def dot(s,o):return s.x*o.x+s.y*o.y+s.z*o.z
    def cross(s,o):return V(s.y*o.z-s.z*o.y,s.z*o.x-s.x*o.z,s.x*o.y-s.y*o.x)
    @property
    def Length(s):return math.sqrt(s.dot(s))
    def normalize(s):
        l=s.Length;s.x/=l;s.y/=l;s.z/=l;return s
m=types.ModuleType('FreeCAD');m.Vector=V;sys.modules['FreeCAD']=m
spec=importlib.util.spec_from_file_location('d','/tmp/wcp/patches/v49/drafting_v10.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
class Dim:
    def __init__(s,key,dl):s.key=key;s.Dimline=dl;s.LinkedGeometry=[(OBJ,('Vertex%d'%(key[0]+1),)),(OBJ,('Vertex%d'%(key[1]+1),))]
OBJ=object()
class Doc:
    def __init__(s):s.Objects=[]
def run(P):
    pts=[V(*p) for p in P];doc=Doc()
    for i in range(len(pts)-1):
        a,b=pts[i],pts[i+1];v=(b-a);v.normalize();sd=V(0,0,1).cross(v);mid=(a+b)*0.5
        first=d._first_side(pts,i,i+1,mid,sd)
        pathsegs=[(pts[k],pts[k+1]) for k in range(len(pts)-1)]
        others=d._obstacles(pts,pathsegs,d._collect_dims(doc,OBJ),i)
        _,sdd,off=d._best_placement(a,b,first,100.0,others)
        doc.Objects.append(Dim((i,i+1),mid+sdd*off))
        d._repair_dims(doc,OBJ,pts)
    # count with strict metric (all segs incl. path, dim-dim)
    pathsegs=[(pts[k],pts[k+1]) for k in range(len(pts)-1)]
    allx=[]
    for dim in doc.Objects:
        s,e=dim.key;a,b=pts[s],pts[e];v=b-a;v.normalize();sd=V(0,0,1).cross(v);off=(dim.Dimline-(a+b)*0.5).dot(sd)
        allx.append(d._dimension_segments(a,b,sd,off))
    pb=db=0
    for k,mine in enumerate(allx):
        for idx,seg in enumerate(mine):
            for o in pathsegs:
                if idx>0 and ((seg[0]-o[0]).Length<1e-7 or (seg[0]-o[1]).Length<1e-7):continue
                if d._seg_hit_strict(seg[0],seg[1],o[0],o[1]):pb+=1
        for k2,m2 in enumerate(allx):
            if k2==k:continue
            for seg in mine:
                for s2 in m2:
                    if (seg[0]-s2[0]).Length<1e-7:continue
                    if d._seg_hit_strict(seg[0],seg[1],s2[0],s2[1]):db+=1
    return pb,db//2,[round((x.Dimline-(pts[x.key[0]]+pts[x.key[1]])*0.5).Length) for x in doc.Objects]
import time
for n,P in {'Z':[(0,0),(600,0),(0,300),(600,300)],'L':[(0,0),(800,0),(800,500)],'U':[(0,0),(0,400),(300,400),(300,0)],'stair':[(0,0),(400,0),(400,200),(600,200),(600,400),(800,400)],'zig5':[(0,0),(500,0),(0,200),(500,200),(0,400)]}.items():
    t=time.time();print(n,run(P),round(time.time()-t,2))
