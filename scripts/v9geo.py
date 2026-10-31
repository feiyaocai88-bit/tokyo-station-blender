"""V9 shared geometry of the JR Sobu / Yokosuka underground station (総武地下駅, B5), used by mod9_* and validate9_*.

Station frame (local coordinates, metres):
  x  along the platforms, + towards the Chiba / Shin-Nihombashi end (north-east), - towards Shimbashi / Kurihama
  y  across, + towards the west (away from the brick building), - towards the building (east)
  z  world height (plaza ground = 0)

Placement (model XY, +X south, +Y east):
  * orientation, length and along-track position: the two B5 island platforms in OpenStreetMap
    (ways 759432999 "総武3;総武4" and 759433000 "総武1;総武2", © OpenStreetMap contributors, ODbL), converted with
    a transform fitted on the ten surface platforms (lateral RMS 0.4-1.9 m) and checked against the GSI
    underground line of the Marunouchi Line already in the model data (OSM vs GSI: 1.1 / 1.4 m RMS);
  * across the platforms the OSM polygons are schematic (the two islands are drawn only ~10 m apart, which leaves
    no room for the two tracks between them), so the cross-section is designed here (2 islands x 10.6 m, 4 tracks)
    and the axis is moved 25.0 m west of the OSM midline so that
      - the box does not run under the station building (ja.wikipedia 東京駅: "丸の内側ロータリー直下にあり、上部に
        建物などの構造物がありません"), clearance to the building's west face >= 3.5 m, and
      - the existing ventilation tower in the plaza (V3, "横須賀・総武線地下ホーム用の換気塔") stands over the box.
    Expected placement uncertainty: about +/- 10 m across, +/- 5 m along the platforms.
Depth: rail top 28.0 m below the plaza ("地下鉄丸ノ内線の下、地下28mの位置", gendai.media); platform 1.04 m above rail
as on the surface; B4 concourse 6.06 m above the platform (the over-track soffit must clear the raised pantograph,
whose shoe is 5.42 m above rail in the model's train collections).
"""
import math
import numpy as np

# --------------------------------------------------------------- placement
NE_OSM = (-183.3, 2.6)       # mean NE end of the two OSM island polygons (model XY)
SW_OSM = (92.7, -101.0)      # mean SW end
SHIFT_W = 25.0               # metres, perpendicular towards the west (see header)
_d = np.array(NE_OSM) - np.array(SW_OSM)
AX = _d / np.linalg.norm(_d)                    # local +x in model XY  (-0.9362, 0.3514)
AY = np.array([-AX[1], AX[0]])                   # local +y in model XY  (-0.3514, -0.9362), right-handed
MID_OSM = (np.array(NE_OSM) + np.array(SW_OSM)) / 2
C = MID_OSM + SHIFT_W * AY                       # local origin (model XY)
YAW = math.atan2(AX[1], AX[0])                   # rotation of the local frame about +Z


def to_world(x, y, z=0.0):
    x = np.asarray(x, float); y = np.asarray(y, float)
    X = C[0] + x * AX[0] + y * AY[0]
    Y = C[1] + x * AX[1] + y * AY[1]
    return X, Y, z


def to_local(X, Y):
    d0 = np.asarray(X, float) - C[0]; d1 = np.asarray(Y, float) - C[1]
    return d0 * AX[0] + d1 * AX[1], d0 * AY[0] + d1 * AY[1]


def frame_matrix():
    from mathutils import Matrix
    return Matrix(((AX[0], AY[0], 0.0, C[0]),
                   (AX[1], AY[1], 0.0, C[1]),
                   (0.0, 0.0, 1.0, 0.0),
                   (0.0, 0.0, 0.0, 1.0)))


# --------------------------------------------------------------- levels (z, metres; plaza = 0)
RAIL = -28.00
DECK = RAIL + 1.04            # -26.96
INVERT = -28.60               # top of the base slab in the track zones
TRACKBED = -28.32             # top of the concrete track slab
BASE_BOT = -30.80
B5_CEIL = DECK + 3.00         # platform suspended ceiling, -23.96
B4_SOFFIT = -21.90            # underside of the B4 slab (6.10 m above rail)
B4_BEAM = -22.15              # bottom of the over-track transverse beams (5.85 m above rail)
B4_FLOOR = -20.90
B4_CEIL = -17.90
B3_SOFFIT, B3_FLOOR = -17.30, -16.50
B2_SOFFIT, B2_FLOOR = -13.20, -12.40
B1_SOFFIT, B1_FLOOR = -9.00, -8.20
B1_CEIL = -5.00
ROOF_SOFFIT, ROOF_TOP = -4.60, -3.60
LOWROOF_TOP = -15.50          # roof of the two-level part under the Marunouchi Line crossing
PANTO_SHOE = 5.42             # raised shoe top above rail (V4 pantograph collections)
WIRE_BOTTOM = RAIL + PANTO_SHOE   # contact-wire underside of the rigid conductor
BAR_TOP = WIRE_BOTTOM + 0.20

# --------------------------------------------------------------- plan
TRK = {1: -16.28, 2: -2.50, 3: 2.50, 4: 16.28}
EDGE = 1.59                   # track centre to platform edge (as on the surface)
ISL = {"1-2": (-14.69, -4.09), "3-4": (4.09, 14.69)}
ISL_C = {k: (a + b) / 2 for k, (a, b) in ISL.items()}     # -9.39 / +9.39
ISL_TRACKS = {"1-2": (1, 2), "3-4": (3, 4)}
WALL_IN, WALL_T = 18.68, 1.20
WALL_OUT = WALL_IN + WALL_T
PLAT_X = (-153.0, 153.0)
BOX_X = (-172.0, 172.0)       # inner faces of the end walls
END_T = 1.20
UPPER_X = (-60.0, 150.0)      # three-level upper part (B1-B3): starts past the Marunouchi Line crossing, ends inside the plinth
COL_ROW_OFF = 2.60            # island column rows at island centre +/- 2.60
COL_R_ISL, COL_R_MID = 0.50, 0.45
BAY = 7.0
COL_X = [3.5 + BAY * k for k in range(-24, 24)]            # -164.5 ... 164.5


def col_number(x):
    """Column numbers along the platform, 1 at the Shimbashi (SW) end."""
    return int(round((x - PLAT_X[0] - 2.5) / BAY)) + 1     # x = -150.5 -> 1 ... 150.5 -> 44


# B5 -> B4 stair / escalator groups: centre x along both islands (fractions read off the JR East B5F plan)
GROUP_FRAC = [0.15, 0.29, 0.44, 0.57, 0.71, 0.86]
GROUP_X = [round(PLAT_X[0] + (PLAT_X[1] - PLAT_X[0]) * f, 1) for f in GROUP_FRAC]
GROUP_LEN = 16.0
ENCL_HALF = 2.05              # enclosure outer half width (walls 1.93 .. 2.05)
ENCL_IN = 1.93
STAIR_RISE = B4_FLOOR - DECK  # 6.06


def group_frame(gx, isl):
    """(foot_x, s, yc): stairs rise towards the middle of the station; s = +1 rises towards +x."""
    s = 1 if gx < 0 else -1
    return gx - s * GROUP_LEN / 2, s, ISL_C[isl]


def group_opening(gx, isl):
    """B4-slab opening above a group, as (x0, x1, y0, y1) in local coordinates."""
    xf, s, yc = group_frame(gx, isl)
    u0, u1 = 6.5, 15.6
    a, b = sorted((xf + s * u0, xf + s * u1))
    return a, b, yc - ENCL_IN, yc + ENCL_IN


ELEV = {"1-2": (-4.0, ISL_C["1-2"], "B1"), "3-4": (1.0, ISL_C["3-4"], "B4")}   # x, y, top level
ELEV_SIZE = (2.4, 2.6)

# B4 -> B1 long escalator banks (foot at B4, rising along s)
BANKS = {"A": (-6.0, -1), "B": (40.0, 1)}
BANK_HALF = 2.80
BANK_LEN = 27.4

B4_HALL_X = (-128.0, 128.0)
B4_HALL_Y = 14.2
B1_HALL_X = (-58.0, 95.0)
B1_GATES_X = -45.0
B1_CORRIDOR_X = (-56.0, -49.0)
B1_CORRIDOR_Y = -32.0

# existing V3 ventilation tower (model XY centre (-57.4, -79.3)) -> shaft from B2 to just under the plaza
VENT_XY_MODEL = (-57.35, -79.25)
VENT_HALF = 3.25
VENT_TOP = -0.45

# plinth footprint (Display base): every V9 vertex above STUDIO_FLOOR must stay inside it
PLINTH = (-215.0, 255.0, -151.0, 225.4)
STUDIO_FLOOR = -4.2

# Tokyo Metro Marunouchi Line, OSM way 661604130 in model XY (context only, simplified box tunnel)
MARUNOUCHI_MODEL = [(-72.8, -131.5), (-36.0, -124.6), (-26.4, -122.7), (31.7, -110.8), (63.0, -101.1),
                    (85.4, -90.2), (110.5, -70.9), (133.0, -48.0), (157.2, -23.5)]
MARU_Z = (-11.5, -4.6)
MARU_HALF = 4.8

# trains: 15 cars at 20.25 m pitch, car 1 at the Kurihama (-x) end
CAR_PITCH = 20.25
CAR_X = [-141.75 + CAR_PITCH * i for i in range(15)]

# --------------------------------------------------------------- review cameras (local position, local target, lens)
CUT_Y = 11.5                  # section plane of the cutaway view (local y)
REVIEW_CAMS = [  # name, local position, local target, lens
    ("V9 01 B5 PLATFORM 1-2 | Yokosuka Line train on track 1, spandrel ceiling, column bands", (-95.0, -8.4, DECK + 1.6), (-40.0, -10.2, DECK + 1.2), 24),
    ("V9 02 B5 PLATFORM 3-4 | Sobu Rapid train for Chiba on track 4", (-148.5, 13.2, DECK + 1.65), (-110.0, 16.0, DECK + 1.1), 24),
    ("V9 03 B5 | across tracks 2 and 3: over-track soffit, beams, rigid conductor", (-26.0, -4.6, DECK + 1.6), (-8.0, 11.0, DECK + 0.9), 20),
    ("V9 04 B5 TRACK 1 | the Yokosuka Line train at the Shimbashi end", (-162.0, -13.6, RAIL + 2.3), (-151.0, -16.28, RAIL + 2.0), 24),
    ("V9 05 B5 | stair and escalator to the B4 concourse", (-122.0, -8.6, DECK + 1.6), (-100.0, -9.39, DECK + 3.2), 20),
    ("V9 06 B4 CONCOURSE | stair wells, guide lines, signs", (-110.0, 2.0, B4_FLOOR + 1.6), (-40.0, -2.0, B4_FLOOR + 1.0), 22),
    ("V9 07 B4 -> B1 | long escalators and stair (bank B)", (35.5, 0.9, B4_FLOOR + 1.7), (60.0, 0.0, B1_FLOOR + 0.6), 20),
    ("V9 08 B1 CONCOURSE | ticket gates towards 丸の内地下中央口", (-30.0, 9.0, B1_FLOOR + 1.6), (-50.0, -4.0, B1_FLOOR + 1.0), 20),
    ("V9 09 CUTAWAY | the five levels under the Marunouchi plaza (section at y = 11.5 m)", (185.0, 58.0, -7.0), (60.0, 2.0, -18.0), 22),
    ("V9 10 B5 TRACK 2 | looking along the empty track 2", (-150.0, -2.5, RAIL + 3.4), (-60.0, -3.5, RAIL + 2.8), 26),
]

