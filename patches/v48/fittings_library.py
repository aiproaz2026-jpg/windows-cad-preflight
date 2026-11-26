# SPDX-License-Identifier: GPL-3.0-or-later
"""Source-cited nominal fitting dimensions (ASME B16.9 fittings, ASME B16.5 Class 150 flanges).

Data only: nominal millimetre dimensions transcribed from the published sources listed per
table below. No standard text, drawings or CAD assets copied. These are dimensional values,
not a rating, material, tolerance or design-approval library. Every value below was checked
against the cited fetched sources on 2026-11-26; fields where the fetched sources disagreed
are marked in FIELD_NOTES and use the stated convention.
"""

NPS_RANGE = ['1', '1 1/4', '1 1/2', '2', '2 1/2', '3', '3 1/2', '4']

# --- ASME B16.9 long-radius 90-degree elbow, center-to-end A (mm) ---
# Sources (fetched 2026-11-26, values identical in both for NPS 1..4):
#  S1 https://reynoldsbauhm.co.uk/pipe-elbow-dimensions (states transcription from ASME B16.9-2018 Table 6.1-1)
#  S2 https://teshigroup.com/dimensional-standards/asme-b16-9-elbow-dimensions/
ELBOW_90_LR_A = {'1': 38, '1 1/4': 48, '1 1/2': 57, '2': 76, '2 1/2': 95, '3': 114, '3 1/2': 133, '4': 152}
ELBOW_90_LR_SOURCES = ['https://reynoldsbauhm.co.uk/pipe-elbow-dimensions',
                       'https://teshigroup.com/dimensional-standards/asme-b16-9-elbow-dimensions/']
ELBOW_90_LR_REVISION = 'ASME B16.9-2018 Table 6.1-1 (as stated by source S1)'

# --- ASME B16.9 long-radius 45-degree elbow, center-to-end B (mm); same two sources, identical values ---
ELBOW_45_LR_B = {'1': 22, '1 1/4': 25, '1 1/2': 29, '2': 35, '2 1/2': 44, '3': 51, '3 1/2': 57, '4': 64}
ELBOW_45_LR_SOURCES = ELBOW_90_LR_SOURCES
ELBOW_45_LR_REVISION = ELBOW_90_LR_REVISION

# --- ASME B16.9 short-radius 90-degree elbow, center-to-end A (mm); same two sources, identical values ---
ELBOW_90_SR_A = {'1': 25, '1 1/4': 32, '1 1/2': 38, '2': 51, '2 1/2': 64, '3': 76, '3 1/2': 89, '4': 102}
ELBOW_90_SR_SOURCES = ELBOW_90_LR_SOURCES
ELBOW_90_SR_REVISION = 'ASME B16.9-2018 Table 6.1-4 (as stated by source S1)'

# --- ASME B16.9 equal straight tee, center-to-end C (run) and M (outlet) (mm) ---
# Sources (fetched 2026-11-26, values identical in both for NPS 1..4):
#  S1 https://www.wermac.org/fittings/dim_tees_eq.html
#  S2 https://www.piping-world.com/dimensions-of-equal-straight-tees (page marked Last Updated 31 May 2023)
TEE_EQ_CM = {'1': (38, 38), '1 1/4': (48, 48), '1 1/2': (57, 57), '2': (64, 64),
             '2 1/2': (76, 76), '3': (86, 86), '3 1/2': (95, 95), '4': (105, 105)}
TEE_EQ_SOURCES = ['https://www.wermac.org/fittings/dim_tees_eq.html',
                  'https://www.piping-world.com/dimensions-of-equal-straight-tees']
TEE_EQ_REVISION = 'ASME B16.9 equal tee dimensions as published by both sources'

# --- ASME B16.9 concentric/eccentric reducer, end-to-end length H (mm) ---
# Sources (fetched 2026-11-26, values identical in both for all in-range pairs):
#  S1 https://www.wermac.org/fittings/dim_reducers.html
#  S2 https://www.lfpiping.com/wp-content/uploads/2023/08/Dimensions-of-concentric-eccentric-reducers-ASME-B16.9.pdf
REDUCER_H = {('1 1/4', '1'): 51, ('1 1/2', '1'): 64, ('1 1/2', '1 1/4'): 64,
             ('2', '1'): 76, ('2', '1 1/4'): 76, ('2', '1 1/2'): 76,
             ('2 1/2', '1'): 89, ('2 1/2', '1 1/4'): 89, ('2 1/2', '1 1/2'): 89, ('2 1/2', '2'): 89,
             ('3', '1 1/4'): 89, ('3', '1 1/2'): 89, ('3', '2'): 89, ('3', '2 1/2'): 89,
             ('3 1/2', '1 1/4'): 102, ('3 1/2', '1 1/2'): 102, ('3 1/2', '2'): 102, ('3 1/2', '2 1/2'): 102, ('3 1/2', '3'): 102,
             ('4', '1 1/2'): 102, ('4', '2'): 102, ('4', '2 1/2'): 102, ('4', '3'): 102, ('4', '3 1/2'): 102}
REDUCER_SOURCES = ['https://www.wermac.org/fittings/dim_reducers.html',
                   'https://www.lfpiping.com/wp-content/uploads/2023/08/Dimensions-of-concentric-eccentric-reducers-ASME-B16.9.pdf']
REDUCER_REVISION = 'ASME B16.9 reducer dimensions as published by both sources'

# --- ASME B16.5 Class 150 weld-neck flange connection dimensions (mm) ---
# Sources (fetched 2026-11-26):
#  S1 https://reynoldsbauhm.co.uk/pipe-flange-dimensions (exact-mm table; thickness INCLUDES the 1.6 mm raised face)
#  S2 https://rajendradatacenter.com/flanges/class-150/ (thickness EXCLUDES the 1.6 mm raised face, stated convention)
#  S3 https://www.zickwolff.de/wissen/en/flanges/dimensions-asme/ (connection dimensions: OD, bolt circle, holes, stud, RF)
# S1 and S2 thickness values agree after applying the stated 1.6 mm raised-face convention.
# FIELD_NOTES:
#  bolt_circle_mm: S1 gives 79.4 for NPS 1; S2/S3 print 79.2 (3.12 in rounded). 3-1/8 in = 79.375 mm; S1's 79.4 recorded.
#  hole_dia_mm: S1 15.9 / S2-equivalent 15.88 vs S3 15.7 for 1/2-in bolts; 15.9 (5/8 in) recorded.
#  thickness_min_mm: MINIMUM flange thickness WITHOUT raised face (B16.5 convention as stated by S2).
#  rf_height_mm: 1.6 (0.06 in) per S3 for Class 150-600.
FLANGE_CL150 = {
    '1':     {'od': 108.0, 'bolt_circle': 79.4,  'holes': 4, 'hole_dia': 15.9, 'bolt_in': '1/2', 'rf_dia': 50.8,  'thickness_min': 12.7},
    '1 1/4': {'od': 117.5, 'bolt_circle': 88.9,  'holes': 4, 'hole_dia': 15.9, 'bolt_in': '1/2', 'rf_dia': 63.5,  'thickness_min': 14.2},
    '1 1/2': {'od': 127.0, 'bolt_circle': 98.6,  'holes': 4, 'hole_dia': 15.9, 'bolt_in': '1/2', 'rf_dia': 73.0,  'thickness_min': 15.9},
    '2':     {'od': 152.4, 'bolt_circle': 120.7, 'holes': 4, 'hole_dia': 19.1, 'bolt_in': '5/8', 'rf_dia': 92.1,  'thickness_min': 17.5},
    '2 1/2': {'od': 177.8, 'bolt_circle': 139.7, 'holes': 4, 'hole_dia': 19.1, 'bolt_in': '5/8', 'rf_dia': 104.8, 'thickness_min': 20.6},
    '3':     {'od': 190.5, 'bolt_circle': 152.4, 'holes': 4, 'hole_dia': 19.1, 'bolt_in': '5/8', 'rf_dia': 127.0, 'thickness_min': 22.4},
    '3 1/2': {'od': 215.9, 'bolt_circle': 177.8, 'holes': 8, 'hole_dia': 19.1, 'bolt_in': '5/8', 'rf_dia': 139.7, 'thickness_min': 22.3},
    '4':     {'od': 228.6, 'bolt_circle': 190.5, 'holes': 8, 'hole_dia': 19.1, 'bolt_in': '5/8', 'rf_dia': 157.2, 'thickness_min': 22.4},
}
FLANGE_RF_HEIGHT = 1.6
FLANGE_SOURCES = ['https://reynoldsbauhm.co.uk/pipe-flange-dimensions',
                  'https://rajendradatacenter.com/flanges/class-150/',
                  'https://www.zickwolff.de/wissen/en/flanges/dimensions-asme/']
FLANGE_REVISION = 'ASME B16.5 Class 150 as published by the cited sources'

SCOPE_TEXT = ('Nominal fitting/flange dimensions only, from the recorded published sources. '
              'No material, pressure rating, tolerance, wall schedule, approval or design compliance inherited. '
              'A human piping engineer must sign off any real use.')


def record(obj, fitting_type, preset, sources, revision):
    for key in ('FittingPreset', 'FittingType', 'DimensionSource', 'DimensionRevision', 'DimensionScope'):
        if not hasattr(obj, key):
            obj.addProperty('App::PropertyString', key, 'Dimensional provenance')
    obj.FittingType = fitting_type
    obj.FittingPreset = preset
    obj.DimensionSource = ' | '.join(sources)
    obj.DimensionRevision = revision
    obj.DimensionScope = SCOPE_TEXT
    for key in ('FittingPreset', 'FittingType', 'DimensionSource', 'DimensionRevision', 'DimensionScope'):
        obj.setEditorMode(key, 1)


def status(fitting_type, preset):
    """Human-readable provenance summary for one fitted object."""
    table = {'elbow_90_lr': (ELBOW_90_LR_A, ELBOW_90_LR_SOURCES, ELBOW_90_LR_REVISION),
             'elbow_45_lr': (ELBOW_45_LR_B, ELBOW_45_LR_SOURCES, ELBOW_45_LR_REVISION),
             'elbow_90_sr': (ELBOW_90_SR_A, ELBOW_90_SR_SOURCES, ELBOW_90_SR_REVISION),
             'tee_eq': (TEE_EQ_CM, TEE_EQ_SOURCES, TEE_EQ_REVISION),
             'reducer': (REDUCER_H, REDUCER_SOURCES, REDUCER_REVISION),
             'flange_cl150_wn': (FLANGE_CL150, FLANGE_SOURCES, FLANGE_REVISION)}
    data, sources, revision = table[fitting_type]
    return {'preset': preset, 'dimensions_mm': data.get(preset) if not isinstance(preset, tuple) else data.get(preset),
            'sources': sources, 'revision': revision, 'scope': SCOPE_TEXT}
