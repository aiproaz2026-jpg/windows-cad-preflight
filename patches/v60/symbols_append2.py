

# ---- v60 additions: data-driven, editable electrical symbol library (original illustrative shapes) ----
def _v60_load():
    import os, json
    try:
        from . import elec_lib_data as _d
    except Exception:
        import elec_lib_data as _d
    lib = dict(_d.LIB)
    try:
        udir = App.getUserAppDataDir()
    except Exception:
        udir = os.path.expanduser('~')
    uf = os.path.join(udir, 'elec_symbols.json')
    if os.path.isfile(uf):  # user file: {"Name": {"label": "...", "terminals": [...], "prims": [["L",[[x,y],...]],["C",x,y,r],["A",x,y,r,a0,a1]]}}
        try:
            for k, e in json.load(open(uf, encoding='utf-8')).items():
                lib[k] = (e['label'], tuple(e['terminals']), [tuple(p) if p[0] != 'L' else ('L', [tuple(q) for q in p[1]]) for p in e['prims']])
        except Exception as ex:
            App.Console.PrintWarning('elec_symbols.json ignored: %s\n' % ex)
    return lib


V60_LIB = _v60_load()
for _k, (_lab, _term, _pr) in V60_LIB.items():
    TEMPLATES.setdefault(_k, (_lab, tuple(_term)))
_outline_v59 = outline


def outline(device):
    kind = device.SymbolTemplate
    if kind not in V60_LIB:
        return _outline_v59(device)
    p = device.Position
    out = []
    for pr in V60_LIB[kind][2]:
        if pr[0] == 'L':
            pts = [p + App.Vector(x, y, 0) for x, y in pr[1]]
            out.append(Part.makePolygon(pts) if len(pts) > 2 else Part.makeLine(pts[0], pts[1]))
        elif pr[0] == 'C':
            out.append(Part.makeCircle(pr[3], p + App.Vector(pr[1], pr[2], 0)))
        elif pr[0] == 'A':
            out.append(Part.makeCircle(pr[3], p + App.Vector(pr[1], pr[2], 0), App.Vector(0, 0, 1), pr[4], pr[5]))
    return out
