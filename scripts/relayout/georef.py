"""Model <-> GSI z18 mosaic georeference for the Tokyo Station model.
Model axes: +X = south (along the Marunouchi building), +Y = east (rail side), metres.
Anchor: midpoint of the two dome lanterns found by 8-fold symmetry in the aerial photo,
model dome centres N(-104.0, 0.415) / S(107.0, 0.415)."""
import numpy as np
MPP = 0.48509                       # metres per pixel, z18 at 35.677 N
DOME_N_PX = np.array([1226.25, 1442.75])
DOME_S_PX = np.array([1105.00, 1837.25])
MID_PX = (DOME_N_PX + DOME_S_PX) / 2
S_PX = (DOME_S_PX - DOME_N_PX); S_PX = S_PX / np.linalg.norm(S_PX)   # model +X in pixel axes
E_PX = np.array([-S_PX[1], S_PX[0]]) * -1                            # model +Y in pixel axes
# check handedness: +Y should point to +px x (east)
if E_PX[0] < 0: E_PX = -E_PX
MID_MODEL = np.array([1.5, 0.415])
def model_to_px(X, Y):
    X = np.asarray(X, float) - MID_MODEL[0]; Y = np.asarray(Y, float) - MID_MODEL[1]
    px = MID_PX[0] + (X * S_PX[0] + Y * E_PX[0]) / MPP
    py = MID_PX[1] + (X * S_PX[1] + Y * E_PX[1]) / MPP
    return px, py
def px_to_model(px, py):
    dx = (np.asarray(px, float) - MID_PX[0]) * MPP; dy = (np.asarray(py, float) - MID_PX[1]) * MPP
    X = dx * S_PX[0] + dy * S_PX[1]; Y = dx * E_PX[0] + dy * E_PX[1]
    return X + MID_MODEL[0], Y + MID_MODEL[1]
