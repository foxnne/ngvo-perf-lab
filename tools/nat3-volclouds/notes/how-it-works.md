# Per-weather volumetric clouds in this fork: how it works

Written 2026-11-17 from source only. Fork: `C:\Users\foxnn\dev\skyrim-community-shaders`, branch `foxnne/nr-pr6`
(HEAD 5451c7e). Nothing was built, launched or measured. Every value in the draft is an untested guess.
Paths below are relative to the fork root unless they start with a drive letter.

Sections: 1 what applies cloud settings per weather, 2 file schema, 3 what can and cannot be set per weather,
4 parameters (look and cost), 5 why noon went dark grey, 6 why distant fog and grass shimmered,
7 what the Azure Hearth reference does, 8 the draft and how it would be installed, 9 what I could not determine.

## 1. The mechanism

Two layers are involved, and they use two different JSON shapes.

**Baseline pack file** (`Presets/<Pack>/Baseline/PhysicalSky.json`): plain feature settings that replace the
defaults. It is the same tree `PhysicalSky::SaveSettings` writes (`src/Features/PhysicalSky.cpp:153-207`, `:512-515`).
Global-only things live here: the volumetric and vanilla cloud switches, march quality, noise.

**Scene Manager weather files** (`Presets/<Pack>/Weather/<formkey>/[<Period>/]<Pack>_<Feature>.json`): one folder per
weather form, loaded by `SceneSettingsManager::DiscoverWeatherOverwrites`
(`src/CSEditor/SceneManager/SceneSettingsDiscovery.cpp:656-706`). Each numeric leaf in the file becomes one scene
entry for that weather, and the Scene Manager blends the entries of the outgoing and incoming weather along the
game's own weather transition. This is the only thing that applies cloud settings per weather.

There is no weather table inside the cloud settings themselves. The `weather.states` arrays inside
`cloudLayer.cirrus.weather` and `cloudLayer.middle.weather` are not a list of weathers: they are a `SceneBlend`
(`src/Utils/SceneBlend.h`), a weighted set of endpoint states that the Scene Manager produces while it is blending
two scenes. A weather file supplies one state with weight 1; during a transition the manager accumulates the two
endpoints with their weights, and the generator renders each state's map scaled by its weight
(`src/Features/PhysicalSky/Ndf.cpp:832-866`, `features/Physical Sky/Shaders/PhysicalSky/CirrusGenerate.cs.hlsl:63-82`).

`Forms/<Category>/<formkey>.json` in a pack is something else again: CS Editor edits of game records (weather,
lighting, ImageSpace). It carries no Physical Sky settings.

Layer order, lowest to highest (from `C:\Modlists\NGVO 8.0 Beta\look\cs-scene-presets-guide.txt`, section 1):
feature defaults, Baseline packs, your own edits in `SettingsUser.json`, then Scene Manager
(Interior, Time of Day, Weather, Location). Inside a scene layer the active pack supplies a value and your own
override in `SceneSettings/SceneManager.json` goes on top.

### Rules that shaped the draft

| Rule | Source |
|---|---|
| A weather scene takes blendable values only: floats and `SceneBlend` objects. Booleans, integers and dropdowns are refused. | `SceneSettingsContextRules.cpp:91-93` (`requireNumeric = true`), `SceneSettingsInternal.cpp:946-950`, `SceneBlend.h:28-31` |
| PhysicalSky is allowed in weather scenes at all. | `SceneSettingsPolicy.h:105-118` (time-of-day whitelist, which weather uses) |
| Some PhysicalSky settings are barred from every scene. | `SceneSettingsPolicy.h:13-52` |
| A setting must also exist in the compiled scene catalog with the `Transitionable` flag. | `SceneSettingsInternal.cpp:792-807`, `:955-992`; catalog generated at build time into `build/PR/generated/SceneSettingsCatalog.generated.cpp` |
| The weather folder name is `0x<local form id>~<origin plugin>`. | `SceneSettingsDiscovery.cpp:671-679`, `src/Utils/Form.cpp:38-60` |
| The feature is read from `_feature`, or else from the file name after the last underscore. | `SceneSettingsOverwrites.cpp:202-208` |
| A weather has ONE time-of-day mode for all features. Flat files (in the weather folder) and per-period files (in `Dawn`, `Sunrise`, `Day`, `Sunset`, `Dusk`, `Night`) are two separate sets, and only the set matching the mode is active. | `SceneSettingsManager.h:462-474`, `SceneSettingsOverwrites.h:32-40` |
| The mode is: your own choice, else the pack's `_metadata.timeOfDayEnabled`, else "true only if every entry of that weather is per-period". | `SceneSettingsManager.h:462-468` |
| Only the active pack's scene files are loaded, and an active id containing `:` has no pack folder. | `SceneSettingsManager.cpp:217-220`, `src/Presets/UnifiedPresetCatalog.cpp:298-304` |
| Applying a pack that has scene files makes it the active pack. A Baseline-only pack does not. | `UnifiedPresetCatalog.cpp:676-720` |
| A Baseline file with a key the feature does not have is skipped whole. | `src/BaselineManager.cpp:517-533` |

The time-of-day rule matters here. Your `SceneManager.json` already holds per-period Look Grade entries for all
111 NAT.CS III weathers and no flat ones, so every one of them is in per-period mode today. A flat cloud file
would either be ignored or, worse, flip the weather to flat mode and switch your Look Grade entries off. The draft
therefore ships per-period files only, six per weather, with `timeOfDayEnabled: true`.

## 2. Schema

### 2.1 Weather scene file

`Weather/0x81A~Skyrim.esm/Day/foxnne-nat3-clouds_PhysicalSky.json` (SunnyPF, Day):

```json
{
  "_feature": "PhysicalSky",
  "_metadata": { "description": "...", "timeOfDayEnabled": true },
  "cloudMap": { "procedural": { "parameters": {
    "primary":      { "range": { "x": 0.3, "y": 1.0, "z": 0.0, "w": 0.45 } },
    "secondary":    { "range": { "x": 0.5, "y": 1.0, "z": 0.0, "w": 0.3 } },
    "coverageGain": { "range": { "z": 1.0, "w": 1.0 } }
  } } },
  "cloudLayer": {
    "low":      { "ndfAltitudeOffset": 1300.0, "ndfAltitudeScale": 700.0, "densityScale": 0.35, "topExpansionScale": 0.3 },
    "lighting": { "brightness": 1.0, "sunExtinction": 0.6, "viewExtinction": 0.8, "ambientStrength": 1.0 },
    "wind":     { "lowVelocity": { "x": 3.78, "y": 1.13 }, "highVelocity": { "x": 9.18, "y": 2.75 },
                  "development": 0.2, "disturbance": 0.15 },
    "cirrus":   { "altitude": 9000.0, "densityScale": 0.5,
                  "weather": { "states": [ { "value": { "layers": [ ... ], "localMap": "", "localWeight": 0.0,
                                                        "localWindScale": 1.0, "localBlendMode": 0 },
                                             "weight": 1.0 } ] } }
  }
}
```

- The tree mirrors the settings struct. The parser walks objects and treats every float, and every object of
  the exact form `{"states": [...]}`, as one entry (`SceneSettingsInternal.cpp:43-46`, `:674-697`).
- **Vector components are separate entries keyed `x`, `y`, `z`, `w`**, not arrays. The Azure Hearth files do the
  same (`sunlightColor: {x, y, z}`). You may give only some components, as with `coverageGain.range` above.
- Inside a blend state's `value` the object is deserialised as a whole struct, so there vectors are plain arrays
  (`CirrusNoiseLayer`, `src/Features/PhysicalSky/Ndf.h:260-284`).
- Values must be written as floats (`1300.0`). The loader widens integers for float settings
  (`SceneSettingsInternal.cpp:196-204`), but there is no reason to rely on it.
- Keys under `_metadata` are ignored as settings; `timeOfDayEnabled` is read from there
  (`SceneSettingsOverwrites.cpp:184-190`).

### 2.2 Baseline file

`Baseline/PhysicalSky.json`: the SettingsUser tree, so vectors are arrays (`"range": [0.3, 1.0, 0.0, 0.45]`),
booleans and integers are allowed, `_metadata` is optional. `cloudMap` needs `"version": 3`, otherwise the whole
map block is reset to defaults on load (`PhysicalSky.cpp:73-83`).

### 2.3 The same values as your own overrides

`SceneSettings/SceneManager.json` stores the user layer as
`"weather": { "<formkey>": { "entries": [ {feature, path[], setting, value, originalValue, paused, period} ] } }`
(`SceneSettingsSerialization.cpp:13-40`, `:632-705`). For a vector component, `path` ends with the vector name and
`setting` is the component, for example `path: ["cloudMap","procedural","parameters","primary","range"]`,
`setting: "x"`. The draft carries this form too (section 8).

## 3. What can be set per weather

Checked against the compiled catalog of the `build/PR` tree (generated 2026-11-16, so one day older than the
branch head; I did not regenerate it). A copy of the Physical Sky rows is in
`draft/_generator/physicalsky-scene-catalog.json`, and the generator validates every value in the draft against it.

**Per weather (float, transitionable):**

| Setting | Range in UI | Default | Struct |
|---|---|---|---|
| `cloudMap.procedural.parameters.primary.range.{x,y,z,w}` | -16..16 | -0.4, 0.65, 0, 0.65 | `Ndf.h:92` |
| `...secondary.range.{x,y,z,w}` | -16..16 | -0.2, 0.8, 0, 0.4 | `Ndf.h:93` |
| `...coverageGain.range.{x,y,z,w}` | -16..16 | -1, 1, 1, 1 | `Ndf.h:94` |
| `...primary/secondary .exponent`, `.frequency`, `.offset.{x,y}` | 0.01..8, 0..64 | 1.4 / 1, 1 | `Ndf.h:78-88` |
| `...modeling.*`, `modelingGain.*`, `heightVariation.*`, `bottomTypeRange`, `baseHeight.{x,y}` | | | `Ndf.h:95-101` |
| `cloudLayer.low.ndfAltitudeOffset` (base, m) | 0..20000 | 256 | `Ndf.h:244` |
| `cloudLayer.low.ndfAltitudeScale` (span, m) | 1..20000 | 1792 | `Ndf.h:245` |
| `cloudLayer.low.densityScale` ("Extinction Scale") | 0..1 | 0.75 | `Ndf.h:253` |
| `cloudLayer.low.topExpansionScale`, `bottomSpreadScale`, `bottomSpreadHeight`, `bottomSoftness`, `bottomSoftnessHeight`, `curvatureRadius`, `ndfScale.{x,y}` | | | `Ndf.h:246-252` |
| `cloudLayer.lighting.*` (13 floats) | | | `Ndf.h:318-333` |
| `cloudLayer.wind.lowVelocity.{x,y}`, `highVelocity.{x,y}`, `development`, `disturbance` | -80..80, 0..1 | 5,0 / 10,0 / 0.25 / 0.2 | `Ndf.h:335-343` |
| `cloudLayer.cirrus.altitude`, `densityScale`, `weather` (blend) | 1..24000, 0..4 | 8000, 1 | `Ndf.h:305-316` |
| `cloudLayer.middle.*` floats and `weather` (blend) | | | `Ndf.h:356-376` |
| `lightningIntensity`, `sunlightColor`, `masserColor`, `secundaColor`, `aerosolScatter/Absorption/PhaseG` | | | `PhysicalSky.h:122-170` |

**Not per weather:**

| Setting | Why |
|---|---|
| `enableVolumetricClouds`, `enableVanillaClouds`, `cloudLayer.cirrus.enabled`, `cloudLayer.middle.enabled` | booleans; weather scenes take floats and blends only |
| `cloudRelightMix`, `cloudOriginalMix`, `silverLiningMix`, `silverLiningSpread` | blacklisted, `SceneSettingsPolicy.h:32-35` |
| `rayMarchRange`, `shadowVolumeRange`, `marchStepScale` | blacklisted, `SceneSettingsPolicy.h:27-29` |
| `cloudBlurRadius` | integer |
| `cloudNoise.*`, `cloudMap.type`, `cloudMap.procedural.noise`, the `noise` slot of each map layer | blacklisted, `SceneSettingsPolicy.h:30`, `:37-52` |
| `aerosolType`, `aerosolLoading`, `aerosolHumidity` | blacklisted (scenes blend the derived coefficients instead) |

Two consequences for the brief:

1. **A per-weather vanilla-cloud mix is not possible in this fork.** The mix sliders are blacklisted and the switch
   is a boolean. Vanilla cloud meshes are either drawn for every weather or for none. The draft hides them in the
   Baseline (`enableVanillaClouds: false`) so the volumetric layer is the only cloud source and per-weather coverage
   is unambiguous. To change that you would have to remove lines 32-33 of `SceneSettingsPolicy.h` and rebuild.
2. **The middle (altocumulus/altostratus) layer cannot be switched per weather.** It is off by default and the draft
   leaves it off, so the draft is a two-layer sky: the low volumetric layer and the cirrus sheet. The task brief
   said "low/high/cirrus"; in this branch the layers are `low`, `middle` and `cirrus` (`Ndf.h:412-419`).

A weather can still be made cloudless: coverage gain 0 removes the low layer, cirrus density 0 removes the cirrus.

## 4. Parameters: what they look like and what they cost

Altitudes are metres above the worldspace `zBottom` (Tamriel -14500 game units, `PhysicalSky.h:129-139`).
One game unit is 0.0142875 m (`src/Utils/Game.h:50`), so on this scale the Whiterun plains sit roughly 150 to 200 m
up and the highest peaks roughly 800 to 850 m. That estimate comes from typical cell heights, not from a measurement.

### 4.1 Coverage (the weather map)

`features/Physical Sky/Shaders/PhysicalSky/NdfGenerate.cs.hlsl:155-170` builds a 512x512 map
(`Ndf.h:179`) that repeats every `low.ndfScale` km (default 16):

```
first    = Remap(noise(primary) in -1..1, primary.range) ^ primary.exponent
second   = Remap(noise(secondary),        secondary.range) ^ secondary.exponent
coverage = gain * max(first, second)            gain = coverageGain (a constant when its range z == w)
Remap(v, r) = saturate((v - r.x) / (r.y - r.x)) * (r.w - r.z) + r.z
```

So in a range, `x`/`y` are the input interval and `z`/`w` the output interval:

- raise `x` and the cloudy **area** shrinks (only the top of the noise produces cloud);
- `w` is the **peak** coverage, `z` the floor (a floor above 0 means cloud everywhere);
- `coverageGain.range` with `z == w` is a plain multiplier, and 0 removes the low layer;
- if `primary.range` has `z == w` the whole sky gets that one constant coverage (line 158-160).

Coverage turns into density through a threshold
(`CloudNoise.hlsli:54-70`, `Volumetrics.cs.hlsl:709-727`):
`density = saturate(noiseShape - (1 - min(0.7, profile)))`, with `profile = verticalProfile * coverage^k`.
Reading that: coverage below about 0.3 gives almost nothing, 0.4 to 0.5 gives small separate clouds, 0.6 gives
broken cloud, 0.7 and above is solid. The default peak of 0.65 over most of the noise range is a mostly cloudy sky.

Cost: none per frame. The map is regenerated only when a value changes, which during a weather transition is
every frame for a 512x512 compute pass, a small cost.

### 4.2 Low layer shape

| Setting | Look | Cost |
|---|---|---|
| `ndfAltitudeOffset` | Cloud base. The default 256 m is barely above the plains and below every mountain. | none directly |
| `ndfAltitudeScale` | Height span of the layer (`VolumetricClouds.cpp:343-348`). Thin spans give flat stratus or small cumulus, 2500 m and more gives towers. | Rays cross a thicker slab, so march samples grow roughly in proportion |
| `densityScale` | Extinction per metre of cloud (`VolumetricClouds.cpp:1259`). Higher means more opaque, darker bases, harder shadow. | Higher density ends rays sooner (early out), so slightly cheaper |
| `topExpansionScale` | How far tops spread into anvils (`Volumetrics.cs.hlsl:714-719`). I could not tell the exact shape from source. | none |
| `bottomSpreadScale`, `bottomSpreadHeight`, `bottomSoftness`, `bottomSoftnessHeight` | Base shaping (`VolumetricClouds.cpp:1260-1264`). Left at defaults. | none |
| `curvatureRadius` (74.9 km) | A small fake planet that bends the layer down toward the horizon. Left at default. | none |
| `ndfScale` (16 km) | Size of one repeat of the weather map. Larger gives bigger cloud systems and a visible repeat further away. Left at default. | none |

### 4.3 Lighting (`Ndf.h:318-333`, used at `VolumetricClouds.cpp:1266-1275`)

| Setting | Look |
|---|---|
| `sunExtinction` | Optical depth toward the sun. It scales both self-shadowing in the cloud and the cloud shadow cast on the world (`PhysicalSky.cpp:1925`). The main control for how dark it gets under cloud. |
| `viewExtinction` | Optical depth along the view ray (`Volumetrics.cs.hlsl:1382`): how opaque clouds look. |
| `brightness` | Overall scale of cloud radiance. |
| `ambientStrength` | Sky and ground light scattered through the cloud; lifts grey bases (`Volumetrics.cs.hlsl:1410-1429`). Above 0 it also runs the ambient transport passes. |
| `msStrength`, `msAlbedo`, `msBoundaryWidth` | Multiple scattering: how white and soft thick cloud looks. Left at defaults. |
| `dropletDiameter`, `phaseForwardG`, `phaseBackwardG` | Phase function: silver lining and glory strength. Left at defaults. |
| `scatterDensityThreshold`, `scatterDensityPower`, `cirrusLightThickness` | Left at defaults. |

Cost: lighting settings change no step counts, except that `ambientStrength = 0` (or `msAlbedo = 0`) skips the
ambient volume passes (`VolumetricClouds.cpp:1380`).

### 4.4 Cirrus

A single curved sheet at `cirrus.altitude`, not a volume (`Volumetrics.cs.hlsl:939-948`, four light taps at
`:976-978`). `weather.states[].value.layers[0]` is coverage and `layers[1]` is type, both remaps of the shared
weather noises. Visibility goes with roughly coverage cubed, so a peak under 0.4 is nearly invisible.
`cirrus.densityScale` multiplies the result; 0 hides it. Cheap.

### 4.5 March quality (Baseline only)

| Setting | Default | Effect | Cost |
|---|---|---|---|
| `marchStepScale` | 0.5 (UI 0.125..2) | Step length is `(3 m + distance * 60/16384) * scale` (`Volumetrics.cs.hlsl:653-662`), doubled in empty space (`:1376`). Larger steps lose thin detail and add noise. | Samples per ray are proportional to 1/scale. A horizon ray from 5 km to 32 km is about 940 samples worst case at 0.5 and about 470 at 1.0; a ray straight up through a 700 m layer at 1.3 km is about 150 at 0.5. Rays stop early once opaque. |
| `rayMarchRange` | 32 km (1..64) | Farthest low cloud drawn (`Volumetrics.cs.hlsl:604`). Too short and clouds stop before the horizon. | Steps grow with distance, so the far end is cheap per kilometre: at 0.5, going from 32 to 64 km adds about 370 samples to a horizon ray and going from 32 to 24 km saves about 150. |
| `shadowVolumeRange` | 8 km (1..16) | Side of the box around the camera in which cloud shadows on the world are resolved. The volume is fixed at 256 x 256 x 64 (`PhysicalSky.h:291-293`), so a texel is range/256: 31 m at 8 km, 62 m at 16 km. Outside the box a single mean transmittance is used (`ShadowVolume.hlsli:19-52`). | Fixed resolution, so cost is flat; the trade is sharpness against reach. |
| `cloudBlurRadius` | 1 (0..2) | Final blur in internal pixels (`PhysicalSky.cpp:1398-1400`). 2 hides march noise and softens edges. | One filter pass; 0 skips it. |
| `halfResApShadow` | false | Cloud shadow in the aerial perspective at half resolution. | Cheaper shadow accumulation pass. |
| `cloudLayer.middle.enabled` | false | Adds the middle layer and its own passes. | Not estimated. |

The main view is traced at quarter resolution in each axis, one pixel of every 4x4 block per frame
(`VolumetricClouds.cpp:1197-1198`, `CloudTemporal.hlsli:335`, `:413`), and rebuilt over 16 frames by reprojection.
So the per-frame ray count is internal pixels / 16.

The draft's two variants (`draft/baseline-variants/`):

| | quality | performance |
|---|---|---|
| `marchStepScale` | 0.5 | 1.0 |
| `rayMarchRange` | 32 | 24 |
| `shadowVolumeRange` | 8 | 6 |
| `cloudBlurRadius` | 1 | 2 |
| `halfResApShadow` | false | true |

Quality is simply the fork's defaults; the copy inside the pack is the quality one. I have no timings for either.

## 5. Why a clear noon went dark, grey and desaturated

All of these follow from switching the feature on with defaults and no per-weather scenes. Ranked by how much I
think each contributed; none is confirmed in game.

1. **The default sky is mostly cloudy, whatever the weather.** Default primary coverage maps noise -0.4..0.65 to
   0..0.65 with gain 1 (`Ndf.h:92-94`). Nothing ties it to the game weather unless a weather scene overrides it,
   and there were none. A NAT "Sunny" weather therefore got the same broken-to-solid deck as a storm.
2. **That deck is optically thick and it shadows the world physically.** `low.densityScale` 0.75 and
   `sunExtinction` 1. Sunlight on every surface is multiplied by the cloud transmittance from the shadow volume
   (`features/Physical Sky/Shaders/PhysicalSky/Common.hlsli:741-770`), and ambient light by a clouded/clear
   transport ratio (`Common.hlsli:713-725`). Under a deck both drop together, which reads as grey and
   desaturated rather than as shade.
3. **The layer starts at 256 m and is 1.8 km deep.** That puts the cloud base just above the plains and wraps every
   mountain, so there is cloud between the camera and distant terrain: a grey veil over the vista.
4. **Vanilla cloud meshes were still drawn** (`enableVanillaClouds` default true, `package/Shaders/Sky.hlsl:388-395`),
   relit and stacked with the volumetric layer and the default cirrus (density 1 at 8 km).
5. **Your sun is already tuned down for a cloudless model**: `sunlightColor` 7 against the default 10, with
   `aerosolLoading` 0.7. Any cloud shadow lands on top of that.

What the draft does about it: clear weathers get coverage gain 0 (`SClearSky*`) or a peak coverage of 0.45 on the
top third of the noise (`Sunny*`), base at 1300 to 1400 m, density 0.3 to 0.35 and `sunExtinction` 0.5 to 0.6.

## 6. Why distant fog and grass shimmered

I could not confirm a single cause from source. These are the candidates, most likely first.

1. **Cloud volume in front of terrain, rebuilt at 1/16 rate.** With the base at 256 m the low layer intersects
   mid-distance and far terrain. The composite is traced for one pixel in sixteen per frame and reprojected;
   history is rejected at depth edges (`CloudTemporal.hlsli:335-342`, `:413-436`). Grass and tree silhouettes against
   a cloud or haze background are exactly such edges, so they would crawl. Raising the base above the terrain
   removes the overlap, which is the first thing the draft does.
2. **March jitter.** The start of each ray is jittered per frame (`Volumetrics.cs.hlsl:624-629`, `:1359`). Longer
   steps (higher `marchStepScale`) make each jittered sample differ more, and the blur radius decides how much of
   that survives.
3. **Coarse, camera-snapped cloud shadow.** World shadows come from a 256 x 256 x 64 volume snapped to its grid
   (`ShadowVolume.hlsli:8-12`): 31 m texels at the default 8 km. Grass is switched to a different sampler while
   volumetric clouds are on (`PhysicalSky.cpp:2368-2378`), and distant fog is lit through the same data in the
   aerial perspective. Past the box edge the shadow falls back to one mean value, so a moving edge of shade sits
   about 4 km out, right where distant fog is.
4. **Upscaler and frame generation.** The cloud passes run on the internal resolution and their own history, not on
   DLSS history. I did not check how they interact here.

To separate them in game: set `marchStepScale` 0.25 (if the shimmer falls, it is 2), set `shadowVolumeRange` 4 (if
the shimmer on grass changes scale, it is 3), raise the base to 1500 m (if it goes away, it was 1).

## 7. What the Azure Hearth reference does

`C:\Users\foxnn\dev\nat3-volclouds\ref-azure\extracted\SKSE\Plugins\CommunityShaders\Presets\AzureHearth\`

- **It does not use volumetric clouds.** `Baseline/PhysicalSky.json` sets `enableVolumetricClouds: false`,
  `enableVanillaClouds: true`, `cloudRelightMix: 1.0`, `cloudOriginalMix: 0.68`, `sunlightColor: [9.2, 8.92, 8.74]`.
  It relights Azurite's cloud textures. So it gives no cloud value ranges at all; the cloud numbers in this draft
  come from the fork's defaults and shader code, not from the reference.
- Layout: manifest (`type: "CS"`), `Baseline/` (5 features), `InteriorOnly/`, `TimeOfDay/<Period>/`,
  `Weather/<formkey>/` for 91 weathers, `LUT/`, and `Forms/Volumetric Lighting/` with 59 per-weather form edits.
  No other folder exists under `Forms`. 548 files in total.
- Per-weather Physical Sky files exist for 59 weathers (42 flat, 17 per-period; the per-period ones are the aurora
  weathers). They carry only `sunlightColor`, `masserColor`, `secundaColor`, and for non-clear weathers
  `aerosolScatter`, `aerosolAbsorption` and sometimes `aerosolPhaseG`.
- Its grouping, from the file descriptions: Clear sky (5), Broken cloud (10), Broken cloud with light snow (6),
  Heavy cloud (2), Heavy cloud with light snow (3), Overcast (1), Fog (7), Rain (5), Heavy rain (2),
  Thunderstorm (3), Snowfall (4), Blizzard (1), Ashfall (5), Ash storm (1), Burning sky (2), Forgotten Vale (2).
  The same weather type is repeated per region (Marsh, Coast, Reach, Fall forest, Tundra, Snowfields, Hot springs)
  with identical values.
- Its values, Day period:

| Reference group | sun (R) | aerosol scatter | aerosol absorption |
|---|---|---|---|
| Clear sky | 7.85 | not set (default 39.96) | not set (4.44) |
| Broken cloud | 7.71 | 49.95 | 5.55 |
| Broken cloud, light snow | 7.85 | 55.94 | 6.22 |
| Heavy cloud | 3.38 | 63.9 to 71.9 | 7.1 to 8.0 |
| Heavy cloud, light snow (Skuldafn) | 2.70 | 71.93 | 7.99 |
| Overcast | 1.81 | 99.9 | 11.1 |
| Snowfall | 1.81 | 119.88 | 13.32 |
| Rain | 1.81 | 139.86 | 15.54 |
| Heavy rain | 1.81 | 199.8 | 22.2 |
| Thunderstorm | 1.81 | 239.76 | 26.64 |
| Blizzard | 1.71 | 319.68 | 35.52 |
| Fog | 1.81 | 399.6 | 44.4 |
| Ashfall | 1.81 to 3.08 | 159.84 | 53.28 |
| Ash storm | 0.91 | 319.68 | 142.08 |

What to take from it: without volumetric clouds the author dims the sun by hand, to about a quarter under overcast,
and thickens the haze 2.5x to 10x for bad weather. With volumetric clouds on, the dimming comes from the cloud
shadow itself, so the draft does **not** also lower `sunlightColor`; doing both would darken twice. The haze
figures are still a sensible starting point if rain and fog weathers later look too clear at distance, but that is
an atmosphere change and outside this draft.

## 8. The draft and how it would be installed

```
draft/
  foxnne-nat3-clouds/                       the pack
    foxnne-nat3-clouds.json                 manifest, type CS
    Baseline/PhysicalSky.json               quality variant
    Weather/<formkey>/<Period>/foxnne-nat3-clouds_PhysicalSky.json     111 weathers x 6 periods = 666 files
  baseline-variants/quality|performance/PhysicalSky.json
  alt-user-overrides/SceneManager.weather.PhysicalSky.json             same values as user-layer entries
  _generator/build_draft.py                 group table and generator; inputs beside it
```

Nothing was copied anywhere. The target would be
`C:\Modlists\NGVO 8.0 Beta\mods\CS Settings\SKSE\Plugins\CommunityShaders\Presets\foxnne-nat3-clouds\`, beside the
existing `foxnne-look` (a Baseline-only pack with no `PhysicalSky.json`, so the two do not overlap).

**Read this before applying.** `SettingsUser.json` currently says
`"Presets": {"activePackId": "e11:fnenb Cabbage", "baselinePackIds": ["foxnne-look"], "pipeline": "PostProcessing"}`.
The pack as drafted contains scene files, so applying it makes `foxnne-nat3-clouds` the active pack in place of
`e11:fnenb Cabbage` and re-selects the Post Processing pipeline (`UnifiedPresetCatalog.cpp:697-712`). The pipeline is
already Post Processing, but I could not tell from source whether losing `e11:fnenb Cabbage` as the active id
changes anything you see. Two ways to install:

- **Route A, as a pack.** Copy the folder, apply it on the Presets page. Simple, and the values show as the pack's
  (blue) in the editor. Replaces the active pack id as described.
- **Route B, without touching the active pack.** Copy the pack folder *without* its `Weather` folder: it is then
  Baseline-only and applying it leaves the active pack alone (`UnifiedPresetCatalog.cpp:700`, `:714-717`). Put the
  per-weather values into your own layer instead, by appending each weather's `entries` from
  `alt-user-overrides/SceneManager.weather.PhysicalSky.json` to the matching `entries` array in
  `SceneSettings/SceneManager.json` (game closed, backup first; the keys already exist for all 111 weathers).
  Your overrides then show green and can be edited per weather in the CS Editor.

Either way the Baseline sits below your own edits, and you have no saved edit for any key it sets (your edits are
`sunlightColor`, `cloudRelightMix`, `aerosolLoading`), so it takes effect. `cloudRelightMix` stops mattering while
vanilla clouds are hidden.

Weathers with no file (the Helios copies, map and interior-light weathers, other mods) fall back to the Baseline,
which carries the fair-weather values, so an uncovered weather gets a nearly clear sky and not the dark default.

## 9. What I could not determine

- Nothing was run. Whether every file loads without a warning in `CommunityShaders.log` is unverified; the check I
  could do is the offline one against the compiled catalog (0 problems), and that catalog is from the `build/PR`
  tree of 2026-11-16, not necessarily the DLL that is deployed.
- Whether a blend-valued entry (`cloudLayer.cirrus.weather`) coming from a pack file passes the last compatibility
  check (`IsCompatibleSceneSettingValue`). The reference pack has no blend entries to compare with. If it is
  refused, only the cirrus coverage is lost; `cirrus.densityScale` still works.
- The statistics of the four weather noises, so the real sky fraction for a given coverage range. The coverage
  numbers are reasoned from the remap and the density threshold, not from a rendered map.
- How partial nested objects in a Baseline file merge (deep or per top-level key). Either way the result is valid,
  because every nested struct fills missing members with defaults, but with a shallow merge untouched members of
  `cloudLayer` would come from defaults rather than from an earlier layer.
- What `topExpansionScale` and the cloud type channels look like; units and direction convention of the wind
  velocities; whether NAT's wind direction should drive them.
- Whether hiding vanilla cloud meshes removes anything NAT draws through cloud layers besides clouds. Auroras
  normally use their own mesh, but I did not check NAT's records.
- The effect of replacing `e11:fnenb Cabbage` as the active pack (section 8).
- The cause of the shimmer (section 6) and all performance figures.
