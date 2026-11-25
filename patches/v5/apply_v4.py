"""Delta Engineering v4 patches: applies v3 (apply_v3.py) first, then diagonal dimension label placement."""
import sys,os,subprocess
root=sys.argv[1]
here=os.path.dirname(os.path.abspath(__file__))
subprocess.check_call([sys.executable,os.path.join(here,'..','v3','apply_v3.py'),root])
DR_OLD=("        else:\n"
"            labels.append((str(round(dim.Distance.Value,3))+' mm',middle.x-20,middle.y+15,'right'))")
DR_NEW=("        elif abs(vector.y)<0.05:\n"
"            labels.append((str(round(dim.Distance.Value,3))+' mm',middle.x-20,middle.y+15,'right'))\n"
"        else:\n"
"            normal=side if offset>=0 else side*-1\n"
"            labels.append((str(round(dim.Distance.Value,3))+' mm',middle.x,middle.y,'normal',(normal.x,normal.y)))")
EX_OLD=("                for text,x,y,side in annotations:\n"
"                    px=target.x()+(x-box.x())*ratio\n"
"                    py=target.y()+(-y-box.y())*ratio\n"
"                    labelrect=QtCore.QRectF(px-125 if side=='left' else px+8,py-12,117,24)\n"
"                    painter.drawText(labelrect,int(QtCore.Qt.AlignRight if side=='left' else QtCore.Qt.AlignLeft),text)")
EX_NEW=("                for ann in annotations:\n"
"                    text,x,y,side=ann[:4]\n"
"                    px=target.x()+(x-box.x())*ratio\n"
"                    py=target.y()+(-y-box.y())*ratio\n"
"                    if side=='normal':\n"
"                        nx,ny=ann[4]\n"
"                        ax=px+nx*10;ay=py-ny*10\n"
"                        if nx>0.3:rx=ax;align=QtCore.Qt.AlignLeft\n"
"                        elif nx<-0.3:rx=ax-117;align=QtCore.Qt.AlignRight\n"
"                        else:rx=ax-58;align=QtCore.Qt.AlignHCenter\n"
"                        if ny>0.3:ry=ay-24\n"
"                        elif ny<-0.3:ry=ay\n"
"                        else:ry=ay-12\n"
"                        painter.drawText(QtCore.QRectF(rx,ry,117,24),int(align|QtCore.Qt.AlignVCenter),text)\n"
"                        continue\n"
"                    labelrect=QtCore.QRectF(px-125 if side=='left' else px+8,py-12,117,24)\n"
"                    painter.drawText(labelrect,int(QtCore.Qt.AlignRight if side=='left' else QtCore.Qt.AlignLeft),text)")
for base in (root+'/DeltaEngineering', root+'/package/Mod/DeltaEngineering/DeltaEngineering'):
    p=base+'/drafting.py';s=open(p,encoding='utf-8').read();assert DR_OLD in s
    open(p,'w',encoding='utf-8').write(s.replace(DR_OLD,DR_NEW))
    p=base+'/export.py';s=open(p,encoding='utf-8').read();assert EX_OLD in s
    open(p,'w',encoding='utf-8').write(s.replace(EX_OLD,EX_NEW))
    print('v4 patched',base)

