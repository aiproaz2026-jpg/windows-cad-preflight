# Parts library dimension sources (parts_library.py)

All values fetched and cross-checked 2026-11-26. Nominal millimetre values only. Each family was
verified against two independent fetched sources; disagreements are noted.

| Table | Standard basis (as stated by sources) | Source 1 | Source 2 | Agreement |
| --- | --- | --- | --- | --- |
| NUTS_ISO4032 | ISO 4032 style 1 | fasteners.eu/standards/iso/4032/ | mechcodex.com/reference/hex-nut-dimensions-metric | identical M4-M36 (P, s, e min, m max) |
| BOLTS_ISO4014 | ISO 4014/4017 | wermac.org/bolts/metricBDC.html (grade A limits; nominal = max) | mechcodex.com/reference/hex-bolt-dimensions-metric | identical nominal s (ISO variant) and k, M5-M64. Both sources note ISO vs DIN s differs at M10 (16/17), M12 (18/19), M14 (21/22), M22 (34/32); ISO values recorded |
| WASHERS_ISO7089 | ISO 7089 normal series | boltnote.net/en/lib/iso-7089-7090 | partxt.com/standards/iso-7089/ | identical M4-M36 (d1, d2, h) |
| BEARINGS_62 | ISO 15 boundary dims | normtorial.com/bearings/6200-series-ball-bearing/ | nbkbearingusa.com/single-row-deep-groove-ball-bearings-62-series/ | identical d/D/B 6200-6220; r min from S1 only (S2 does not list chamfer) |
| IPE | IPE sections | indumor.com/en/tables/ipe-beam-dimensions.php | normtorial.com/profiles/ipe/ | identical h/b/tw/tf/r IPE 80-450 |
| SpurGear | none (formula) | standard involute, pressure angle 20 deg, addendum = module, dedendum = 1.25 x module | - | computed, no table source |

Modeling simplifications (honest labels):
- Bolt and nut threads are NOT modeled; shank and bore are plain cylinders.
- Bearing internals simplified to inner + outer rings (no balls, no cage, no seals).
- IPE flange/web fillet radius r is recorded in the table but the profile is drawn without fillets.
- Gear tooth tip land is drawn as a chord, not an arc (small approximation).
- Load ratings from the bearing sources are NOT included (no design values ship).

Not included (no citable fetched source yet): 63xx/60xx bearing series, ISO 4033/4035 nuts,
ISO 7090/7091 washers, HEB/HEA/UPN sections, socket-head bolts (ISO 4762), set screws.
These can be appended with the same two-source check when needed.
