# Tokyo Station – Blender model

![Overview of the model](images/hero_overview.jpg)

A diorama-style 3D model of Tokyo Station, made in Blender 5.2. It covers:

- the red-brick Marunouchi station building with both domes;
- the Marunouchi plaza;
- all conventional and Shinkansen platforms, with tracks, overhead lines and trains;
- the JR Sobu Rapid / Yokosuka Line underground station, five levels below the plaza.

The model is built with Blender Python scripts. Automatic checks test clearances, headroom and train placement.

> This is an interpretive model, not survey data. Track and platform positions are matched to GSI (Geospatial Information Authority of Japan) data and OpenStreetMap. Heights, interiors and many details are estimates. See [Accuracy and limitations](#accuracy-and-limitations).

## Download

The Blender file is on the **[release page](https://github.com/feiyaocai88-bit/tokyo-station-blender/releases/tag/blender-scene)** as `Tokyo_Station_Blender.zip` (96 MB).

- Open `Tokyo_Station.blend` with **Blender 5.2 LTS**. Textures and fonts are packed into the file.
- The default camera shows the whole model. Other viewpoints are in the camera collections.
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
  - a simplified Marunouchi Line tunnel crossing above.

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
  - the Marunouchi Line station;
  - the JR Keiyo Line underground station;
  - driver's cabs and Green car interiors.
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
