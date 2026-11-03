# Tokyo Station – Blender model

![Continuous Chuo canopy and connected equipment](images/v22/overview.jpg)

A diorama-style 3D model of Tokyo Station, made in Blender 5.2. It covers:

- the red-brick Marunouchi station building with both domes;
- the Marunouchi plaza;
- all conventional and Shinkansen platforms, with tracks, overhead lines and trains;
- the JR Sobu Rapid / Yokosuka Line underground station, five levels below the plaza.
- the Tokyo Metro Marunouchi Line M17 station and a six-car 2000-series train in V11.

The model is built with Blender Python scripts. Automatic checks test clearances, headroom and train placement.

> This is an interpretive model, not survey data. Track and platform positions are matched to GSI (Geospatial Information Authority of Japan) data and OpenStreetMap. Heights, interiors and many details are estimates. See [Accuracy and limitations](#accuracy-and-limitations).

## V22 continuous Chuo roof and connections to the lower canopy

V22 corrects the Chuo 1/2 roof silhouette using the user's new oblique aerial photograph. A broad, shallow mint-green roof meets continuous dark curved side panels. Twenty-five complete metal frames follow the enclosure across its crown. A raised white transverse cover sits approximately beside the central station pavilion; its function is unverified. The former generic Chuo rooftop house is retained as a hidden original.

![Matched before and after roof views](images/v22/comparison.jpg)

The user also confirmed the equipment connecting the elevated Chuo structure to the lower 3/4 canopy. Eight assemblies now have access panels, louvres, handles, continuous rectangular risers, collars, service conduit, upper portal brackets and support rails ending on bearings fitted to the actual sloped roof. These quantities and positions are visual model choices, not a surveyed equipment schedule.

![Equipment and supports connecting the two levels](images/v22/equipment.jpg)

The existing columns, slatted soffit, lights, CCTV, staff room, covered end passage and platform fittings remain. Original mast, contact-wire, messenger, dropper, insulator and lower steady-arm geometry stays unchanged. The Chuo portion of the exposed transverse trusses becomes curved internal support beams; only the hanger upper ends and mounting plates change to meet those beams without crossing the new shell.

Fifteen checks cover preservation of the 37,767 V21 source objects, hidden originals, unchanged electrical geometry, train clearance, actual shell/OCS intersections, continuous roof joints, mast apertures, all 44 hanger mounting points, existing stairs and passages, the white cover's bearings, all eight interlevel connections, and file resources. The source photograph has no supplied date, author or measured dimensions. Its silhouette guides the model; precise heights, spacing, material properties and white-cover placement remain estimates. The source image is not redistributed or used as a texture.

See the [Chinese guide](README_V22.txt), [reference record](sources_and_licenses/chuo_roof_v22.json), [build record](validation/build_v22.json), [validation report](validation/validate_v22.json), and [V22 model download](https://github.com/feiyaocai88-bit/tokyo-station-blender/releases/tag/v22-chuo-roof).

```sh
blender -b out/Tokyo_Station_Platforms_V21.blend --python-exit-code 1 -P scripts/mod22_chuo_roof.py -- out/Tokyo_Station_Chuo_Roof_V22.blend validation/build_v22.json validation/baseline_v21.json
blender -b out/Tokyo_Station_Chuo_Roof_V22.blend --python-exit-code 1 -P scripts/validate22_chuo_roof.py -- validation/baseline_v21.json validation/validate_v22.json
blender -b out/Tokyo_Station_Chuo_Roof_V22.blend --python-exit-code 1 -P scripts/render_review_cams_v22.py -- out/previews 24 01,02,03,04,05,06,07 1800 1200
```

## V21 individual platform structures and fittings

V21 updates all **13 existing island platforms**: ten on the surface, two Sobu/Yokosuka islands at B5, and the Marunouchi Line M17 island. Google Street View observations are cross-checked with original-author photographs. Each platform retains its own footprint and receives the appropriate canopy structure, columns, suspended fittings and floor detail.

![Platform-by-platform model views](images/v21/contact.jpg)

| Platforms | Main changes |
|---|---|
| 1/2 | Silver column covers and attached equipment; V20 curved acoustic ribs, staff room and end passage retained |
| 3/4 | Exposed haunched steel frames and H columns replacing the uniform round-column treatment |
| 5/6 | Curved central daylight strip, lower side wings and exposed purlins |
| 7/8 | Shallow pitched metal canopy, paired supports, open cable ladders and individual light fittings |
| 9/10 | Light-transmitting photovoltaic roof, riveted transverse frames and dense cable trays |
| 14/15, 16/17, 18/19 | Individual pitched roof profiles, steel columns, corrected roof heights, service-room supports and glazed waiting rooms |
| 20/21, 22/23 | Open central roof structure, segmented side soffits, dark stone/stainless column finishes and glazed waiting rooms; local PV on 22/23 |
| Sobu/Yokosuka B5 1/2 and 3/4 | Column maps, emergency call boxes, ceiling cameras, ceiling joints and coloured floor inlays |
| Marunouchi M17 | Visible slatted ceiling joints, column fittings, dome cameras and lamps mounted on the existing platform-door posts |

![Differentiated roof profiles](images/v21/roofs.jpg)

Five new waiting rooms include open sliding doorways, seating, lights and air diffusers. Their side passages retain real deck support and headroom. The inherited 7/8 layout did not provide a clear bay for an additional room, so its stairs and circulation remain unobstructed. Underground side walls stay open for inspection.

Eleven geometry checks cover source preservation, all 13 platform groups, 30 stair apertures, waiting-room passages, train/electrical corridors, mast penetrations, rooftop equipment against actual overhead-line meshes, Metro lamp attachments, underground cutaways and file dependencies. All 36,931 V20 source objects are unchanged or retained as hidden originals.

Street views date mainly to 2016–2018; platform photographs are from 2019. Direct Google panorama coverage is recorded separately from across-track views and photographic references. This is a multi-epoch visual model with estimated dimensions, fitting quantities and equipment positions; it is not a surveyed reconstruction. Existing newer trains and platform doors are retained. Source imagery is linked for provenance, not redistributed or used as textures. The model's previous pole positions remain in place; new roof openings are checked against those positions, rather than presented as verified real-world coordinates.

See the [Chinese guide](README_V21.txt), [platform-by-platform sources](sources_and_licenses/platforms_v21.json), [build record](validation/build_v21.json), [validation report](validation/validate_v21.json), and [V21 model download](https://github.com/feiyaocai88-bit/tokyo-station-blender/releases/tag/v21-platforms-streetview).

```sh
blender -b out/Tokyo_Station_Chuo_V20.blend --python-exit-code 1 -P scripts/mod21_platforms.py -- out/Tokyo_Station_Platforms_V21.blend validation/build_v21.json validation/baseline_v20.json
blender -b out/Tokyo_Station_Platforms_V21.blend --python-exit-code 1 -P scripts/validate21_platforms.py -- validation/baseline_v20.json validation/validate_v21.json
blender -b out/Tokyo_Station_Platforms_V21.blend --python-exit-code 1 -P scripts/render_review_cams_v21.py -- out/previews 24 01,02,03,04,05,06,07,08,09,10,11,12,13,14,15 1800 1200
```

## V20 Chuo platform details from supplied street views

V20 adds the narrow arched passage at the raised Chuo platform end, 34 curved ribs connecting the outer acoustic screens to the canopy, and a rounded silver staff-room enclosure. The room has panel joints, ribbon windows, a glazed personnel door, hardware and ventilation grilles. Twelve separate CCTV cameras and six hooded departure monitors include mounting rods, lens barrels, brackets and cables. Ribbed ceiling finishes, continuous lights and paving joints complete the platform views.

![Chuo platform end and curved ribs](images/v20/overview.jpg)

| | |
|---|---|
| ![Arched end passage](images/v20/end.jpg) | ![Rounded staff room](images/v20/room.jpg) |
| ![Acoustic-screen to canopy rib](images/v20/arches.jpg) | ![Departure monitors](images/v20/monitors.jpg) |
| ![CCTV lens and bracket](images/v20/cctv.jpg) | ![Complete Chuo platform](images/v20/whole.jpg) |
| ![Before and after](images/v20/comparison.jpg) | ![Room comparison](images/v20/room_comparison.jpg) |

The source is the user's three Google Street View screenshots dated December 2016. Visible forms are recreated with native geometry; the screenshots are not textures and are not redistributed. Dimensions, equipment positions and quantities are estimates fitted to the inherited scene. The curved-rib crest is adapted to clear the model's existing messenger wires, and the precise purpose of the small end passage is unverified.

Eight checks pass: all V19 originals remain preserved; replacement originals are hidden; both room-side walkways have deck support and headroom; all three stairs remain open; the covered passage has a continuous floor; new structures clear the model's rail/electrical corridors; screens stay within the corrected viaduct ends; and image dependencies resolve. Local sign assemblies and five passenger instances are repositioned to clear the new room. Replaced originals remain in `V20_Replaced_hidden`.

See the [Chinese guide](README_V20.txt), [reference record](sources_and_licenses/chuo_details_v20.json), and [validation report](validation/validate_v20.json).

```sh
blender -b out/Tokyo_Station_Connections_V19.blend --python-exit-code 1 -P scripts/mod20_chuo_details.py -- out/Tokyo_Station_Chuo_V20.blend validation/build_v20.json validation/baseline_v19.json
blender -b out/Tokyo_Station_Chuo_V20.blend --python-exit-code 1 -P scripts/validate20_chuo.py -- validation/baseline_v19.json validation/validate_v20.json
blender -b out/Tokyo_Station_Chuo_V20.blend --python-exit-code 1 -P scripts/render_review_cams_v20.py -- out/previews 24 01,02,03,04,05,06,07 1800 1200
```

## V19 rear concourse and connected streets

V19 fills the visible gaps between the Marunouchi building and the Chuo viaduct with continuous skylight glazing, seamed roof panels, columns, rainwater fittings, a paved passage, lighting and service equipment. The canopy follows the back wall and ends where the inherited angled south wing constricts the available space. The two end service yards receive paving, drains and fixtures.

![V19 connected streets](images/v19/overview.jpg)

The perimeter street is rebuilt as one connected asphalt surface. Curves and transport-square interfaces share a consistent grade. Obsolete asphalt aprons become connected footways, and road markings, crossings, signals, lights and gullies give the network a continuous appearance. The northern road avoids the service building, while the southern road skirts the existing model undercroft. Existing Metro stair openings remain clear.

| | |
|---|---|
| ![North intersection](images/v19/north.jpg) | ![South street connection](images/v19/south.jpg) |
| ![Rear concourse](images/v19/rear.jpg) | ![Rear details](images/v19/detail.jpg) |
| ![Covered passage](images/v19/passage.jpg) | ![Street plan](images/v19/plan.jpg) |
| ![Street comparison](images/v19/comparison.jpg) | ![Rear comparison](images/v19/rear_comparison.jpg) |

References include the [JR East Design authors' restoration article, printed page 7 and photograph 3-5](https://www.jtccm.or.jp/sites/default/files/books_pdf/2013/Vol49,No2,2013.pdf) and [JSCE's completed-project aerial](https://design-prize.sakura.ne.jp/archives/result/1406). Positions, equipment details, markings and road widths are interpreted within the inherited model, not surveyed; the southern routing is a model adaptation and does not claim an exact real street alignment. Source photographs are not redistributed.

See the [Chinese guide](README_V19.txt), [source record](sources_and_licenses/connections_v19.json) and [validation report](validation/validate_v19.json). Replaced originals remain in `V19_Replaced_hidden`.

```sh
blender -b out/Tokyo_Station_Plaza_V18.blend --python-exit-code 1 -P scripts/mod19_connections.py -- out/Tokyo_Station_Connections_V19.blend validation/build_v19.json validation/baseline_v18.json
blender -b out/Tokyo_Station_Connections_V19.blend --python-exit-code 1 -P scripts/validate19_connections.py -- validation/baseline_v18.json validation/validate_v19.json
blender -b out/Tokyo_Station_Connections_V19.blend --python-exit-code 1 -P scripts/render_review_cams_v19.py -- out/previews 24 01,02,03,04,05,06,07 1800 1200
```

## V18 Marunouchi plaza compared with completed-project photographs

V18 aligns the white central promenade with the station entrance, replaces the offset lawns with two equal 600 m² lawns, and rebuilds the paired seven-tree rows, broad granite tree seats, slender rope fences and vertical three-lantern lighting. Varied granite paving, flush drains and dry seasonal cooling surfaces complete the central square.

![V18 plaza overview](images/v18/overview.jpg)

The north and south traffic squares now have different island outlines, open taxi holding areas, detailed waiting vehicles, slim cantilevered glass shelters, stop signs and pedestrian rails. Real kerb gaps and graded approaches connect the taxi pools to the traffic loops, which join the perimeter streets. Pedestrians are moved out of lawns and seats, and the existing M7/M8 stair openings remain clear.

| | |
|---|---|
| ![Central plaza axis](images/v18/central.jpg) | ![Granite tree seats and lawn ropes](images/v18/detail.jpg) |
| Paired lawns and white central promenade | Vertical lanterns, planted seats and rope fences |
| ![North transport square](images/v18/north.jpg) | ![South transport square](images/v18/south.jpg) |
| Open taxi pool and northern ventilation island | Asymmetric southern traffic island |
| ![Plaza plan](images/v18/plan.jpg) | ![V17 and V18 comparison](images/v18/comparison.jpg) |
| Both traffic loops connect to perimeter streets | Matching camera before and after |

The comparison uses [JR East's 2017 opening information](https://www.jreast.co.jp/press/2017/20171107.pdf), [JSCE's completed-project aerial and furniture photographs](https://design-prize.sakura.ne.jp/archives/result/1406), [Katabami's planting photographs](https://www.katabami.co.jp/business/works/detail.php?category=3&id=82) and [Teikin's installed furniture photographs](https://www.teikin.co.jp/case/detail/000036.html). Source photos are not redistributed. The geometry follows photographic relationships fitted to the existing model, rather than surveyed coordinates; specific road widths, bay counts and furniture dimensions remain approximations. The inherited M7/M8 locations are unchanged.

All replaced source objects remain in `V18_Replaced_hidden`. See the [Chinese guide](README_V18.txt), [reference record](sources_and_licenses/plaza_v18.json) and [geometry and preservation checks](validation/validate_v18.json).

```sh
blender -b out/Tokyo_Station_Connected_V17.blend --python-exit-code 1 -P scripts/mod18_plaza.py -- out/Tokyo_Station_Plaza_V18.blend validation/build_v18.json validation/baseline_v17.json
blender -b out/Tokyo_Station_Plaza_V18.blend --python-exit-code 1 -P scripts/validate18_plaza.py -- validation/baseline_v17.json validation/validate_v18.json
blender -b out/Tokyo_Station_Plaza_V18.blend --python-exit-code 1 -P scripts/render_review_cams_v18.py -- out/previews 24 01,02,03,04,05,06 1800 1200
```

## V17 continuous Marunouchi building connections

V17 corrects the visible separation between the station's building sections. Four new masonry necks connect the north/south domes to their adjacent wings, including stone courses and storey slabs. The slab edges follow the octagonal dome perimeter and keep the rotunda interiors clear.

![Continuous station building](images/v17/overview.jpg)

Thirteen roof transitions remove the deep V-shaped notches caused by independently hipped roof ends. The old roof solids and new transitions are joined into four connected roof meshes, including the angled south wing. Metal ridge caps continue across the joints. Both central flat-roof attic turrets gain side/back enclosure, and the round dome corner ornaments engage with the new connecting facades.

| | |
|---|---|
| ![North wing roof connections](images/v17/north.jpg) | ![Dome-to-wing connections](images/v17/dome.jpg) |
| Continuous roof across the projecting gable | Brick walls, stone courses and roof necks |
| ![South angled wing](images/v17/south.jpg) | ![Same-camera comparison](images/v17/comparison.jpg) |
| Connected roof through the existing bend | V16 before and V17 after |

All replaced V16 source geometry remains in `V17_Replaced_hidden`; unrelated objects retain their materials, transforms, visibility and collection links. Validation checks roof connectivity and manifold topology, actual surface continuity, connecting walls/slabs, attic enclosure and asset availability. See the [Chinese V17 guide](README_V17.txt) and [validation results](validation/validate_v17.json). Connections follow the inherited model dimensions and the continuity visible in the official photographs; they are not surveyed junctions.

```sh
blender -b out/Tokyo_Station_Architecture_V16.blend --python-exit-code 1 -P scripts/mod17_building_connections.py -- out/Tokyo_Station_Connected_V17.blend validation/build_v17.json validation/baseline_v16.json
blender -b out/Tokyo_Station_Connected_V17.blend --python-exit-code 1 -P scripts/validate17_building_connections.py -- validation/baseline_v16.json validation/validate_v17.json
blender -b out/Tokyo_Station_Connected_V17.blend --python-exit-code 1 -P scripts/render_review_cams_v17.py -- out/previews 24 02,03,04,05 1440 900
blender -b out/Tokyo_Station_Connected_V17.blend --python-exit-code 1 -P scripts/render_review_cams_v17.py -- out/previews 24 01 2000 650
```

## V16 Marunouchi architecture compared with restoration photographs

The complete station now includes revised Marunouchi architecture based on the official Kajima restoration album and Tokyo Station City facade details. The central niche has deeper connected returns and a shallow inner arch, with a thick layered copper pediment above it. Flat attic-turret cornices replace the hip roofs, and two round attic dormers replace rectangular windows.

![Central station building from pedestrian level](images/v16/central.jpg)

Both dome clock gables gain projecting metal archivolts and stone voussoirs. Their octagonal window drums receive brick piers and copper trim; sixteen roof dormers gain scrolls and crowns. Four tall round stone corner ornaments, fine iron balcony rails, carved pilaster capitals, frieze medallions and painted sashes improve the facade at closer distances.

| | |
|---|---|
| ![South dome facade](images/v16/south.jpg) | ![Dome roof details](images/v16/roof.jpg) |
| Layered clock hood, stone corner ornaments and balcony | Copper profiles and round-dormer ornament |
| ![Wing facade details](images/v16/facade.jpg) | ![Central before and after](images/v16/comparison.jpg) |
| Carved capitals, window heads and painted sashes | V15 and V16 rendered with the same camera |

All replaced source objects are retained in `V16_Replaced_hidden`. Validation checks mesh, curve, text and transform preservation; unchanged unrelated objects; actual central openings; consistent window setback; visible clock faces; flat turret caps; and packed images. Eight review cameras are included. Existing trains, platforms, ground details and open underground stations are preserved.

This is a photographic interpretation fitted to the inherited plan and floor heights. Fine carving and dimensions remain approximate. The documented 46.1 m dome-plus-finial height is retained. Reference photographs are not redistributed. See the [Chinese V16 guide](README_V16.txt), [reference evidence and limits](sources_and_licenses/marunouchi_architecture_v16.json), and [validation results](validation/validate_v16.json).

```sh
blender -b out/Tokyo_Station_Cutaway_V15.blend --python-exit-code 1 -P scripts/mod16_marunouchi_architecture.py -- out/Tokyo_Station_Architecture_V16.blend validation/build_v16.json validation/baseline_v15.json
blender -b out/Tokyo_Station_Architecture_V16.blend --python-exit-code 1 -P scripts/validate16_marunouchi_architecture.py -- validation/baseline_v15.json validation/validate_v16.json
blender -b out/Tokyo_Station_Architecture_V16.blend --python-exit-code 1 -P scripts/render_review_cams_v16.py -- out/previews 48 01,02,03,06,07 1440 1100
```

## Surface catenary position audit of V15 (retained in V16)

The central and north platform-area masts are **still inherited procedural positions, not individually photo-calibrated coordinates**. A read-only audit now records all 175 independent surface mast shafts: 162 inherited positions and the 13 south masts from V14. The latter retain their distinctions between ten masts on photo-estimated chainages, two adapted to the cropped model end and one required by model curvature. No mast is promoted to a surveyed coordinate and no `.blend` geometry changes in this audit.

Six model checks pass for shaft clearances, selected platform/roof/rooftop-room intersections and footing/side-bracket connections. These checks establish model relationships, not agreement with every real-world mast. See the [Chinese findings and photographic limits](SURFACE_CATENARY_CHECK.md), [numbered model plan](images/catenary_audit/plan.png), [175-mast CSV](validation/surface_catenary_masts.csv) and [machine-readable audit](validation/surface_catenary_audit.json). V16 preserves this geometry and its accuracy limits.

## V15 open-side underground stations

Both underground stations now have their side enclosures removed from the active geometry in the **complete main scene**, so their interiors are visible in Solid viewport mode as well as in renders. JR Sobu/Yokosuka B5–B1 perimeter walls, track-wall finishes, equipment-room partitions and tunnel side/end walls are opened. Marunouchi M17 track walls, B1 side walls and transfer branches are opened, along with the M7/M8 stairwell and connecting-passage walls. Wall-only posters, lights and tile grout are removed with their walls.

![Complete model with exposed underground levels](images/v15/main.jpg)

| | |
|---|---|
| ![JR underground opposite side](images/v15/jr.jpg) | ![Marunouchi station open sides](images/v15/metro.jpg) |
| Five JR levels, with trains and equipment retained | M17 platform, columns, train and B1 concourse |
| ![M8 exposed staircase](images/v15/access.jpg) | ![Matching before and after](images/v15/comparison.jpg) |
| Stair flights and continuous B1 passage | Identical camera on V14 and V15 |

Floor and roof slabs, their existing openings, platforms, tracks, trains, columns, stairs, escalators, gates, overhead signs and equipment remain. The surface model includes all V14 work. Two linked inspection scenes and five cameras are included. The original meshes are preserved in `V15_Replaced_hidden`; a restoration script saves a separate copy with the original walls. See the [Chinese V15 guide](README_V15.txt) and [validation results](validation/validate_v15.json). This is an exhibition cutaway; the existing model's accuracy limits still apply.

```sh
blender -b out/Tokyo_Station_Ground_V14.blend --python-exit-code 1 -P scripts/mod15_underground_cutaway.py -- out/Tokyo_Station_Cutaway_V15.blend validation/build_v15.json validation/baseline_v14.json
blender -b out/Tokyo_Station_Cutaway_V15.blend --python-exit-code 1 -P scripts/validate15_underground_cutaway.py -- validation/baseline_v14.json validation/validate_v15.json
blender -b out/Tokyo_Station_Cutaway_V15.blend --python-exit-code 1 -P scripts/render_review_cams_v15.py -- out/previews 64 01,02,03,05 1600 760
blender -b out/Tokyo_Station_Cutaway_V15.blend --python-exit-code 1 -P scripts/render_review_cams_v15.py -- out/previews 64 04 1600 1000
blender -b out/Tokyo_Station_Cutaway_V15.blend --python-exit-code 1 -P scripts/restore15_underground_walls.py -- out/Tokyo_Station_Walls_Restored.blend
```

## V14 south ground details and south catenary positions

V14 fills the bare ground below the south approach with a brick-arch frontage, recessed Hato Bus ticket windows, shutters, service doors, louvres, downpipes and lamps. The longitudinal street gains raised paving, joints, kerbs, drainage grates, inspection covers, stop flags, utility cabinets and a parked yellow sightseeing coach. Two old schematic transverse sidewalk strips are replaced, and the undercroft receives floors, ceilings, partitions and pier fittings.

![South ground overview](images/v14/ground.jpg)

| | |
|---|---|
| ![Brick arches and office](images/v14/frontage.jpg) | ![Paving and drainage](images/v14/paving.jpg) |
| Photograph-informed undercroft frontage | Curbs, gullies, covers and stopping bay |
| ![South overhead lines](images/v14/catenary.jpg) | ![Before and after](images/v14/comparison.jpg) |
| Independent staggered portals and connected wires | Same-camera comparison of the ground area |

South conventional-track OCS is actually changed in this version: **21 old masts are replaced by 13**, and eight tracks receive continuous new contact wires, messengers, droppers and fittings. Five portal chainages are interpreted from GSI imagery with an estimated +/-3 m tolerance. A sixth row is moved 3 m inward to fit the cropped bridge end; an extra twin-arm support on tracks 7/8 is required by the inherited curve and is explicitly unverified. Lateral mast locations are fitted to the existing rails. Chuo, central/north conventional and Shinkansen supports remain inherited; this is **not a full-station survey match**. See [pole changes](validation/catenary_changes_v14.csv), [Chinese V14 guide](README_V14.txt) and [reference evidence and limitations](sources_and_licenses/south_ground_v14.json).

Thirteen geometric checks cover source preservation, removal of old active mast shafts and tie rods, vehicle clearance, actual wire continuity and suspension attachment, mast bases, walking surfaces/headroom, coach ground contact and asset packing. V12 rolling stock and V13 Metro access remain active. The frontage follows official Hato Bus photographs; bay dimensions, internal service layout, furniture and coach details remain interpretive. Reference photographs are not redistributed.

```sh
blender -b out/Tokyo_Station_Site_V13.blend --python-exit-code 1 -P scripts/mod14_south_ground.py -- out/Tokyo_Station_Ground_V14.blend validation/build_v14.json validation/baseline_v13.json
blender -b out/Tokyo_Station_Ground_V14.blend --python-exit-code 1 -P scripts/validate14_south_ground.py -- validation/baseline_v13.json validation/validate_v14.json
blender -b out/Tokyo_Station_Ground_V14.blend --python-exit-code 1 -P scripts/render_review_cams_v14.py -- out/previews 64
```

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

Catenary positions in V13 are **not verified survey coordinates**. V13 retained the nominal 44 m procedural grid, often subdivided to 22 m and adjusted for obstacles; 183 mast records are exported in [the V13 audit CSV](validation/catenary_audit_v13.csv). V14 updates the south subset as described above. M7/M8 surface positions and passage lengths are fitted to the existing simplified plaza and shifted underground frame. See the [Chinese V13 guide](README_V13.txt) and [photographic sources and limits](sources_and_licenses/site_completion_v13.json).

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

The current V20 Blender file is on the **[V20 release page](https://github.com/feiyaocai88-bit/tokyo-station-blender/releases/tag/v20-chuo-platform-details)** as `Tokyo_Station_Chuo_V20.zip`. It contains the complete packed model, seven views, matching comparisons, scripts, validation records and asset credits. The [V19 streets and rear-concourse release](https://github.com/feiyaocai88-bit/tokyo-station-blender/releases/tag/v19-rear-concourse-streets) and earlier releases remain available.

- Open `Tokyo_Station_Chuo_V20.blend` with **Blender 5.2 LTS**. Textures and fonts are packed.
- The default V20 camera shows the raised Chuo platform end. Seven V20 cameras include the end passage, room, curved ribs, monitors and CCTV lens. Earlier camera collections remain available.
- Underground cameras remain available below the display base.


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
