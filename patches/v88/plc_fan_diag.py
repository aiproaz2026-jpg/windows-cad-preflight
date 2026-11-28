# CI diagnostic: does the PLC device in gallery_elec7 get stub fan-out? Prints DeviceType, _wants_fan, fan_lengths.
import sys, json, os
src = open('patches/v76/gallery_elec7.py', encoding='utf-8').read() if os.path.exists('patches/v76/gallery_elec7.py') else open('C:/gallery_elec7.py', encoding='utf-8').read()
src = src.replace("OUT = 'C:/seed/gallery72'", "OUT = 'C:/seed/plcfan'")
ns = {'__name__': 'diag'}
exec(compile(src, 'gallery_elec7', 'exec'), ns)
out = {'done': False}
try:
    from DeltaEngineering import wire_route as R
    d = ns['d']; plc = ns['PLC']
    found = R.boxes(d)
    rect = None
    for o, r in found:
        if o is plc: rect = r
    out['device_type'] = str(plc.DeviceType)
    out['FanStubs'] = str(getattr(plc, 'FanStubs', None))
    out['wants_fan'] = R._wants_fan(plc)
    out['FAN'] = R.FAN
    out['rect'] = list(rect) if rect else None
    out['fan_lengths'] = R.fan_lengths(plc, rect) if rect else None
    out['terminals'] = list(plc.Terminals)
    out['done'] = True
except Exception:
    import traceback; out['error'] = traceback.format_exc()
os.makedirs('C:/seed/plcfan', exist_ok=True)
json.dump(out, open('C:/seed/plcfan/plcfan.json', 'w'), indent=1)
print(json.dumps(out))
