"""CD metrology (planned, v0.2+).

Planned modules, following the thin-film pattern (physics/model -> fit -> wafer -> SPC):
    image_preprocess.py   denoise, flatten, charging/contrast normalisation for CD-SEM images
    edge_detection.py     threshold / max-derivative / model-based edge finding
    cd_measurement.py     top/middle/bottom CD, LER/LWR (power spectral density)
    overlay.py            overlay vectors, linear model (translation, rotation, scale), residuals
Site-level CD results use the same long schema (parameter = 'cd_nm') so the existing
wafer-map, SPC, MSA and matching modules apply unchanged.
"""
