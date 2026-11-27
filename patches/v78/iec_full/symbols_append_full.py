

# ---- v75full additions: IEC-style variants of the electrical symbol library (original drawings, not IEC 60617 copies) ----
def _v75full_load():
    try:
        from . import elec_lib_iec_full as _i
    except Exception:
        import elec_lib_iec_full as _i
    return dict(_i.LIB_IEC)


V75F_LIB = _v75full_load()
for _k, (_lab, _term, _pr) in V75F_LIB.items():
    TEMPLATES.setdefault(_k, (_lab, tuple(_term)))
# same renderer path as the v60 library: outline() renders anything present in V60_LIB,
# and term_ends.build_table() picks up the two-terminal IEC-style symbols automatically.
V60_LIB.update(V75F_LIB)
