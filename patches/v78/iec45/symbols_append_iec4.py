# -*- coding: utf-8 -*-
# ---- IEC-style power/protection symbols: register the IEC library on top of the v60 library ----
# Append this file to DeltaEngineering/symbols.py AFTER symbols_append2.py (it needs V60_LIB and TEMPLATES).
# It only ADDS new '... (IEC)' keys; the existing '(illustr.)' symbols are left untouched.


def _iec4_merge():
    try:
        from . import elec_lib_iec4 as _iec
    except Exception:
        import elec_lib_iec4 as _iec
    for _k, (_lab, _term, _pr) in _iec.LIB_IEC.items():
        V60_LIB[_k] = (_lab, tuple(_term), _pr)
        TEMPLATES.setdefault(_k, (_lab, tuple(_term)))
    return len(_iec.LIB_IEC)


IEC4_LIB_COUNT = _iec4_merge()
