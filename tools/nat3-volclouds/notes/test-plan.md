# Test plan for the foxnne-nat3-clouds draft

Untested draft. The point of the first session is to find out which of the guessed numbers are wrong, in an order
that changes one thing at a time. Mechanism, schema and install routes are in `how-it-works.md`; values per weather
are in `weather-table.md`.

## 0. Before the first launch

1. Do this when no benchmark is running: it needs the game.
2. Back up `mods\CS Settings\SKSE\Plugins\CommunityShaders\SettingsUser.json` and `SceneSettings\SceneManager.json`.
3. Install by route A or route B (`how-it-works.md` section 8). Route B keeps `e11:fnenb Cabbage` as the active
   pack; use it if you do not want to find out what replacing the active pack does.
4. After loading a save, open the Community Shaders log (`CommunityShaders.log` in the SKSE log folder) and search for `[SceneSettings]` warnings and for
   `Baseline`. A line such as "entry ... is not permitted", "is blacklisted" or "Skipped Baseline file" means a
   file was refused, and the look you see is not the draft. Stop and fix that first.
5. In the CS menu, Physical Sky > Clouds: "Enable Volumetric Clouds" should be ticked with a "Ready" badge, and
   "Enable Vanilla Clouds" unticked.

## 1. Order of weathers

Force each with the console (`fw <form id>`; the load-order byte goes in front of the id for NAT-ENB.esp records),
at 12:00 unless noted (`set gamehour to 12`).

| # | Weather | Form key | Group | Why this one |
|---|---|---|---|---|
| 1 | SClearSkyPF | `0x7F00~NAT-ENB.esp` | clear_sky | Coverage gain 0. Proves the clear case and that the per-weather layer is applied at all. |
| 2 | SunnyPF | `0x81A~Skyrim.esm` | clear | The weather that looked dark before. Few small cumulus. |
| 3 | CloudyPF | `0x12F89~Skyrim.esm` | cloudy | Broken cloud; the reference point for cloud shape and shadow contrast. |
| 4 | OvercastPF | `0x53B6~NAT-ENB.esp` | overcast | Full deck: is it grey but still readable, not black? |
| 5 | RainPF | `0xC821F~Skyrim.esm` | rain | Thicker, darker deck with rain. |
| 6 | StormPF | `0xC8220~Skyrim.esm` | storm | Deepest and darkest; also the most expensive. |
| 7 | FogPF | `0xC821E~Skyrim.esm` | fog | Low thin deck together with height fog; the shimmer case. |
| 8 | Snow, then Snowstorm | `0x4D7FB~Skyrim.esm`, `0xC8221~Skyrim.esm` | snow, snowstorm | Bright snow deck against the blizzard deck. Test near Dawnstar or Winterhold. |

Then two transitions, without `fw` (use `sw <id>` so the weather blends): SunnyPF to StormPF and back, watching
for popping or a sudden change in cloud shape, and one aurora weather at night (`SunnyPF_A`,
`0x10E1F2~Skyrim.esm`, 23:00) to check the aurora is not hidden.

## 2. The two views

**Plains view.** Whiterun tundra, standing west of the city looking east across grass toward the mountains, sun
high. This shows sun and shade on near ground, grass, and the plains-to-mountain distance.

**Lake vista.** Lake Ilinalta shore near Riverwood looking west down the lake (or Lake Honrich from Riften docks).
This shows a long open distance, water reflection of the sky, and haze and fog toward the horizon.

What to look at, in this order:

| Check | Plains | Lake |
|---|---|---|
| 1. Sun on the ground | In clear weathers the ground is in full sun and as bright and saturated as with volumetric clouds off. Toggle the feature off and on to compare the same frame. | Same, on the far shore. |
| 2. Sky coverage | Does the amount of cloud match the weather's name? Clear: blue with a few small clouds or none. Cloudy: about half. Overcast and worse: no blue. | Coverage toward the horizon; does cloud end in a hard line before the horizon (march range)? |
| 3. Cloud altitude | Clouds clearly above the mountain tops in clear and cloudy weather. In overcast and storm, peaks in cloud is intended. | Cloud base against the far ridgeline. |
| 4. Cloud shadows | In cloudy weather: moving patches of shade on the plain, soft edged, not black. | Shade patches on the water and far shore; any blocky stepping at the 30 m scale. |
| 5. Shimmer | Stand still for ten seconds and watch distant grass edges and the tree line against the sky. Then walk forward. | Watch the fog band at the far shore and the water horizon. |
| 6. Colour under cloud | Overcast noon should be neutral grey and darker than clear, with detail still visible in shadows. | Water should take the sky's grey, not go black. |
| 7. Reflection | not applicable | Clouds in the water should match the sky's coverage (they come from a separate cube pass). |
| 8. Cost | Note the frame time for clear, cloudy and storm with the performance overlay. | Same. The horizon-heavy lake view is the expensive one. |

Send full-resolution screenshots when comparing, not downscaled ones.

## 3. What to change first

All of these can be tried live in the CS Editor on the weather's Scene Manager page, then written back into
`GROUPS` in `draft\_generator\build_draft.py` so every weather of the group follows.

### A clear day is still too dark

In this order, one at a time:

1. **Confirm the weather layer is applied.** In SClearSkyPF the coverage gain is 0, so there must be no low cloud
   at all. If there is cloud, the per-weather files are not loading (log, time-of-day mode, install route), and
   no value will help until that is fixed.
2. `cloudMap.procedural.parameters.coverageGain.range` z and w together, 1.0 down to 0.7 then 0.5. Fewer and
   smaller clouds. This is the bluntest control and the first to use.
3. `...primary.range.x` (input minimum) from 0.3 up to 0.5. Shrinks the cloudy area without changing cloud size.
4. `cloudLayer.lighting.sunExtinction` from 0.6 down to 0.4. Lighter shadow under the clouds that remain.
5. `cloudLayer.low.densityScale` from 0.35 down to 0.25. Thinner, more translucent clouds.
6. `cloudLayer.cirrus.densityScale` to 0. If the scene brightens, the cirrus sheet was the cause.
7. Only if SClearSkyPF with no cloud at all is still darker than with the feature off: the cause is not coverage.
   Look at `sunlightColor` (yours is 7, default 10) and report it; that is an atmosphere question, not a cloud one.

### A clear day is grey or hazy at distance but the ground is sunlit

Raise `cloudLayer.low.ndfAltitudeOffset` (1300 to 1800) and check `rayMarchRange`. Cloud between the camera and
the mountains is the likely cause.

### Shimmer is still there

1. Note whether it is on grass against cloud, in the fog band, or in the shadow patches.
2. Baseline `marchStepScale` 0.5 to 0.25. If it falls a lot, the cause is march noise; then try 0.5 with
   `cloudBlurRadius` 2 as the cheaper fix.
3. Baseline `shadowVolumeRange` 8 to 4. If the shimmer on lit grass changes scale or moves closer, it is the
   shadow volume.
4. In FogPF only: raise `ndfAltitudeOffset` from 600 to 900. If it goes, the low deck was intersecting terrain.
5. If none of these moves it, switch volumetric clouds off and confirm it disappears, then report where it sits.

### A storm is too thin

1. `...primary.range.z` (coverage floor) from 0.6 up to 0.75, and `secondary.range.z` from 0.45 to 0.6. Closes
   the gaps: with a floor at or above 0.7 the deck is solid everywhere.
2. `cloudLayer.low.densityScale` from 0.9 to 1.0 (the maximum).
3. `cloudLayer.lighting.sunExtinction` from 1.25 up to 1.6 or 2.0. Darker bases and darker ground.
4. `cloudLayer.low.ndfAltitudeScale` from 2600 to 3500. A deeper cloud is darker underneath, at a march cost.
5. `cloudLayer.lighting.ambientStrength` from 1.0 down to 0.6. Removes the light that fills the bases.
6. `cloudLayer.lighting.brightness` from 0.9 down to 0.7, last, since it dims the whole cloud including lit edges.

### A storm or overcast is too dark (black ground, crushed shadows)

The reverse, starting with `sunExtinction` (down to 0.8) and `ambientStrength` (up to 1.5). Remember your Look
Grade entries per weather were tuned with vanilla clouds and no cloud shadow, so storm weathers may now be
darkened twice: once by the grade and once by the shadow. If so, it is the grade that should give way.

### Clouds look wrong in shape

Too blobby or too uniform: `...primary.frequency` (1 to 2) and `...primary.exponent` (1.4 to 2). Clouds too large
or a visible repeat: `cloudLayer.low.ndfScale` (16 km default). I have not set these per group.

### Too slow

Swap in `draft\baseline-variants\performance\PhysicalSky.json`. If storms alone are slow, reduce the storm group's
`ndfAltitudeScale` (2600 to 1800) before touching the march.

## 4. What to write down

For each of the eight weathers: clear or not, sky fraction by eye, darkest and brightest ground compared with the
feature off, shimmer yes or no and where, frame time. That is enough to correct the group table in one pass.
