import math,itertools
def build(m,z,pa_deg=20.0):
    pa=math.radians(pa_deg);rp=m*z/2;rb=rp*math.cos(pa);ra=rp+m;rd=rp-1.25*m;inv=math.tan(pa)-pa
    def th(r):
        ar=math.acos(min(1,rb/r));return math.pi/(2*z)+inv-(math.tan(ar)-ar)
    rs=max(rd,rb);ths=th(rs);radii=[rs+(ra-rs)*i/8 for i in range(9)];step=2*math.pi/z
    pt=lambda r,a:(r*math.cos(a),r*math.sin(a))
    segs=[];minlen=1e9
    for k in range(z):
        phi=step*k;path=[]
        if rd<rb:path.append(pt(rd,phi-ths))
        path+=[pt(r,phi-th(r)) for r in radii]
        path+=[pt(r,phi+th(r)) for r in reversed(radii)]
        if rd<rb:path.append(pt(rd,phi+ths))
        for a,b in zip(path,path[1:]):
            segs.append((a,b));minlen=min(minlen,math.dist(a,b))
        a0=phi+ths;a1=phi+step-ths;n=6
        arc=[pt(rd,a0+(a1-a0)*i/n) for i in range(n+1)]
        for a,b in zip(arc,arc[1:]):segs.append((a,b));minlen=min(minlen,math.dist(a,b))
    return segs,minlen,th(ra),th(rs)
def inter(p,q,r,t):
    def o(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    d1,d2,d3,d4=o(p,q,r),o(p,q,t),o(r,t,p),o(r,t,q)
    return d1*d2<0 and d3*d4<0
for m,z in [(1.5,12),(2,20),(3,40),(4,60),(2.5,96)]:
    segs,ml,tip,root=build(m,z)
    n=len(segs);bad=0
    for i in range(n):
        for j in range(i+2,n):
            if i==0 and j==n-1:continue
            if inter(*segs[i],*segs[j]):bad+=1
    # continuity check: consecutive endpoints
    gaps=max(math.dist(segs[i][1],segs[(i+1)%n][0]) for i in range(n))
    print(m,z,'minseg=%.4f tip_theta=%.4f root_theta=%.4f crossings=%d maxgap=%.4f'%(ml,tip,root,bad,gaps))
segs,ml,tip,root=build(1.5,12);n=len(segs)
for i in range(n):
    for j in range(i+2,n):
        if i==0 and j==n-1:continue
        if inter(*segs[i],*segs[j]):print(i,j,segs[i],segs[j],[math.hypot(*s[0]) for s in (segs[i],segs[j])])
