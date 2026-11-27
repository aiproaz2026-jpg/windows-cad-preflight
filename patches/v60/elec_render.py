import math
from PIL import Image, ImageDraw
import elec_lib_data as d
def sheet(path, cols=6, cell=190, S=2):
    keys=list(d.LIB); rows=(len(keys)+cols-1)//cols
    im=Image.new('RGB',(cols*cell,rows*cell),'white'); dr=ImageDraw.Draw(im)
    for i,k in enumerate(keys):
        lab,term,prims=d.LIB[k]; cx=(i%cols)*cell+cell//2; cy=(i//cols)*cell+cell//2-8
        P=lambda x,y:(cx+x*S*0.9,cy+y*S*0.9)
        for p in prims:
            if p[0]=='L': dr.line([P(*q) for q in p[1]],fill='black',width=2)
            elif p[0]=='C': x,y,r=p[1:]; dr.ellipse([P(x-r,y-r),P(x+r,y+r)],outline='black',width=2)
            else:
                x,y,r,a0,a1=p[1:]; pts=[]
                for n in range(25):
                    a=math.radians(a0+(a1-a0)*n/24); pts.append(P(x+r*math.cos(a),y-r*math.sin(a)))
                dr.line(pts,fill='black',width=2)
        dr.text((cx-cell//2+4,(i//cols)*cell+cell-16),k[:30]+' '+','.join(term)[:20],fill='blue')
    im.save(path)
sheet('/tmp/elec_sheet.png')
