# BTPS and Floating Subtitles: lag, jitter, off-centre prompt and overlap

Read-only audit, 2026-11-17. Profile `foxnne-nsfw`. Nothing was changed; the game and MO2 were not touched.
Nothing here was measured in the running game; each claim is marked **evidence** (read in a file, log or source) or **inference**.

## Summary

1. **The off-centre BTPS prompt and most of the overlap come from a saved HUD NG offset on the BTPS prompt** (evidence). HUD NG shifts it about 54 px left and 80 px up at 3440x1440 and shrinks it to 81%. Floating Subtitles stacks its text just above where BTPS *thinks* its prompt is, so the shifted prompt lands on the subtitle.
2. **BTPS does supply the subtitle anchor height for the selected NPC** (evidence, confirmed integration). It is only the height (world Z), only for the NPC BTPS currently selects, and it does not include the HUD NG shift.
3. **The lag/jitter while turning has two causes** that the settings cannot remove:
   - Frame generation composites one UI image onto both the real and the generated frame, so 3D-tracked UI updates at about 40 Hz over a world moving at about 80 Hz (evidence in the fork source).
   - BTPS additionally positions its prompt with the previous frame's camera matrix, one real frame (about 25 ms) late (source evidence for what it reads; inference for the frame ordering).
4. The two widgets disagree with each other by about one real frame during a turn, which is probably part of what looks like "fighting"; the rest is the subtitle jumping height and losing its name line whenever BTPS selection toggles.

## 1. Installed versions and config

### Better Third Person Selection

| Item | Value |
|---|---|
| Mod folder | `mods\Better Third Person Selection - BTPS` (enabled, modlist line 1900) |
| Version | 0.8.9.0 (`meta.ini`, Nexus 64339); 0.9.0 is available |
| DLL | `SKSE\Plugins\BetterThirdPersonSelection.dll` (2025-06-07) |
| Widget SWF in use | `Interface\BetterThirdPersonSelection\BTPS_menu.swf` from `Dragonborn UI - SkyUI Reskin - 21x9` (enabled, line 1849), which overrides BTPS's own |
| Defaults | `mods\Better Third Person Selection - BTPS\MCM\config\BetterThirdPersonSelection\settings.ini` |
| User overrides | `mods\foxnne - carried-over settings\MCM\Settings\BetterThirdPersonSelection.ini` (line 18, wins) |
| Other files | `...\Filters\FilterPresets*.toml`, `...\Overrides\Overrides*.toml` (ignore list is empty), `overwrite\MCM\Settings\FilterStates.json` (all four filters off) |

There is no BTPS ini/json under `SKSE\Plugins`, and nothing for BTPS in `overwrite\MCM\Settings` apart from `FilterStates.json`.

Effective values (user override where present, otherwise default):

| Setting (`[Widgets]` unless noted) | Effective | Default | Meaning |
|---|---|---|---|
| `fWidgetZOffset` | 12.0 (user) | 30.0 | World units above the head node (third person) |
| `fWidgetZOffsetFirstPerson` | 5.0 | 5.0 | Same, first person |
| `fWidgetZOffsetAdditionalNPC` | 0.0 | 0.0 | Extra height for NPCs only |
| `fWidgetSizeMin` / `fWidgetSizeMax` | 0.2 / 0.8 (user) | 0.3 / 0.9 | Distance-based scale range |
| `fWidget2DSize`, `fWidget2DXPos`, `fWidget2DYPos` | 1.0, 0.5, 0.35 | same | 2D fallback prompt |
| `fWidgetFadeInDelta` / `fWidgetFadeOutDelta` | 0.05 / 0.05 | same | Alpha step per UI frame (frame-rate dependent: 20 frames = 0.5 s at 40 fps) |
| `bIsWidget3DEnabledInThirdPerson` | 1 | 1 | 3D-tracked prompt |
| `bIsWidget3DEnabledInFirstPerson` | 0 (user) | 0 | |
| `[General] bIsEnabledInFirstPerson` | 1 (user) | 0 | |
| `[General] bEnableFiltersForNativeSelection` | 1 (user) | 0 | |
| `[General] fMaxInteractionRange` | 200.0 | 200.0 | Selection distance limit |
| `[General] fMaxAngleDif` | 0.5 | 0.5 | Selection cone |
| `[Priority] fNPCSelectionBonus` | 1.5 | 1.5 | |
| `[Priority] fPreviousSelectionBonus` | 0.1 | 0.1 | Stickiness of the current selection |
| `[Performance] iNumTracesHorizontal/Vertical` | 4 / 4 (user) | 3 / 3 | |
| `[Compatibility] bAdjustMoreHudWidgets` | 1 | 1 | |
| `[Compatibility] bAdjustQuickLootWidgets` | 0 | 0 (the `.bak` has 1) | |

BTPS 0.8.9 has **no** setting for position smoothing/lerp, update rate, "hide while NPC is speaking", SmoothCam, Cinemacam, frame generation or upscaling. Its only cross-mod behaviour:
- It hides its prompt on an actor that has a TrueHUD info bar (source: `SelectionWidget::UpdateTDMVisibility`; log shows "compat - found TrueHUD").
- It did not ask the SmoothCam bridge for anything (`SmoothCamBridgeForCinemacam.log` lists no BTPS request).

Log note: `BetterThirdPersonSelection.log` prints "failed to cache GFxObjects" once at 16:42:24 and then "successfully initialized SelectionWidget UI values", so the reskinned SWF is working.

### Floating Subtitles

| Item | Value |
|---|---|
| Mod folder | `mods\Floating Subtitles` (enabled, line 501) |
| Version | 3.3.5.0 (`meta.ini`, Nexus 154424; log: "Floating Subtitles v3.3.5.0", latest) |
| DLL | `SKSE\Plugins\po3_FloatingSubtitles.dll` |
| Defaults | `mods\Floating Subtitles\MCM\Config\FloatingSubtitles\settings.ini` |
| User overrides | `mods\foxnne - carried-over settings\MCM\Settings\FloatingSubtitles.ini` |
| Fonts / styles | `mods\Floating Subtitles\Interface\FloatingSubtitles\fonts.ini`, `styles.ini` (the `Dagger - Floating Subtitles Patch` that also ships these is disabled) |
| Also read by the DLL | BTPS's two ini files, TrueHUD's (`MCM\Config\TrueHUD\settings.ini`, `MCM\Settings\TrueHUD.ini`), `SSEDisplayTweaks.ini` |

Effective `[Settings]`:

| Setting | Effective | Default |
|---|---|---|
| `bGeneralSubtitles` | 1 | 1 |
| `bDialogueSubtitles` | 1 (user) | 0 |
| `bShowSpeakerName` | 1 (user) | 0 |
| `fHeadOffset` | 12.0 (user) | 15.0 |
| `bUseBTPSWidgetPosition` | 1 | 1 |
| `bUseTrueHUDWidgetPosition` | 1 | 1 |
| `bRequireLineOfSight` | 1 | 1 |
| `fObscuredSubtitleOpacity` | 0.35 | 0.35 |
| `bDualSubtitles` | 0 | 0 |
| `iLanguagePrimary` / `iLanguageSecondary` | 2 / 11 (user) | -1 / -1 |
| `iMaxCharactersPerLinePrimary` / `Secondary` | 120 / 120 (user) | 80 / 80 |
| `fSubtitleAlphaPrimary` / `Secondary` | 1.0 / 0.5 | 1.0 / 1.0 |
| `iOffscreenSubtitles` | 1 | 1 |
| `iMaxOffscreenSubtitles` | 2 (user) | 3 |

Notes from the 3.3.5 source (`src/Manager.cpp`, `src/Compatibility.cpp`):
- `fHeadOffset` is multiplied by screen height / 1080 (1.333 here, because Display Tweaks has `BorderlessUpscale = false`), so 12 behaves as 16 world units. The log confirms the same scale on fonts (31 loaded as 41).
- The MCM help line `bRequireLineOfSight` is not what the DLL reads; it reads `bEnableRaycastChecks`, which is absent from the ini, so line-of-sight checks stay on regardless. Minor upstream mismatch.
- Distance limit is the game's `fMaxSubtitleDistance` (log: 1250 start, 1312.5 end of fade). There is no separate subtitle-count limit for on-screen floating subtitles; `iMaxOffscreenSubtitles` only limits the classic bottom-of-screen ones.
- TrueHUD values it uses: `uInfoBarAnchor = 1` (head), `fInfoBarOffsetZ = 30` (from `mods\TrueHUD - HUD Additions\MCM\Config\TrueHUD\settings.ini`; the user's `TrueHUD.ini` does not override them).
- No setting for smoothing, update rate, SmoothCam, Cinemacam, frame generation or upscaling.

### HUD NG (added lead)

| Item | Value |
|---|---|
| Mod folder | `mods\HUD NG` (enabled, line 490), version 1.0.5.0, Nexus 191835 |
| Static config | `mods\HUD NG\SKSE\Plugins\HudNG.ini` (language only) |
| Active layout (runtime-written) | `overwrite\SKSE\Plugins\HudNG\Layout.json` (2026-11-13 11:53), 28 placements, `"activation": "active"` |
| Backups | `overwrite\SKSE\Plugins\HudNG\Layout.stage.42560.51318671.1.0.previous`, `Layout.stage.42560.51448062.2.0.previous` |
| Presets | `overwrite\SKSE\Plugins\HudNG\Presets.json` (one preset, "foxnne") |

**A saved HUD NG entry for the BTPS prompt exists and is being applied** (evidence):

```json
{
  "asset": "BetterThirdPersonSelection/BTPS_menu.swf",
  "hidden": false,
  "id": "btps-prompt",
  "label": "Interaction prompt",
  "menu": "BTPS Menu",
  "path": ["_root", "mc_SelectionWidget"],
  "scale": 0.811791967354744,
  "x": -0.01580614499777666,
  "y": -0.055596803608784356
}
```

`HudNG.log` (today's session) confirms it is live: `item=btps-prompt menu=BTPS Menu resolved=true movable=true drawn=true visible=true hidden=false transformed=true saved=(-0.0158, -0.0556, 0.8118)`.

History of that entry: backup 1 and the "foxnne" preset have x=-0.0038, y=-0.0089, scale=0.679; backup 2 has x=+0.0029, y=-0.127, scale=0.679. So the prompt has been dragged upward at least twice.

Size of the shift (inference on units): the log reports the BTPS stage frame as 1720 x 720 stage pixels. If x/y are fractions of that frame, the offset is about 27 stage px left and 40 stage px up, which is about **54 px left and 80 px up on screen at 1440p**, with the prompt drawn at 81% of BTPS's own size.

Other relevant entries in `Layout.json`:

| id | Target | x | y | scale | Effect on this problem |
|---|---|---|---|---|---|
| `subtitles` | `HUD Menu` `_root.HUDMovieBaseInstance.SubtitleTextHolder` | 0.0091 | 0.0948 | 0.9098 | Vanilla bottom-of-screen subtitles only (used for off-screen speakers). Does not touch the floating ones. |
| `interaction-name` | `RolloverName_mc` | 0.0018 | 0.0067 | 1.4393 | Vanilla activate prompt (BTPS hides it while its own prompt is active) |
| `interaction-divider` | `GrayBarInstance` | 0.0031 | -0.0153 | 1.1685 | Same |
| `interaction-info` | `RolloverInfo_mc` | 0.0032 | -0.0094 | 1.1257 | Same |

There is no crosshair entry and **no Floating Subtitles entry**. HUD NG cannot have one: Floating Subtitles is drawn with its own ImGui pass, not a Scaleform clip (source: `src/ImGui/Renderer.cpp`).

How HUD NG moves things:
- Evidence (config format): every entry names a menu plus a clip `path` inside it, so it adjusts individual clips, not whole movies. For BTPS the clip is `_root.mc_SelectionWidget`, the single clip BTPS itself repositions every frame.
- Evidence (HUD NG README): "BTPS keeps following the selected object. Moving its prompt changes the offset from that moving position; resizing multiplies its usual size." It also keeps the adjusted prompt within the screen edges.
- Conclusion: the prompt still tracks the NPC, but with a constant screen-space offset. A constant pixel offset is a larger world distance the farther the NPC is, which is exactly "not centred over NPCs".

### Other mods checked

- `UI Parallax` 3.0.0 (enabled, `SkyrimHudParallax.dll`, `bEnabled = 1`, sensitivities 0.08): shifts the HUD opposite mouse-look. Its README lists the vanilla HUD movie, SkyUI widgets, TrueHUD, STB widgets and the SKSE Menu Framework layer; "Menus are not directly modified". BTPS is its own menu and Floating Subtitles uses its own ImGui context, so neither should be shifted (inference from the README; the log lists only STB and TrueHUD containers). It does move the classic off-screen subtitles.
- `SmoothCam API Bridge For Cinemacam` 1.0: only relays camera take/return requests. Neither mod uses it.
- `Cinemacam.ini`: nothing HUD-related besides `CinematicHideHud=1`.
- Display: 3440x1440 borderless, `fDefaultWorldFOV=90`, CS `resolutionScale` 0.75, `frameGenerationForceEnable` 1.

## 2. Is BTPS the source of the subtitle anchor? (added lead)

**(a) Confirmed integration, but partial.**

- Floating Subtitles setting: `bUseBTPSWidgetPosition` (= 1 here), MCM file above.
- Source: `src/Compatibility.cpp`, `ModAPIHandler::BTPS::GetWidgetPos`, calls BTPS's API `GetSelectionWidgetPos3D` and keeps only **Z**. Used in `Manager::CalculateSubtitleAnchorPos`.
- Log: `po3_FloatingSubtitles.log` "Retrieving BTPS API... BTPS API is up to date!"; `BetterThirdPersonSelection.log` "API request successful".
- BTPS side: `src/API/BTPS_API.cpp` returns `LastWidgetPos`, the world position computed in `SelectionWidget::Get3DWidgetPos` = head node + `fWidgetZOffset` + `fWidgetZOffsetAdditionalNPC`.

Conditions, all required: the speaker is the current BTPS selection (BTPS writes its selection into the game's crosshair target), BTPS's 3D prompt is enabled, the actor has no TrueHUD info bar (TrueHUD's bar height wins if present), and the NPC is not the dialogue-menu speaker.

Resulting heights above the head node (for a standard-height NPC):

| Case | Subtitle bottom edge | BTPS prompt anchor |
|---|---|---|
| NPC speaking, not selected | 16 units (`fHeadOffset` 12 x 1.333) | none |
| NPC speaking and selected by BTPS | 12 + 0.75 x 16 = 24 units; the speaker-name line is dropped | 12 units (`fWidgetZOffset`) |

What this means for the shared-cause idea:
- `fWidgetZOffset` (BTPS) moves the BTPS prompt and, for the selected speaker, the subtitle with it. It is the one shared setting.
- The HUD NG offset is applied to the drawn clip after BTPS computes its position, and the API reports the unshifted world position. So HUD NG moves the prompt but not the subtitle. That breaks the stacking Floating Subtitles relies on: the gap is only 12 world units (roughly 50 to 90 px at conversation distance, inference), and the prompt has been pushed up about 80 px into it.
- X and Y of the subtitle never come from BTPS; they come from the head node. The sideways shift of the prompt is HUD NG only.

So: one fix (reset the HUD NG entry) addresses the off-centre prompt and most of the overlap. It will not fix the turn lag.

## 3. Causes of lag/jitter when the camera turns, ranked

### Cause 1: one UI image for two presented frames (high confidence)

Evidence, fork source:
- `src\Features\Upscaling.cpp`, `Upscaling::MenuManagerDrawInterfaceStartHook::thunk` calls `Upscaling::PostDisplay`, which calls `HDRDisplay::SetUIBuffer` (`src\Features\HDRDisplay.cpp`). With the D3D12 swap chain and frame generation active, the game's UI render target is redirected to a separate transparent texture, `uiBufferWrapped`.
- `src\Features\Upscaling\FidelityFX.cpp`, `FidelityFX::Present`, registers that texture with `ffx::ConfigureDescFrameGenerationSwapChainRegisterUiResourceDX12` using `FFX_FRAMEGENERATION_UI_COMPOSITION_FLAG_USE_PREMUL_ALPHA | FFX_FRAMEGENERATION_UI_COMPOSITION_FLAG_ENABLE_INTERNAL_UI_DOUBLE_BUFFERING`, with `HUDLessColor` empty.
- `src\Features\Upscaling\DX12SwapChain.cpp`, `DX12SwapChain::Present`, clears the UI texture once per real frame.
- Both widgets land in that texture: BTPS is a Scaleform menu; Floating Subtitles draws ImGui inside `HUDMenu::PostDisplay` to whatever target is bound.

Inference: FSR's swap chain composites the same UI texture onto the generated frame and the real frame. The generated frame shows the world halfway between two real frames but carries the newer frame's UI. A world-anchored label therefore alternates between "right" and "half a real frame of camera motion off", 40 times a second. At a 90 degrees/second turn that is roughly 35 px of alternating error at this resolution. The user's suspicion about the low base frame rate is right: the error scales with real frame time.

Not affected by any setting in either mod.

### Cause 2: BTPS uses last frame's camera (medium-high confidence)

Evidence, BTPS source (GitLab `Shrimperator/skyrim-mod-betterthirdpersonselection`, tag 0.8.8 and `main`; 0.8.9 has no tag):
- Position is set in `SelectionWidgetMenu::AdvanceMovie` -> `SelectionWidget::Update` -> `UpdateWidgetPos`.
- `SelectionWidget::GetScreenLoc` projects with the engine's global world-to-camera matrix (`Offsets::WorldToCamMatrix`, IDs 519579 / 406126) and global viewport.

Inference: menu advance runs in the game update, before the frame is rendered, while that global matrix is written when the scene camera is set up for rendering. So the prompt for frame N is placed with frame N-1's camera, one real frame (about 25 ms) behind, regardless of which camera mod is used. I could not confirm the ordering without a debugger.

Contrast, Floating Subtitles source: it projects in `HUDMenu::PostDisplay` (after the world is rendered) with `RE::Main::WorldRootCamera()->WorldPtToScreenPt3`, so it uses the current frame's camera, including whatever Cinemacam did that frame. It has no camera latency on real frames.

Combined with cause 1: BTPS trails the world by 0.5 to 1 real frame; subtitles are between 0 and 0.5 frame ahead. The two differ from each other by a full real frame while turning, so they visibly slide against each other.

### Cause 3: selection toggling changes the subtitle layout (medium confidence, explains "fighting")

Evidence (`Manager::CalculateSubtitleAnchorPos`, `Manager::Draw`): when the speaker becomes or stops being the BTPS selection, the subtitle jumps between 16 and 24 units above the head and the name line appears or disappears. BTPS selection is re-evaluated continuously from angle and distance, so turning the camera near several NPCs flips it. Inference: this reads as the two widgets pushing each other around. BTPS's fade is 0.5 s at 40 fps, so the prompt lingers while the subtitle has already jumped.

### Ruled out or minor

| Candidate | Finding |
|---|---|
| Built-in smoothing | None in either mod (evidence: no lerp/smoothing code; positions are written directly) |
| Scaleform update rate | BTPS updates every real frame in `AdvanceMovie`; no separate timer (evidence) |
| Render vs display resolution (0.75 scale) | Both use `WorldPtToScreenPt3`, which returns 0..1 screen fractions; BTPS maps onto the menu's visible rect, subtitles onto the full screen size. `Upscaling::PostDisplay` also resets the dynamic-resolution ratios to 1 before UI is drawn (evidence). No mismatch expected; upscaler jitter is sub-pixel (inference) |
| Ultrawide projection | HUD NG's log shows the BTPS stage frame as 1720x720, i.e. the full 21:9 area; subtitles use the true screen size (evidence). No systematic ultrawide error expected, but centring was not checked in game |
| Camera mod updating late | Affects BTPS only through cause 2; subtitles read the camera after it is final |
| UI Parallax | Should not touch either widget (inference from its README) |

## 4. Options

Order: A fixes the off-centre prompt and most overlap; B to D tune separation; E to G concern lag.

### A. Reset the HUD NG adjustment on the BTPS prompt (recommended first)

- In game (preferred, HUD NG owns the file): SKSE Menu Framework > HUD NG > HUD Editor > Edit HUD > select "Interaction prompt - BTPS" > "Reset selected" > "Save & Close". No restart.
- By file, **with Skyrim closed** (HUD NG re-saves and re-applies its layout while running): in `overwrite\SKSE\Plugins\HudNG\Layout.json`, in the entry with `"id": "btps-prompt"`, set `"x": 0.0`, `"y": 0.0`, `"scale": 1.0`, or delete that whole entry object. Keep a copy of the file first.
- Effect: prompt returns to BTPS's own position (centred over the head at `fWidgetZOffset`) and full BTPS size; the subtitle stacking gap works as designed.
- Side effect: the prompt is about 23% larger again. To keep it small without HUD NG, lower BTPS `fWidgetSizeMax` / `fWidgetSizeMin` instead (currently 0.8 / 0.2).
- If the prompt was moved up on purpose, do that with `fWidgetZOffset` instead (option B), because Floating Subtitles follows that value and HUD NG's shift is invisible to it.

### B. Change the shared height: BTPS `fWidgetZOffset`

- File: `mods\foxnne - carried-over settings\MCM\Settings\BetterThirdPersonSelection.ini`, `[Widgets]`, or MCM > Better Third Person Selection. Currently 12.0, default 30.0.
- Effect: moves the prompt and, for the selected speaker, the subtitle together. It does not change the gap between them.
- `fWidgetZOffsetAdditionalNPC` (default 0.0) does the same for NPCs only, leaving items and containers alone.
- Restart: not needed via MCM. A hand edit needs the game closed or a restart to be safe (BTPS re-reads settings while running, but MCM may write its own copy back).

### C. Widen the gap: Floating Subtitles `fHeadOffset`

- File: `mods\foxnne - carried-over settings\MCM\Settings\FloatingSubtitles.ini`, `[Settings]`, or MCM > Floating Subtitles. Currently 12.0.
- Suggested 20.0: selected-speaker gap becomes 0.75 x 20 x 1.333 = 20 units above the prompt anchor (was 12); unselected speakers sit 26.7 units above the head (was 16).
- Side effect: all floating subtitles sit higher, including on NPCs with no prompt.
- Restart: no; the DLL reloads when the MCM closes.

### D. Decouple the two: `bUseBTPSWidgetPosition = 0`

- Same Floating Subtitles file/MCM. Subtitles then always sit `fHeadOffset` above the head and no longer jump when selection toggles (removes cause 3's height jump; the name line still hides for the selected NPC).
- Then separate them by hand: keep the prompt low, for example BTPS `fWidgetZOffset = 5.0`, and subtitles high, `fHeadOffset = 20.0` or more. Nothing then keeps them apart automatically, so tall prompts (item info lines) can still reach the text.
- `bUseTrueHUDWidgetPosition = 1` should stay on so subtitles clear TrueHUD info bars.
- Restart: no.

### Other overlap options the installed versions support

- `bShowSpeakerName = 0` (Floating Subtitles): removes the name line, one line less to collide and no line popping in and out. BTPS already shows the name for the selected NPC.
- BTPS `bIsItemInfoEnabled = 0` and/or `bIsDividerEnabled = 0`: a shorter prompt.
- BTPS `fWidgetFadeOutDelta = 0.2` (and `fWidgetFadeInDelta = 0.2`): prompt clears in about 5 frames instead of 20 when selection changes.
- BTPS `bIsWidget3DEnabledInThirdPerson = 0`: prompt becomes a fixed 2D prompt at `fWidget2DXPos` / `fWidget2DYPos`. This removes BTPS's lag, jitter and overlap completely, and Floating Subtitles then ignores the BTPS position by itself. Cost: the prompt no longer sits on the object.
- Not available in these versions: hiding the BTPS prompt on NPCs that are speaking, per-mod distance limits for the prompt on speakers, any smoothing or prediction.

### E. Lag: update BTPS to 0.9.0

- Changelog (GitLab commits, 2026-09-29 to 10-02) lists flicker and cache-retry fixes and QuickLoot changes. `main` still positions in `AdvanceMovie` with the same global matrix, so **it will not fix the one-frame lag**. Worth doing only for the flicker fixes. Check that the reskinned `BTPS_menu.swf` and HUD NG (whose README names BTPS 0.8.9) still work.

### F. Lag: raise the real frame rate

- Both lag causes scale with real frame time. Going from 40 to 60 real fps cuts the visible error by a third. No setting in either mod substitutes for this.

### G. Lag: test without frame generation

- Turning frame generation off in the Community Shaders menu removes cause 1 entirely (UI and world come from the same frame), leaving only BTPS's one-frame trail. Useful as a diagnostic even if not kept.

## 5. Code fix in the Community Shaders fork

Cause 1 is in how the fork hands UI to FSR frame generation:

- `C:\Users\foxnn\dev\skyrim-community-shaders\src\Features\Upscaling\FidelityFX.cpp`, `FidelityFX::Present`: the `uiConfig` block (`ConfigureDescFrameGenerationSwapChainRegisterUiResourceDX12`) and `configParameters.HUDLessColor = FfxApiResource({})`.
- `C:\Users\foxnn\dev\skyrim-community-shaders\src\Features\HDRDisplay.cpp`, `HDRDisplay::SetUIBuffer` and `GetD3D12UIBufferMode`: the redirect of all UI into `uiBufferWrapped`.
- `C:\Users\foxnn\dev\skyrim-community-shaders\src\Features\Upscaling.cpp`, `Upscaling::MenuManagerDrawInterfaceStartHook::thunk` / `Upscaling::PostDisplay`: where the redirect is triggered.
- `C:\Users\foxnn\dev\skyrim-community-shaders\src\Features\Upscaling\DX12SwapChain.cpp`, `DX12SwapChain::Present`: per-frame clear of the UI texture.

The current design is the standard one and is correct for screen-fixed HUD; it is only wrong for world-anchored UI. What a fix would involve:

1. **Split world-anchored UI from screen-fixed UI.** Render chosen menus (BTPS's `BTPS Menu`, TrueHUD's actor bars, and the ImGui pass Floating Subtitles makes in `HUDMenu::PostDisplay`) into the scene colour before the frame is handed to frame generation, so they are interpolated with the world. This needs a per-menu hook around menu drawing to switch render targets (the fork currently switches once for the whole interface), plus a list of menu names. Cost: interpolation artefacts on text over fast-moving backgrounds, and these widgets would have to be composited in the right colour space when HDR is on.
2. **Or reproject the world-anchored layer for the generated frame.** Keep a second UI texture for those menus and shift it by half the camera rotation delta before composition. FSR's swap chain composites one UI texture for both frames, so this would need the frame-generation `presentCallback` (currently `nullptr` in `FidelityFX::Present`) to do the compositing manually. More work, cleaner text.
3. Either way, `Layout`/menu selection must stay off for pause menus, where the fork already composites UI differently ("When paused, UI is composited in HDROutputCS").

Cause 2 is in BTPS, not the fork: the fix there is to project with the current camera at draw time (as Floating Subtitles does) instead of the global matrix in `AdvanceMovie`. The fork could mask it by option 1 or 2 only partly, since the prompt would still be one frame late.

## 6. Not determined without running the game

- The actual frame ordering behind cause 2 (whether BTPS really is exactly one frame late with Cinemacam).
- Which UI image FSR puts on the generated frame in this build (assumed: the newest one, on both frames).
- The pixel size of the HUD NG shift (computed from an assumed unit) and the sign convention; the direction "up and left" matches the user's description but was not seen.
- How much of the perceived "fighting" is selection toggling versus the one-frame disagreement.
- Whether UI Parallax leaves both widgets alone in practice. Quick check: `bEnabled = 0` in `mods\UI Parallax\SKSE\Plugins\SkyrimHudParallax.ini` or its in-game toggle.
- Whether BTPS 0.9.0 works with the Dragonborn UI reskin SWF and HUD NG 1.0.5.

## Sources

- Floating Subtitles source: https://github.com/powerof3/FloatingSubtitles (tag v3.3.5: `src/Manager.cpp`, `src/Compatibility.cpp`, `src/SettingLoader.h`, `src/ImGui/Renderer.cpp`, `src/ImGui/Util.cpp`, `src/Hooks.cpp`)
- BTPS source: https://gitlab.com/Shrimperator/skyrim-mod-betterthirdpersonselection (tag 0.8.8 and `main`: `src/UI/SelectionWidget.cpp`, `src/API/BTPS_API.cpp`, `src/FocusManager.cpp`, `src/RevE/Offsets.h`, `src/Settings.cpp`)
- HUD NG: `mods\HUD NG\HUD-NG-README.txt`, `HudNG.log`
- UI Parallax: `mods\UI Parallax\README.md`
- Logs: `C:\Users\foxnn\Documents\My Games\Skyrim Special Edition\SKSE\` (`po3_FloatingSubtitles.log`, `BetterThirdPersonSelection.log`, `HudNG.log`, `SmoothCamBridgeForCinemacam.log`, `SkyrimHudParallax.log`)
