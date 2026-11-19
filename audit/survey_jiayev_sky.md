# Survey: jiayev/skyrim-community-shaders sky work vs our fork (2026-11-18)

Clone: `C:\Users\foxnn\dev\_survey\jiayev-cs` (partial clone, branch `parametric-sky` @ 5bf3f31ce checked out). Read-only comparison against
`C:\Users\foxnn\dev\skyrim-community-shaders` (`foxnne/nr-pr6` @ e8e1d0d50). No builds, no game launch. (Work in progress - sections appended below.)

## Headline (early)

- The newest sky code in jiayev's fork is branch `parametric-sky` (last commit 2026-11-18). Its sky/cloud/atmosphere code is
  **the same code we already have**: `src/Features/PhysicalSky.h` and every file in `src/Features/PhysicalSky/` except one are byte-identical
  (ignoring line endings); the Settings structs and every default are identical. The handful of differing files differ only by things on OUR side
  (texture slot renumbering / reverse-Z helpers from upstream dev, and our own fork additions).
- So the screenshots are NOT explained by missing code. They are explained by SETTINGS: our live file departs strongly from the shipped defaults
  (e.g. `low.densityScale` 0.059 vs default 0.75).

## 1. Branches and recent activity (jiayev fork)

159 remote branches. Those touched in the last ~6 weeks (last commit date):

| Date | Branch | Note |
|---|---|---|
| 2026-11-18 | `parametric-sky` (5bf3f31ce) | **the Physical Sky / volumetric cloud development branch**; just merged upstream dev (which now contains #3157) |
| 2026-11-18 | `pp-share-rt` (371778b4c) | post-processing VRAM work; sky paths identical to `parametric-sky` (0 files differ) |
| 2026-11-18 | `compendium-clean` (78d4ab4eb), `compendium-env-probe` (9e80795c7) | jiayev's all-in-one "compendium" build branches. Sky differs from `parametric-sky` in 9 / 11 files: they carry the upstream-#3157 variant (CPU fallback that builds the vertical profile from `top_lut.dds`/`bottom_lut.dds` when the Nubis LUTs are missing, ~100 lines in `VolumetricClouds.cpp`), nothing that changes the look when the shipped LUTs are present |
| 2026-11-17 | `pp-physlens`, `advanced-skin` | unrelated |
| 2026-11-16 | `pp`, `origin` | upstream-tracking, pre-psky (80 sky files differ = no psky) |
| 2026-11-13/14/15 | `grass-wetness`, `pbr-nif`, `revert-78-psky/restore-upstream` | unrelated / merge housekeeping |
| 2026-10-13..15 | `volumetric-fog`, `scenemanager-pp`, `waterintreflectionfix` | older |
| 2026-08-13 | `physky/cloud-quality-p1` | stale experiment (85 files behind) |
| 2026-04-03 | `cloud-relight` | old vanilla-cloud relight |

Commits on `parametric-sky` touching sky paths, last 6 weeks (68), by theme:

- **Local cloud maps / weather map**: 4e662f8aa local ndf (10-05), 9a3249131 + bb8ea7f4d middle cloud + opti (11-11), 0003e9d70 weather review (11-13).
- **Cirrus**: 1497d9159, 30e723a97 (10-10).
- **Cloud lighting**: 03e2cdcfa "cloud lighting rewrite, unified composite" (10-21), 15dd30296 fix leaking cloud lighting, 7a8e03512 drop screenspace march, f38f85827 swap to cascade (11-17), 57a3a7715 occlude cloud sunlight with terrain (11-16), 8cc84ac21 correct cloud shadowing (11-17), f069f6942 gate cloud self shadow.
- **Storms / voxel clouds / lightning**: 6ea45027a storm and voxel cloud (10-26), 7a26ba87c lightning (10-30).
- **Reflections / fog**: 6a3ca9e49 fix fog/cloud in reflection (10-30), 624de26b5 fix cubemap cloud.
- **Sun/moon**: f2444f520 phys sky light disk, aec8603c5 lunar illuminance controls (11-16), ee237502b angular size in transmittance (11-17), 2539a82d3 / ffb2aeaa6 sky sync caster handovers.
- **Performance**: af95178cb cloud optimize (10-21), a92fbda05 cut cloud cost with volumetrics off, 2e21fd6d9 cut psky shader compile time, e9904777e async compute shader compilation.
- **Exposure**: d5d96328b preexposure (10-27). **Housekeeping**: d336bb56c purge unused dds, 0641bd74e ini edit, ba734bda9 UI strings.

## 2. Code comparison (their `parametric-sky` vs our `foxnne/nr-pr6`)

Compared with `diff --strip-trailing-cr` on working trees.

- `src/Features/PhysicalSky.h`: **identical** (all Settings fields and defaults).
- `src/Features/PhysicalSky/*` (Aerosol, CloudNoiseGenerator, Lightning, LocalNdf, Ndf, Storm, VoxelCloud): **identical**, except `VolumetricClouds.cpp`.
- `features/Physical Sky/Shaders/PhysicalSky/*`: same 42 files; 35 identical. `features/Physical Sky/Textures/*`: identical.
- `docs/physical-sky/*`: identical (12 docs).
- Files that differ, and why (all differences are on OUR side; they have nothing newer):
  - `PhysicalSky.cpp`, `VolumetricClouds.cpp`, `ViewAtmosphere.cpp`, `Common.hlsli`, `DiskPhase.hlsli`: pixel-shader texture slots only. Theirs bind PS at t106/t109-t116 (deferred t16-t20); ours binds PS at t24/27/28/32-34/54/56/57 (deferred t20-t24). No behaviour difference intended.
  - `CloudTemporal.hlsli`, `CloudVoxelView.hlsli`, `LightningView.hlsli`, `ShadowAccum.cs.hlsl`, `UpperCloudTiles.hlsli`, `ViewAtmosphere/Composite.cs.hlsl`: ours wraps depth tests in `FrameBuffer::ToStandardDepth` / `ToNativeDepth` (reverse-Z support). Theirs is plain depth.
  - `ViewAtmosphere/LightScattering.cs.hlsl`: ours adds `MediumTerrainShadow` (soft terrain shadow in haze) and weather-driven height fog (`useVanillaFogSettings`). Theirs uses the hard `TerrainShadows::GetTerrainShadow` and has no weather-fog path.
  - `CloudShadows.cpp`: ours adds the `Scattering` setting. `SkySync.cpp`: ours adds moon-hidden handling and aurora working light (`ProceduralNightSky`, which they do not have).
- New files there that we lack: **none** in sky/atmosphere. New Settings fields: **none**. Changed defaults: **none**. New shader passes: **none**.
- Things we have that they lack: `ProceduralNightSky.*`, cloud-shadow scattering, medium terrain soft shadow, weather fog in the medium, reverse-Z depth helpers.

Conclusion: there is no cloud shape / lighting / reconstruction / aerosol code to port. Their renderer is our renderer.

## 3. Defaults and presets

No shipped cloud preset exists anywhere in the repo: `package/SKSE/Plugins/CommunityShaders/Presets/` holds only a README; there are no Scene Manager weather files, no example settings JSON, and the #3157 squash commit message has no description. The only shipped cloud data file is `features/Physical Sky/Textures/PhysicalSky/Storms/RedMountain/Instance.json` (Solstheim volcanic plume). So "their settings" means the struct defaults in `src/Features/PhysicalSky.h`, `src/Features/PhysicalSky/Ndf.h`, `CloudNoiseGenerator.h`, plus whatever jiayev dialled in by hand for the screenshots (not recorded in the repo).

Our deployed `mods/CS Settings/SKSE/Plugins/CommunityShaders/SettingsUser.json` "Physical Sky" block stores only overrides, so it is the exact list of where we depart from defaults. Everything not in this table equals the default (weather map, 3D noise bands, lighting phase / multi-scatter / ambient, `marchStepScale` 0.5, `cloudBlurRadius` 1, `shadowVolumeRange` 8, aerosol coefficients, silver lining).

| Key | Ours (live) | Their default | Effect of our value |
|---|---|---|---|
| `cloudLayer.low.densityScale` (extinction, 1/m) | **0.059** | **0.75** | 12.7x thinner medium. Edges and thin parts become translucent haze instead of defined surfaces; it also divides sunlight self-shadowing and ground-shadow density by 12.7 (the same density feeds all three). UI tooltip: "At density 0.1 and scale 0.75, a 40 m path transmits about 5%"; at 0.059 the same path transmits about 79%. |
| `cloudLayer.lighting.sunExtinction` | **0.559** | 1.0 | Further halves self-shadowing. Combined with density, optical depth toward the sun is about 23x lower than default, so folds are not shaded. |
| `cloudLayer.lighting.brightness` | **2.583** | 1.0 | Compensating gain; lifts everything uniformly, so the unshaded cloud goes flat white / milky. |
| `cloudLayer.lighting.viewExtinction` | 1.033 | 1.0 | negligible |
| `cloudLayer.low.curvatureRadius` (km) | **384.93** | **74.946** | Deck drop = d^2/R (`CloudGeometry.hlsli`). Default: 1.3 km at 10 km, 5.3 km at 20 km, so the deck sinks under the horizon within roughly 10-15 km and the horizon shows a clean sky gradient. Ours: 0.26 km at 10 km, 1.0 km at 20 km, 4.4 km at 41 km, so cloud continues to the horizon at grazing angles, stacking into a pale band seen through 20-40 km of haze. |
| `rayMarchRange` (km) | 41 | 32 | More far cloud (and cost). Works with the curvature to fill the horizon. |
| `cloudLayer.low.ndfScale` (km) | **[24.66, 16.7]** | [16, 16] | Weather map stretched 1.54x in X only: cloud masses become elongated ovals, and the cell pattern of weather-noise slot 3 (12 cells per tile) reads as regular blobs about 2.05 x 1.39 km. The 3D detail noise is fixed in metres and does not scale with this, so bigger blobs get relatively finer, weaker erosion = "stamped popcorn". |
| `cloudLayer.low.ndfAltitudeOffset` / `ndfAltitudeScale` (m) | 236 / 1911 | 256 / 1792 | minor |
| `cloudLayer.low.bottomSpreadScale` | 0.794 | 0.8133 | negligible |
| `cloudLayer.cirrus.densityScale` | 1.596 | 1.0 | denser high veil = more overall whiteness over the blue |
| `cloudLayer.wind.lowVelocity` / `highVelocity` (m/s) | [14.1, 0] / [16.8, 0] | [5, 0] / [10, 0] | faster drift; more stress on temporal reconstruction (1 of 16 pixels traced per frame), can smear detail |
| `cloudRelightMix` | 0.7 | 1.0 | vanilla cloud meshes only |
| `sunlightColor` | [7, 6.79, 6.65] | [10, 9.7, 9.5] | same hue, 0.7x illuminance |
| `aerosolLoading` | 0.7 | 1.0 | **inert**: with `aerosolType` 0 (Custom) loading and humidity are ignored (`Settings::GetAerosolOptics` returns the raw coefficients). Our aerosol scatter / absorption / g / falloff are the defaults (39.96 / 4.44 per Mm, g 0.8, 1/1.2 km). |
| `sunDiskRad` | 0.0024 (deployed file) / 0.00925 (live dump) | 0.00925 (0.53 deg) | the two files disagree |
| `lightningIntensity` | 0.04 (deployed) / 0 (live) | 0 | n/a |
| `cloudMap.localCloud.states[0]` | enabled, empty asset, default size | empty | no effect (no asset) |

Most plausible causes of "milky, stamped popcorn", in order:

1. `densityScale` 0.059 + `sunExtinction` 0.559 + `brightness` 2.583: translucent, not self-shadowed, over-gained. This is the lighting / softness difference; bright tops with shaded folds need optical depth toward the sun.
2. `curvatureRadius` 385 km + `rayMarchRange` 41: a cloud wall to the horizon instead of a clean gradient.
3. `ndfScale` [24.66, 16.7]: anisotropic stretch of the coverage cells.
4. cirrus density 1.6 adding a white veil.

Caveat: `docs/physical-sky/cloud-lighting.md` itself says the 0.75 density default "comes from one captured frame and remains provisional", and the docs lag the code in places (they still quote brightness 0.5 and density 0.125 as initial values). The defaults are the author's working values, not a tuned preset.

## 4. "Sea of clouds below the peaks"

Height contract: low-cloud altitude (m) = `ndfAltitudeOffset` + `ndfAltitudeScale` x NDF height (0..1), measured above the worldspace `zBottom` (Tamriel -14500 units). Convert a game z with `altitude_m = (z + 14500) * 0.01428`. The default layer therefore spans 256-2048 m above that reference, i.e. game z from about 3,400 up to about 128,900: its base sits just above the Whiterun plain and its possible top is far above every summit. Column height comes from coverage (`heightFromCoverage` = 1, `baseHeight` [0, 0.95], `heightVariation` out range [0, 0.02]), so ordinary cumulus only fill the lower part of the span. Standing on a high peak (roughly z 35-48k, about 700-900 m) at defaults already puts the camera above most tops in a high-coverage sky; the screenshot is very likely defaults or near-defaults seen from altitude at low sun.

To force it:

- Lower and compress the layer: `low.ndfAltitudeOffset` about 150-250, `low.ndfAltitudeScale` about 400-600, so tops stay below about z 35k. These are scene-authorable, so this can be a weather or location override.
- Raise coverage: `cloudMap.procedural.parameters.primary.range` is [inMin, inMax, outMin, outMax]; default output is [0, 0.65]. Raise outMin (0.3-0.4) and outMax (0.85-0.95) for a near-continuous deck. `coverageGain` output range [1, 1] is the global multiplier.
- Flatter tops: lower the `modeling.range` output max (top type toward stratiform); keep `topExpansionScale` 1.
- Keep `curvatureRadius` at the default 75 km: from above, this is what makes the deck fall away to a horizon line with clean sky above it.
- A Local Cloud (`cloudMap.localCloud`: one authored Height/Modeling DDS pair under `Data/Textures/PhysicalSky/LocalNdf/<Id>/`, placed in metres with altitude / heightSpan) is the tool for a valley-filling hero deck at one location. It needs authored textures; none are shipped.
- The golden-hour look comes from the atmosphere LUTs and the sun's transmittance at low elevation; there is no special setting. Optional: `aerosolType` 1 (Continental) or 2 (Marine) with `aerosolLoading` about 0.5-1 and humidity 50 gives a physically derived, slightly coloured haze instead of the grey Custom coefficients (untested).

## 5. Performance / quality and per-weather documentation

- `docs/physical-sky/cloud-sampling.md`: step = (3 + 60 * distance / 16384 m) * `marchStepScale` (default 0.5); the march stops at T <= 0.1 or at `rayMarchRange` (default 32 km, includes clear air). One pixel per 4x4 block is traced per frame (16 phases) with full-resolution temporal reconstruction; a 64x64x6 cubemap runs on the same schedule. There is no trace-resolution option; the knobs are `rayMarchRange` (1-64), `shadowVolumeRange` (1-16, default 8), `marchStepScale` (0.125-2), `cloudBlurRadius` (0-2, default 1), `halfResApShadow`.
- `cloud-lighting.md`: ambient transport cascades use about 29.3 MiB, target under 0.1 ms; ambient strength 0 skips it.
- UI text: "A shorter ray or shadow range and a larger march step cost less; smaller steps keep more detail at a higher cost."
- Per-weather: `docs/development/scene-settings-framework.md`, section "Physical Sky". Scene Manager contexts (weather, time of day, location, interior) can override sun/moon colours, atmosphere coefficients, low-cloud altitude / span / map scale / curvature / density / profile, weather-map coverage and type ranges, cirrus state, cloud lighting and wind. Global only: quality settings, noise sources, texture paths, relight mixes. Weather contexts cannot toggle clouds ("fade cloud density instead"). No weather files are shipped, and nothing maps vanilla weather records to cloud states automatically.

## 6. What to port / copy

Settings first (no code):

1. Remove our overrides for `cloudLayer.low.densityScale`, `cloudLayer.lighting.{brightness,sunExtinction,viewExtinction}`, `cloudLayer.low.{curvatureRadius,ndfScale,ndfAltitudeOffset,ndfAltitudeScale,bottomSpreadScale}`, `cloudLayer.cirrus.densityScale`, `rayMarchRange` and wind. Effort: minutes. Code risk: none. Note the backup `SettingsUser.json.bak-pre-psky-defaults-20261117`: a defaults reset was apparently tried once already, so check whether something re-applies the tuned values.
2. If the result is then too dark or too bright, correct it in exposure / tonemapping or `sunlightColor`, not with cloud `brightness`.

Code: nothing required. Optional, low value:

- Upstream #3157 profile-LUT fallback (branch `compendium-clean`, `src/Features/PhysicalSky/VolumetricClouds.cpp` `CreateProfileFallbacks`, plus `top_lut.dds` / `bottom_lut.dds`): only matters when the Nubis LUT DDS files are missing; ours are deployed. Skip.
- Our tree already contains 8cc84ac21 (cloud shadowing), 15dd30296 / f38f85827 (lighting leak, cascade) and 57a3a7715 (terrain occlusion of cloud sunlight), since the files are identical.

Recommended first try (UNTESTED), same key structure as `physicalsky_live.json`:

```json
{
  "rayMarchRange": 32.0,
  "marchStepScale": 0.5,
  "cloudBlurRadius": 1,
  "shadowVolumeRange": 8.0,
  "cloudLayer": {
    "low": {
      "densityScale": 0.75,
      "ndfAltitudeOffset": 256.0,
      "ndfAltitudeScale": 1792.0,
      "ndfScale": [16.0, 16.0],
      "curvatureRadius": 74.946,
      "bottomSpreadScale": 0.8133333,
      "bottomSpreadHeight": 0.3,
      "bottomSoftness": 1.0,
      "bottomSoftnessHeight": 0.68,
      "topExpansionScale": 1.0
    },
    "lighting": { "brightness": 1.0, "sunExtinction": 1.0, "viewExtinction": 1.0, "ambientStrength": 1.0, "msStrength": 1.0, "msAlbedo": 0.999 },
    "cirrus": { "densityScale": 1.0 },
    "wind": { "lowVelocity": [5.0, 0.0], "highVelocity": [10.0, 0.0] }
  }
}
```

Cloud-sea variant (UNTESTED), applied on top of the above:

```json
{
  "cloudLayer": { "low": { "ndfAltitudeOffset": 200.0, "ndfAltitudeScale": 500.0 } },
  "cloudMap": { "procedural": { "parameters": { "primary": { "range": [-0.4, 0.65, 0.35, 0.9] } } } }
}
```

## Not determined

- The actual settings jiayev used for the screenshots (not in the repo: no preset, PR text or wiki in the clone). The GitHub PR page and Discord were not consulted.
- Whether the deployed DLL in `mods/Bottled Shaders - foxnne` matches fork HEAD (its `textures/PhysicalSky` is dated 11-16 and still has `top_lut.dds` / `bottom_lut.dds`).
- Whether Scene Manager scenes or the Baseline pack override Physical Sky at runtime (a grep of `SceneSettings` and `Presets` for PhysicalSky / densityScale found nothing).
- Exact peak z values (conversion formula given; verify with `player.getpos z`).
- Nothing was rendered. The cause ranking comes from reading the density and lighting equations, not from A/B captures. In particular, whether 0.75 is the best density or merely much better than 0.059 is unknown; a sweep 0.2 / 0.4 / 0.75 is cheap.
