"""Delta Engineering v3 patches. Applied to the original v58 source zip. v2 (gui.py) + v3 (drafting.py)."""
import sys
root=sys.argv[1]
GUI_OLD="(title,'طول الحواف (mm)',item['length_mm'])"
GUI_NEW="(title,'مجموع أطوال حواف الجسم (mm)',item['length_mm'])"
GUI2_OLD="            if 'radius_mm' in item:values.append("
GUI2_ADD="            _o=App.ActiveDocument.getObject(item['object']) if App.ActiveDocument and item.get('object') else None\n            if _o is not None and hasattr(_o,'CenterlineLength'):values.append((title,'طول خط المركز للماسورة (mm)',_o.CenterlineLength.Value))\n"
DR_OLD="        labels.append((str(round(dim.Distance.Value,3))+' mm',middle.x-20,middle.y+15,'right'))"
DR_NEW=("        if abs(vector.y)>abs(vector.x):\n"
"            labels.append((str(round(dim.Distance.Value,3))+' mm',middle.x,middle.y,'right'))\n"
"        else:\n"
"            labels.append((str(round(dim.Distance.Value,3))+' mm',middle.x-20,middle.y+15,'right'))")
for base in (root+'/DeltaEngineering', root+'/package/Mod/DeltaEngineering/DeltaEngineering'):
    p=base+'/gui.py'
    s=open(p,encoding='utf-8').read()
    assert GUI_OLD in s and GUI2_OLD in s
    s=s.replace(GUI_OLD,GUI_NEW).replace(GUI2_OLD,GUI2_ADD+GUI2_OLD,1)
    open(p,'w',encoding='utf-8').write(s)
    p=base+'/drafting.py'
    s=open(p,encoding='utf-8').read()
    assert DR_OLD in s
    open(p,'w',encoding='utf-8').write(s.replace(DR_OLD,DR_NEW))
    print('patched',base)

