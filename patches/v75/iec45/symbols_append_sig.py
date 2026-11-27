

# ---- v69 additions: IEC-style signalling and measuring symbols (lamps, buzzers, meters) ----
# Append AFTER symbols_append2.py (v60): this block registers into TEMPLATES and extends the
# v60 rendering table V60_LIB in place, so the existing outline() renders the new symbols too.
def _v69_load():
    try:
        from . import elec_sig_meter as _sm
    except Exception:
        import elec_sig_meter as _sm
    return dict(_sm.LIB)


V69_LIB = _v69_load()
for _k, (_lab, _term, _pr) in V69_LIB.items():
    TEMPLATES.setdefault(_k, (_lab, tuple(_term)))
try:
    V60_LIB.update(V69_LIB)
except NameError:
    pass  # symbols_append2 not applied yet; templates still registered
