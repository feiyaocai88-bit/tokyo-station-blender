#!/bin/bash
# Rebuild Tokyo Station V5 from the untouched V4 file, module by module (V6: "v6" mode, V7: "v7" mode, V8: "v8" mode, V9: "v9" mode, see below).
# usage: BLENDER_PY=/path/to/python-with-bpy-5.2 ./run_pipeline.sh /path/to/Tokyo_Station_V4.blend /path/to/output_dir
#   (or run each module inside Blender:  blender -b --python-exit-code 1 -P mod_x.py -- in.blend out.blend
#    after changing sys.argv handling accordingly)
# The track/platform re-layout reads targets.json (next to this script). It was produced by
# relayout/build_targets.py from GSI vector-tile track centrelines; see sources_and_licenses/GSI_Layout_Sources.txt.
set -e
PY=${BLENDER_PY:-python3}
S=$(cd "$(dirname "$0")" && pwd)
if [ "${1:-}" = "v9" ]; then
  BL=${BLENDER:-blender}
  V8=${2:?path to Tokyo_Station_V8.blend}
  OUT=${3:-.}
  PKG=${4:-$OUT/Tokyo_Station_V9}
  mkdir -p "$OUT" "$PKG"
  ${PYTHON:-python3} "$S/make9_textures.py"
  [ -f "$PKG/README_CN.txt" ] || echo "note: README_CN.txt is not in $PKG yet; mod9_finalize.py embeds it only if present"
  b() { echo "== $1"; "$BL" -b "$2" --python-exit-code 1 -P "$S/$1" -- "${@:3}"; }
  b mod9_sobu_station.py   "$V8"                         "$OUT/V9_s1_station.blend" "$OUT/station_report.json"
  b mod9_trains_people.py  "$OUT/V9_s1_station.blend"    "$OUT/V9_s2_trains.blend" "$OUT/trains_report.json"
  b mod9_finalize.py       "$OUT/V9_s2_trains.blend"     "$PKG/Tokyo_Station_V9.blend" "$PKG"
  b validate9_sobu.py      "$PKG/Tokyo_Station_V9.blend" "$OUT/validate_sobu.json"
  b validate8_level.py     "$PKG/Tokyo_Station_V9.blend" "$OUT/validate_level.json"
  b validate8_canopies.py  "$PKG/Tokyo_Station_V9.blend" "$OUT/validate_canopies.json"
  b validate7_interiors.py "$PKG/Tokyo_Station_V9.blend" "$OUT/validate_interiors.json"
  b validate6_platforms.py "$PKG/Tokyo_Station_V9.blend" "$OUT/validate_platforms.json"
  b validate6_catenary.py  "$PKG/Tokyo_Station_V9.blend" "$OUT/validate_catenary.json"
  b validate6_trains.py    "$PKG/Tokyo_Station_V9.blend" "$OUT/validate_trains.json"
  b render_review_cams_v9.py "$PKG/Tokyo_Station_V9.blend" "$PKG/previews" 64
  exit 0
fi
if [ "${1:-}" = "v8" ]; then
  BL=${BLENDER:-blender}
  V7=${2:?path to Tokyo_Station_V7.blend}
  OUT=${3:-.}
  PKG=${4:-$OUT/Tokyo_Station_V8}
  mkdir -p "$OUT" "$PKG"
  b() { echo "== $1"; "$BL" -b "$2" --python-exit-code 1 -P "$S/$1" -- "${@:3}"; }
  b mod8_shinkansen_level.py "$V7"                         "$OUT/V8_s1_level.blend" "$OUT/level_report.json"
  b mod8_canopies.py         "$OUT/V8_s1_level.blend"      "$OUT/V8_s2_canopies.blend" "$OUT/canopies_report.json"
  b mod8_finalize.py         "$OUT/V8_s2_canopies.blend"   "$PKG/Tokyo_Station_V8.blend" "$PKG"
  b validate8_level.py       "$PKG/Tokyo_Station_V8.blend" "$OUT/validate_level.json"
  b validate8_canopies.py    "$PKG/Tokyo_Station_V8.blend" "$OUT/validate_canopies.json"
  b validate7_interiors.py   "$PKG/Tokyo_Station_V8.blend" "$OUT/validate_interiors.json"
  b validate6_platforms.py   "$PKG/Tokyo_Station_V8.blend" "$OUT/validate_platforms.json"
  b validate6_catenary.py    "$PKG/Tokyo_Station_V8.blend" "$OUT/validate_catenary.json"
  b validate6_trains.py      "$PKG/Tokyo_Station_V8.blend" "$OUT/validate_trains.json"
  exit 0
fi
if [ "${1:-}" = "v7" ]; then
  BL=${BLENDER:-blender}
  V6=${2:?path to Tokyo_Station_V6.blend}
  OUT=${3:-.}
  PKG=${4:-$OUT/Tokyo_Station_V7}
  mkdir -p "$OUT" "$PKG"
  b() { echo "== $1"; "$BL" -b "$2" --python-exit-code 1 -P "$S/$1" -- "${@:3}"; }
  b mod7_train_interiors.py "$V6"                        "$OUT/V7_s0_interiors.blend" "$OUT/interiors_report.json"
  b mod7_finalize.py        "$OUT/V7_s0_interiors.blend" "$PKG/Tokyo_Station_V7.blend" "$PKG"
  b validate7_interiors.py  "$PKG/Tokyo_Station_V7.blend" "$OUT/validate_interiors.json"
  b validate6_platforms.py  "$PKG/Tokyo_Station_V7.blend" "$OUT/validate_platforms.json"
  b validate6_catenary.py   "$PKG/Tokyo_Station_V7.blend" "$OUT/validate_catenary.json"
  b validate6_trains.py     "$PKG/Tokyo_Station_V7.blend" "$OUT/validate_trains.json"
  exit 0
fi
if [ "${1:-}" = "v6" ]; then
  BL=${BLENDER:-blender}
  V5=${2:?path to Tokyo_Station_V5.blend}
  OUT=${3:-.}
  PKG=${4:-$OUT/Tokyo_Station_V6}
  mkdir -p "$OUT" "$PKG"
  ${PYTHON:-python3} "$S/make6_sign_textures.py" "$S/textures"
  ${PYTHON:-python3} "$S/make6_train_textures.py" "$S/textures"
  b() { echo "== $1"; "$BL" -b "$2" --python-exit-code 1 -P "$S/$1" -- "${@:3}"; }
  b mod6_platforms.py  "$V5"                     "$OUT/V6_s0_platforms.blend" "$OUT/platforms_report.json"
  b mod6_catenary.py   "$OUT/V6_s0_platforms.blend" "$OUT/V6_s1_catenary.blend" "$OUT/catenary_report.json"
  b mod6_trains.py     "$OUT/V6_s1_catenary.blend"  "$OUT/V6_s2_trains.blend" "$OUT/trains_report.json"
  b mod6_finalize.py   "$OUT/V6_s2_trains.blend"    "$PKG/Tokyo_Station_V6.blend" "$PKG"
  b validate6_platforms.py "$PKG/Tokyo_Station_V6.blend" "$OUT/validate_platforms.json"
  b validate6_catenary.py  "$PKG/Tokyo_Station_V6.blend" "$OUT/validate_catenary.json"
  b validate6_trains.py    "$PKG/Tokyo_Station_V6.blend" "$OUT/validate_trains.json"
  exit 0
fi
V4=${1:?path to Tokyo_Station_V4.blend}
OUT=${2:-.}
mkdir -p "$OUT"
run() { echo "== $1"; $PY -I "$S/$1" "$2" "$3"; }
run mod_relayout.py      "$V4"                        "$OUT/V5_s0_relayout.blend"
run mod_domes.py         "$OUT/V5_s0_relayout.blend"  "$OUT/V5_s1_domes.blend"
run mod_dome_interior.py "$OUT/V5_s1_domes.blend"     "$OUT/V5_s2_interior.blend"
run mod_central_roof.py  "$OUT/V5_s2_interior.blend"  "$OUT/V5_s2b_central.blend"
run mod_train_bodies.py  "$OUT/V5_s2b_central.blend"  "$OUT/V5_s3a_bodies.blend"
run mod_trains.py        "$OUT/V5_s3a_bodies.blend"   "$OUT/V5_s3_trains.blend"
run mod_shinkansen_roofs.py "$OUT/V5_s3_trains.blend" "$OUT/V5_s3b_roofs.blend"
run probe_platforms.py   "$OUT/V5_s3b_roofs.blend"    "$S/platforms.json"
run mod_platforms.py     "$OUT/V5_s3b_roofs.blend"    "$OUT/V5_s4_platforms.blend"
run mod_trackside.py     "$OUT/V5_s4_platforms.blend" "$OUT/V5_s5_trackside.blend"
run mod_finalize.py      "$OUT/V5_s5_trackside.blend" "$OUT/Tokyo_Station_V5.blend"


# V6 (round 6): see the "v6" branch at the top of this script:
#   BLENDER=/path/to/blender ./run_pipeline.sh v6 /path/to/Tokyo_Station_V5.blend /path/to/output_dir [package_dir]
# V7 (round 7): see the "v7" branch at the top of this script (starts from the V6 file):
#   BLENDER=/path/to/blender ./run_pipeline.sh v7 /path/to/Tokyo_Station_V6.blend /path/to/output_dir [package_dir]
# V9 (round 9, Sobu / Yokosuka underground station): "v9" branch at the top (starts from the V8 file):
#   BLENDER=/path/to/blender ./run_pipeline.sh v9 /path/to/Tokyo_Station_V8.blend /path/to/output_dir [package_dir]
