# Tokyo Station – Blender model

![Overview of the model](images/hero_overview.jpg)

A diorama-style 3D model of Tokyo Station, made in Blender 5.2. It covers:

- the red-brick Marunouchi station building with both domes;
- the Marunouchi plaza;
- all conventional and Shinkansen platforms, with tracks, overhead lines and trains;
- the JR Sobu Rapid / Yokosuka Line underground station, five levels below the plaza.
- the Tokyo Metro Marunouchi Line M17 station and a six-car 2000-series train in V11.

The model is built with Blender Python scripts. Automatic checks test clearances, headroom and train placement.

> This is an interpretive model, not survey data. Track and platform positions are matched to GSI (Geospatial Information Authority of Japan) data and OpenStreetMap. Heights, interiors and many details are estimates. See [Accuracy and limitations](#accuracy-and-limitations).

## V13 site details and connected ground entrances

V13 corrects the acoustic screens that continued almost 100 m beyond the Chuo viaduct. All three screen runs now derive their ends from the actual deck meshes, with supports landing on the deck edge. Twenty tracks gain deeper ballast cribs, physical stone fragments, cable-trough lids, junction boxes and rail bonds; existing rails, sleeper instances and train positions are retained.

![Central imperial entrance and forecourt](images/v13/imperial_entrance.jpg)

The central imperial porte-cochere is rebuilt with round brick-and-stone piers, a layered cornice, recessed ornamental iron gates and a planted, balustraded forecourt. Three service buildings gain end-wall louvres, doors, roof seams, ducts and maintenance details. New M7/M8 surface pavilions have real ground openings, two stair flights and continuous passages to the existing Marunouchi Line B1 concourse.

| | |
|---|---|
| ![Corrected screen ends](images/v13/barriers.jpg) | ![Track details](images/v13/track.jpg) |
| Screens end on the Chuo viaduct | Exposed sleepers, fastenings and ballast |
| ![M8 ground entrance](images/v13/metro_entrance.jpg) | ![Service building](images/v13/service_building.jpg) |
| Glazed entrance and stairs connecting to B1 | End louvres, roof fittings and service alley |

The model contains a separate `V13 Metro access cutaway` scene and 12 V13 review cameras. Validation checks all retained V12 source geometry and transforms, screen extents, evaluated sleeper instances, stair openings and headroom, passage continuity, enclosed passage walls and the recessed gate. All V12 train exteriors and interiors remain in the main scene.

Catenary positions are **not verified survey coordinates**. The inherited approximately 22 m procedural spacing and obstacle adjustments remain; 183 mast records are exported in [the audit CSV](validation/catenary_audit_v13.csv). The photographs support structural and relative-placement comparisons, but not a one-to-one coordinate check. M7/M8 surface positions and passage lengths are fitted to the existing simplified plaza and shifted underground frame. See the [Chinese V13 guide](README_V13.txt) and [photographic sources and limits](sources_and_licenses/site_completion_v13.json).

```sh
blender -b out/Tokyo_Station_Trains_V12.blend --python-exit-code 1 -P scripts/mod13_site_completion.py -- out/Tokyo_Station_Site_V13.blend validation/build_v13.json validation/baseline_v12.json
blender -b out/Tokyo_Station_Site_V13.blend --python-exit-code 1 -P scripts/validate13_site_completion.py -- validation/baseline_v12.json validation/validate_v13.json
blender -b out/Tokyo_Station_Site_V13.blend --python-exit-code 1 -P scripts/render_review_cams_v13.py -- out/previews 64
```

## V12 surface trains and visible interiors

V12 replaces the uniform green passenger interiors with separate Chuo, Keihin-Tohoku, Yamanote and Tokaido palettes and native furnishings. It adds individual cushions, priority seating, partitions, grab handles, luggage racks, lighting and family-specific door displays. Neutral transparent side glazing and opened cab windscreens expose the interior, with new window seals, door thresholds, buttons, wipers and gangway fittings outside.

![Four surface commuter families](images/v12/fleet.jpg)

The front shapes and paint boundaries follow real train photographs: Chuo has orange corner patches and a white centre, Keihin-Tohoku a blue centre band, and Tokaido an orange-over-green centre band. These share the E233 raked mask, round lamp optics and pale split apron. E235 has a separate upright rounded lime frame, larger black mask, square LED optics, halftone lower face and dark-grey apron. E233 waist bands continue across the doors; E235 has lime passenger-door headers and stainless driver doors. Lower sloping HVAC shells replace the old rectangular blocks.

![Same-angle cab comparison](images/v12/front_comparison.jpg)

Chuo Green cars receive a new double-deck shell, broad orange band, low end roof equipment, exposed bogies and two furnished decks. Tokaido Green cars gain upper/lower interiors. E5 receives simplified 3+2, 2+2 and 1+2 cabin layouts, and the inherited N700 formations gain 60 surface-conforming door joints. The N700 interior is retained, not rebuilt.

| | |
|---|---|
| ![Chuo interior](images/v12/chuo_interior.jpg) | ![Keihin interior](images/v12/keihin_interior.jpg) |
| Orange backs and dark cushions | Blue seating and black grab handles |
| ![Green-car cutaway](images/v12/green_cutaway.jpg) | ![Yamanote exterior](images/v12/yamanote.jpg) |
| Separate study scene exposing both decks | Clear cab glazing, wipers and lower-front halftone |

The full station remains in the main scene. Eleven separate V12 study scenes and 20 cameras provide cabin and exterior views, including a labelled front comparison. All original objects are retained; only the 86 surface instancers switch to independent V12 templates. Underground trains keep their original collections. Use Material Preview or Rendered shading to see transparent glazing.

This is a photo-informed interpretation. Seat counts, year-specific variants and special-car window distributions remain approximate, and existing wheelbases and train positions are retained. See [Chinese V12 guide](README_V12.txt) and [references and limits](sources_and_licenses/train_refinement_v12.json).

```sh
blender -b out/Tokyo_Station_Detailed_V11.blend --python-exit-code 1 -P scripts/mod12_surface_trains.py -- out/Tokyo_Station_Trains_V12.blend validation/build_v12.json validation/baseline_v11.json
blender -b out/Tokyo_Station_Trains_V12.blend --python-exit-code 1 -P scripts/validate12_surface_trains.py -- validation/baseline_v11.json validation/validate_v12.json
blender -b out/Tokyo_Station_Trains_V12.blend --python-exit-code 1 -P scripts/render_review_cams_v12.py -- out/previews 64
```

## V11 photographic detail and Marunouchi Line

V11 opens the edges beneath all ten platform decks and adds recessed supports, brackets and service trays. Platform groups now have H-section, round, paired-channel, portal-pair, box-clad and stone/stainless-clad columns. The 5/6 roof has a rounded green centre with low side wings, and the two conserved cast-iron columns are represented separately at the south end.

![Marunouchi plaza and lower ventilation towers](images/v11/plaza.jpg)

The plaza gains 6,888 stone paving faces, 15 planted tree pits with stone seat edges, drains and inspection covers. Both circular ventilation towers are lowered and given broad radial canopies, following the JR East alteration and as-built photographs. A vertically screened utility enclosure uses Google Maps street-level imagery as a visual reference. Station windows, rainwater pipes, service-building doors and 48 existing JR vehicle templates receive additional detail.

| | |
|---|---|
| ![Open platform underside](images/v11/platform_underside.jpg) | ![Paired platform columns](images/v11/platform_columns.jpg) |
| Recessed edge, supports, brackets and cable trays | Paired columns with section details and protective bands |
| ![Marunouchi platform](images/v11/metro_platform.jpg) | ![2000 series car](images/v11/metro_train.jpg) |
| B2 island platform with granite columns and half-height gates | Circular end windows, wave band, bogies and third-rail shoes |

The new M17 station follows the topology of Tokyo Metro's April 2026 diagram: B2 island, B1 concourse, three stair/escalator banks, lift, two gate areas and short JR transfer branches. A six-car scarlet 2000-series interpretation has three doors per side, round end windows, interior seating, grab loops, HVAC and third-rail collection. The model includes 36 platform-door pairs and standard-gauge tracks. The display base and studio floor have real underground voids so the complete station can be viewed in the main scene.

The `.blend` contains two additional inspection scenes: `V11 Marunouchi cutaway` omits B1, walls and ceilings to expose B2; `V11 2000 series vehicle study` shows a linked cab-car mesh separately. Fourteen review cameras are in `V11_Review_Cameras`.

This is still a photographic interpretation. Column positions, rooftop and equipment-building dimensions, underground depths and transfer passage extents are not surveyed. The former schematic Marunouchi bearing is retained, with about 7.35 m westward adjustment to clear the inherited Sobu upper structures. References span different dates; the model is not a single-date reconstruction. See [V11 sources and limitations](sources_and_licenses/detail_refinement_v11.json).

Apply V11 to the V10 file generated below:

```sh
blender --background out/Tokyo_Station_Refined.blend --python-exit-code 1 --python scripts/mod11_refinement.py -- out/Tokyo_Station_Detailed_V11.blend validation/build_v11.json validation/baseline_v10.json
blender --background out/Tokyo_Station_Detailed_V11.blend --python-exit-code 1 --python scripts/validate11_refinement.py -- validation/baseline_v10.json validation/validate_v11.json
blender --background out/Tokyo_Station_Detailed_V11.blend --python-exit-code 1 --python scripts/render_review_cams_v11.py -- out/previews 64
```

The validator compares all source mesh fingerprints and stored transforms against the pre-edit baseline, samples surface track clearances, tests column/facility intersections and roof/catenary intersections, and checks Metro vehicle envelopes, stair headroom, display-base openings and separation from the existing Sobu structure. The baseline is generated locally and is not committed. Visual review remains necessary for photographic similarity.

## V10 platform and railway-service refinement

The V10 post-processing module replaces the ten largely uniform roof skins with individually configured roof sections. It adds patched green and grey roofing, a barrel skylight, the roofing-integrated photovoltaic grid on tracks 9–10 and a local rooftop array on tracks 22–23. The latter has about 434 m² of panel surface in this model. White Shinkansen roofs have separately proportioned raised centre sections.

![Refined roofs and rooftop equipment](images/v10/roofscape.jpg)

The scene also gains eight rooftop equipment rooms, 58 flashed openings around overhead-line masts, 40 platform facility groups, 469 acoustic-screen panels and five railway service buildings. Three of the service buildings have louvred ventilation towers; the larger buildings include roof cooling banks, ducts, maintenance ladders, window bays and safety rails.

| | |
|---|---|
| ![Rooftop rooms and roof profiles](images/v10/rooftop_rooms.jpg) | ![Platform kiosk](images/v10/platform_facilities.jpg) |
| Individually sized plant rooms and folded roofs | Glazed kiosk, shelves and existing platform fittings |
| ![Acoustic screens beside the Chuo Line](images/v10/acoustic_screens.jpg) | ![Rail-side service building](images/v10/service_building.jpg) |
| Framed acoustic panels along the elevated railway | Louvred plant tower and roof cooling equipment |

These additions use the existing track alignment and platform levels. Roof profiles, patch locations, plant-room dimensions, service-building footprints and facility placement remain estimates from photographs and railway construction conventions. The references are predominantly from 2011 and 2020; this is not a survey of all 2026 alterations. The five added service buildings do not represent a reconstruction of the surrounding high-rise district. See [V10 references and limitations](sources_and_licenses/platform_context_v10.json).

The download below is the original published scene. To reproduce V10 from that scene, use Blender 5.2:

```sh
blender --background Tokyo_Station.blend --python-exit-code 1 --python scripts/mod10_platform_context.py -- out/Tokyo_Station_Refined.blend validation/build_v10.json
blender --background out/Tokyo_Station_Refined.blend --python-exit-code 1 --python scripts/validate10_platform_context.py -- validation/validate_v10.json
blender --background out/Tokyo_Station_Refined.blend --python-exit-code 1 --python scripts/render_review_cams_v10.py -- out/previews 64
```

The new meshes are grouped in `V10_Roofs`, `V10_Roof_Plant`, `V10_Platform_Details`, `V10_Acoustic_Barriers` and `V10_Service_Buildings`. Nine review cameras are in `V10_Review_Cameras`. The ten original roof objects are retained in `V10_Replaced_roofs_hidden`.

The V10 validator checks sampled vertices, triangle centres and edge midpoints against the track envelope, plus stair openings, the display-base boundary, packed assets and surface intersections with overhead-line equipment. `validate10_preservation.py` fingerprints the original meshes and stored transforms to confirm that the source objects are retained. Validation records are in `validation/`.

## Download

The current V13 Blender file is on the **[V13 release page](https://github.com/feiyaocai88-bit/tokyo-station-blender/releases/tag/v13-site-details)** as `Tokyo_Station_Site_V13.zip`. It contains the packed model, 12 rendered previews, build scripts, validation records and asset credits. The [original release](https://github.com/feiyaocai88-bit/tokyo-station-blender/releases/tag/blender-scene) remains available separately.

- Open `Tokyo_Station_Site_V13.blend` with **Blender 5.2 LTS**. Textures and fonts are packed into the file.
- The main scene contains the whole model; its default V13 camera faces the central entrance. Other viewpoints are in the camera collections.
- The underground station lies below the display base. Use the underground cameras to look at it.

## Gallery

### Station building and plaza

| | |
|---|---|
| ![Marunouchi plaza](images/marunouchi_plaza.jpg) | ![South dome](images/south_dome.jpg) |
| Marunouchi plaza and the station front | South dome: fish-scale slate, lantern and spire |
| ![South dome ceiling](images/south_dome_ceiling.jpg) | ![Dome clock](images/dome_clock.jpg) |
| Looking up into the south dome rotunda | Dome gable clock |

### Platforms and tracks

| | |
|---|---|
| ![Aerial view](images/aerial_tracks_and_platforms.jpg) | ![Platform 7-8](images/platform_7_8_steel_canopy.jpg) |
| Tracks and platforms, laid out from GSI track centre lines | Platform 7-8: steel canopy with skylight |
| ![Platform 9-10](images/platform_9_10_raised_shinkansen_side.jpg) | ![Platform 20-21](images/platform_20_21_looking_down.jpg) |
| From platform 9-10: the Shinkansen side is 1.90 m higher | Looking down from Shinkansen platform 20-21 |

### Trains

| | |
|---|---|
| ![E233](images/e233_from_platform.jpg) | ![E233 interior](images/e233_interior_aisle.jpg) |
| E233-3000 (Ueno-Tokyo Line) seen through its windows | E233 interior |
| ![E235](images/e235_yamanote_cab_car.jpg) | ![N700](images/n700_head_lamps.jpg) |
| E235 Yamanote Line cab car | N700 head lamps |
| ![E5](images/e5_side_led.jpg) | |
| E5 *Hayabusa* side destination display | |

### Sobu / Yokosuka Line underground station

The station lies 28 m below the Marunouchi plaza. It has five levels:

- B5: two island platforms with tracks 1–4;
- B4: the concourse;
- B3 and B2: plant floors;
- B1: the ticket gates.

| | |
|---|---|
| ![B5 platform 1-2](images/sobu_b5_platform_1_2.jpg) | ![B5 platform 3-4](images/sobu_b5_platform_3_4.jpg) |
| B5 platform 1-2, Yokosuka Line train for Kurihama | B5 platform 3-4, Sobu Rapid train for Chiba |
| ![Across tracks 2 and 3](images/sobu_b5_track_soffit_and_conductor.jpg) | ![Train front](images/sobu_b5_train_front.jpg) |
| Over-track soffit, beams and rigid overhead conductor | E235-1000-style train at the Shimbashi end |
| ![Stairs to B4](images/sobu_b5_stairs_to_b4.jpg) | ![Track 2](images/sobu_b5_track_2.jpg) |
| Stair and escalator up to the B4 concourse | Looking along the empty track 2 |
| ![B4 concourse](images/sobu_b4_concourse.jpg) | ![Long escalators](images/sobu_b4_to_b1_escalators.jpg) |
| B4 concourse | Long escalators from B4 to B1 (12.7 m rise) |
| ![B1 ticket gates](images/sobu_b1_ticket_gates.jpg) | ![Cutaway](images/sobu_cutaway.jpg) |
| B1 ticket gates | Cutaway through all five levels |

## What is modelled

- **Station building:**
  - the Marunouchi building, north and south domes with lanterns and spires;
  - dome rotunda interiors with ceiling reliefs, gable clocks and entrance canopies.
- **Plaza:** paving, lawns, trees, roads, bus islands, the two ventilation towers, pedestrians.
- **Tracks and platforms:**
  - Track centre lines come from GSI vector tiles.
  - Conventional tracks 1–10: the Chuo Line is elevated on tracks 1–2.
  - Shinkansen tracks 14–23 are 1.90 m higher than the conventional tracks.
  - On the platforms: steel canopies (conventional), large roofs (Shinkansen), stairs and escalators, signage, departure boards, clocks, tactile paving and door-position markers.
- **Railway equipment:** overhead lines laid per track, departure signals, stop boards, buffer stops.
- **Trains:**
  - E233-0, E233-1000, E233-3000 and E235-0, with interiors in the commuter cars;
  - E5 and N700 Shinkansen;
  - in the underground station, two 15-car E235-1000-style trains.
- **Underground station:**
  - the cut-and-cover box, 12 stair/escalator groups, 2 lifts and 2 long escalator banks;
  - the B4 and B1 concourses and the ventilation shaft up to the existing tower;
  - the Marunouchi Line B1 concourse and B2 platform, six-car 2000-series train, and M7/M8 ground connections.

## Automatic checks

The validators in `scripts/` run on the finished file. Their reports are in `validation/`. They check the following:

- **Vehicle envelope:** nothing apart from the track and conductor intrudes within 1.55 m of any track centre, from rail level up to the raised pantograph.
- **Fixed structures:** they are at least 1.9 m from the track centres.
- **Trains:** they sit on the rails, and the pantograph shoes touch the contact wire.
- **Headroom:** at least 2.10 m over every stair and escalator; the measured minimum is 2.35 m.
- **People:** each person stands on a floor.
- **Plinth:** everything above the studio floor stays inside the display plinth.
- **Other checks:** overhead lines, platforms, canopies, train markings and track levels.

## Accuracy and limitations

- **Underground station position:**
  - Direction, length and position along the platforms come from OpenStreetMap.
  - The axis was moved 25 m west, because sources say no building stands above the station and the existing ventilation tower has to sit over it.
  - Expected error: about ±10 m across and ±5 m along the platforms.
  - Rail depth is 28 m (published figure). The B4 floor height is derived from the required pantograph clearance, not from a source.
- **Interiors:** ceilings, wall finishes, signs and the times on the departure boards follow typical JR underground stations. They are not reproductions of the real Tokyo Station interiors.
- **Underground trains:** they are the model's E235-0 re-liveried, not a separate E235-1000 model. The Green cars use the E233-3000 double-deck shell.
- **Not modelled:**
  - the curves beyond the ends of the underground station;
  - the JR Keiyo Line underground station;
  - complete commercial underground passages and the building-integrated M9/M10 exits.
- **Vehicle interiors:** V12 includes simplified cabs, commuter interiors and two-deck Green-car seating. Seat counts and small controls are interpretive.
- **Overhead conductor:** the rigid conductor in the underground station is an assumption.

## Repository contents

| Path | Contents |
|---|---|
| `images/` | Renders used in this README |
| `scripts/` | Blender Python build scripts, validators and texture generators, with the fonts, textures and two CC BY assets they use |
| `sources_and_licenses/` | Data sources, references and asset licences |
| `validation/` | JSON reports of the automatic checks |

## Credits and licences

Third-party assets used in the scene keep their own licences:

| Asset | Author | Licence |
|---|---|---|
| [Escalator KONE TravelMaster 110](https://sketchfab.com/3d-models/escalator-kone-travelmaster-110-d1e9d7e1b80d42dc9872d5ba6d8e2307) | Sergey Burov (@s-burov) | CC BY 4.0 |
| [Subway \[interior\]](https://sketchfab.com/3d-models/subway-interior-b7f25426ac674a9291ba092fb9fe8406) | Comicaroid (@yuuuusukeeee) | CC BY 4.0 |
| [N700-3000 Series Shinkansen](https://sketchfab.com/3d-models/n700-3000-series-shinkansen-f70820be44e0467d8b1614f2aa3045bd) | Layo / bciarfello | CC BY 4.0 |
| Noto Sans JP | Google | SIL Open Font License 1.1 |
| TeX Gyre Termes | GUST | GUST Font License |

The models were changed to fit the scene; the changes are listed in `sources_and_licenses/`. [Shinkansen E5 V.2.0](https://sketchfab.com/3d-models/shinkansen-e5-v20-5cb621afd38c4f6e851ea8ea1ee09caf) by hilalhikmahvv (CC BY 4.0) was used as a shape reference. The E5 in the scene is modelled from scratch.

Data sources:

- Track centre lines and aerial imagery: [GSI tiles](https://maps.gsi.go.jp/development/ichiran.html) (国土地理院).
- Underground platform positions: [OpenStreetMap](https://www.openstreetmap.org/copyright) (© OpenStreetMap contributors, ODbL). Only a few converted coordinates are used.
- Facts: Japanese Wikipedia and other references, listed in `sources_and_licenses/`. Reference photos were used for comparison only and are not included.
