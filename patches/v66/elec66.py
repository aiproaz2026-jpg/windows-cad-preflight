import sys, json, os, traceback
import FreeCAD as App
sys.path.insert(0, 'C:/DeltaTest/Mod'); sys.path.insert(0, 'C:/DeltaTest/Mod/DeltaEngineering')
sys.path.insert(0, 'C:/DeltaTest/Mod/DeltaEngineering/DeltaEngineering')
OUT = 'C:/seed/elec66'; os.makedirs(OUT, exist_ok=True)
res = {'done': False}
try:
    App.getUserAppDataDir = lambda: OUT + '/'
    from DeltaEngineering import elec_libedit as L
    from DeltaEngineering.symbols import create
    ex = json.loads(L.EXAMPLE.split('\n}')[0] + '\n}')
    res['valid_example_errors'] = L.validate(ex)
    bad = {'X': {'label': 'a', 'terminals': ['1', '1'], 'prims': [['C', 0, 0, -1]]}}
    res['bad_rejected'] = len(L.validate(bad)) > 0
    try:
        L.save(bad); res['bad_save_blocked'] = False
    except ValueError:
        res['bad_save_blocked'] = True
    p = L.save(ex); res['user_file'] = p
    res['lib_count'] = L.reload_library()
    d = App.newDocument('LE')
    o = create(d, 'Symbol_Mine', 'X1', App.Vector(0, 0, 0))
    d.recompute()
    res['edges'] = len(o.Shape.Edges); res['terminals'] = list(o.Terminals)
    json.dump(json.load(open(p, encoding='utf-8')), open(OUT + '/elec_symbols.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    res['done'] = True
except Exception:
    res['error'] = traceback.format_exc()
json.dump(res, open(OUT + '/result.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False))
