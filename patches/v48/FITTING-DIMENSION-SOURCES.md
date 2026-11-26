# Fitting dimension sources (fittings_library.py)

All values fetched and cross-checked 2026-11-26. Nominal millimetre dimensions only.

| Table | Field | Sources | Agreement |
| --- | --- | --- | --- |
| ELBOW_90_LR_A | center-to-end A, LR 90 | reynoldsbauhm.co.uk/pipe-elbow-dimensions ; teshigroup.com/dimensional-standards/asme-b16-9-elbow-dimensions/ | identical NPS 1-4 |
| ELBOW_45_LR_B | center-to-end B, LR 45 | same two | identical NPS 1-4 |
| ELBOW_90_SR_A | center-to-end A, SR 90 | same two | identical NPS 1-4 |
| TEE_EQ_CM | run C / outlet M | wermac.org/fittings/dim_tees_eq.html ; piping-world.com/dimensions-of-equal-straight-tees (Last Updated 2023-05-31) | identical NPS 1-4 |
| REDUCER_H | end-to-end H, con/ecc | wermac.org/fittings/dim_reducers.html ; lfpiping.com PDF | identical for all in-range pairs |
| FLANGE_CL150 | od, bolt_circle, holes, hole_dia, bolt_in, rf_dia, thickness_min | reynoldsbauhm.co.uk/pipe-flange-dimensions ; rajendradatacenter.com/flanges/class-150/ ; zickwolff.de/wissen/en/flanges/dimensions-asme/ | see notes |

Notes:
- Flange thickness: reynoldsbauhm includes the 1.6 mm raised face; rajendradatacenter states it reports WITHOUT the 0.06 in raised face. After applying that convention the two agree for NPS 1-4. Recorded value is minimum thickness WITHOUT raised face; rf_height recorded separately (1.6 mm).
- Bolt circle NPS 1: reynoldsbauhm 79.4 vs zickwolff/rajendra 79.2; 3-1/8 in = 79.375 mm, recorded 79.4.
- Hole diameter for 1/2-in bolts: 15.9 recorded (5/8 in); zickwolff prints 15.7.
- A fourth source (microfinishgroup PDF) was discarded: its thickness values match neither convention.
- No standard text or drawings copied; values transcribed from the cited pages.
- Not included (no citable fetched source in range): flange hub dimensions X/Y for all sizes (only partially verifiable), pressure classes above 150, non-equal tees, pressure ratings, materials.
