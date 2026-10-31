"""South-wing correction (V5.2).

The model's south wing (the angled wing that runs from the south dome block towards the tracks, ending in the
round tower) points about 7 degrees too far east: its rear face stands up to 8.7 m outside the GSI building
outline (optimal_bvmap BldA), right on the real line of track 3.  The V5 re-layout therefore had to push tracks
3-10 round it in a sharp S-bend.  The wing is now bent back about its root, smoothly (the bend angle grows from 0
at the root to THETA over the first L metres along the wing), so walls, roofs and windows stay rigid locally and
nothing opens at the joints.

Shared by build_targets.py (building edge for the track clearance) and mod_relayout.py (the geometry itself).
"""
import math
import numpy as np

PIVOT = (129.5, 6.0)          # root of the wing (north-east corner where it leaves the south dome block)
AXIS = (0.825, 0.565)         # wing direction in plan (towards the round end tower)
L = 35.0                      # length over which the bend builds up (m)
THETA = math.radians(-7.0)    # final bend (negative = towards the plaza / south-west)
X_MIN = 118.0                 # vertices north of this are never touched


def bend_xy(X, Y):
    """Bent position of plan points (arrays)."""
    X = np.asarray(X, float); Y = np.asarray(Y, float)
    rx, ry = X - PIVOT[0], Y - PIVOT[1]
    s = np.clip((rx * AXIS[0] + ry * AXIS[1]) / L, 0.0, 1.0)
    s = np.where(X < X_MIN, 0.0, s)
    th = THETA * s * s * (3.0 - 2.0 * s)
    c, sn = np.cos(th), np.sin(th)
    return PIVOT[0] + c * rx - sn * ry, PIVOT[1] + sn * rx + c * ry


def bend_angle(X, Y):
    """Local rotation (rad) applied at plan point(s)."""
    X = np.asarray(X, float); Y = np.asarray(Y, float)
    rx, ry = X - PIVOT[0], Y - PIVOT[1]
    s = np.clip((rx * AXIS[0] + ry * AXIS[1]) / L, 0.0, 1.0)
    s = np.where(X < X_MIN, 0.0, s)
    return THETA * s * s * (3.0 - 2.0 * s)
