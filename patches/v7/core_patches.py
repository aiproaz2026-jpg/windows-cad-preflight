# v7 source patches to shipped modules (idempotent). Applied with apply(pkgdir) before the package is imported.
import os


def _sub(path, old, new, marker):
    s = open(path, encoding='utf-8', newline='').read()
    if marker in s:
        return 'already'
    assert old in s, 'anchor not found in ' + path + ': ' + old[:50]
    open(path, 'w', encoding='utf-8', newline='').write(s.replace(old, new, 1))
    return 'patched'


def apply(pkg):
    out = {}
    core = os.path.join(pkg, 'core.py')
    # 1) terminal pitch: at least 14 mm between terminals on devices with more than 4 terminals (legibility)
    out['pitch'] = _sub(core,
        "    y=30-60*(index+1)/(len(terminals)+1)\n",
        "    span=60 if len(terminals)<=4 else 14*(len(terminals)+1)  # v7 pitch\n    y=span/2-span*(index+1)/(len(terminals)+1)\n",
        '# v7 pitch')
    # 2) routed wires: each terminal gets its own vertical channel so parallel conductors do not overlap
    out['channels'] = _sub(core,
        "            start=a+App.Vector(source_sign*20,0,0);end=b+App.Vector(target_sign*20,0,0)\n",
        "            _si=list(obj.SourceDevice.Terminals).index(obj.SourceTerminal) if hasattr(obj,'SourceTerminal') else 0  # v7 channel\n"
        "            _ti=list(obj.TargetDevice.Terminals).index(obj.TargetTerminal) if hasattr(obj,'TargetTerminal') else 0\n"
        "            start=a+App.Vector(source_sign*(20+9*_si),0,0);end=b+App.Vector(target_sign*(20+9*_ti),0,0)\n",
        '# v7 channel')
    # 3) wire ID labels on the electrical page
    exp = os.path.join(pkg, 'export.py')
    out['wire_labels'] = _sub(exp,
        "        _page(temporary[1],'الكهرباء | توصيلات منطقية تجريبية',[views[2]],rows,labels)",
        "        for _w in [o for o in d.Objects if hasattr(o,'SourceTerminal') and not o.Shape.isNull()]:  # v7 wire labels\n"
        "            _e=max(_w.Shape.Edges,key=lambda e:e.Length);_m=_e.CenterOfMass\n"
        "            labels.append((_w.WireId,_m.x,_m.y,'right'))\n"
        "        _page(temporary[1],'الكهرباء | توصيلات منطقية تجريبية',[views[2]],rows,labels)",
        '# v7 wire labels')
    return out
