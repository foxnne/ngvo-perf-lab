# Mod updates installed — NGVO 8.0 Beta (profile foxnne-nsfw) — 2026-11-25

Follow-up to `MODLIST-UPDATE-AUDIT-2026-11-25.md` §1a. All nine "Act now" updates were installed. Game and MO2
were closed throughout (checked before downloading and again right before the copy step); nothing was launched.
Mod folder names are unchanged, so the profile (`modlist.txt`, `plugins.txt`) was **not** edited. No plugin
(.esp/.esl) name changed; no new requirements appeared.

Runtime: Skyrim SE 1.6.1170, SKSE 2.2.6, Address Library v11. Every installed DLL was checked by reading its
`SKSEPlugin_Version` export (declared compatible runtimes / version-independence flags) and its PE build
timestamp, in addition to the Nexus file description and changelog.

Backups (whole mod folders, taken before any change): `C:\Modlists\backups\mod-updates-20261125\<folder name>\`
(177 MB total). To roll a mod back, delete the mod folder and copy the backup folder back under
`C:\Modlists\NGVO 8.0 Beta\mods\`.

Downloads (kept): `C:\Modlists\NGVO 8.0 Beta\downloads\`. Extracted copies: session scratchpad
`...\scratchpad\updates\<mod>\` (disposable).

## Summary table

| # | Mod (folder) | Old -> new | File chosen (Nexus id, size) | 1.6.1170 evidence | Files changed |
|---|---|---|---|---|---|
| 1 | Animation Injector | 1.0.8 -> **1.0.9** | `Animation Injector 197945 1.0.9 2026-11-24T09-36Z HZCMOrMpk.zip` (844334, 1.7 MB) | NG build: flags AddressLibraryPostAE + NoStructUse, no fixed version list, page lists "Skyrim SE/AE"; built 2026-11-24 | dll, ini, 5 docs replaced; licence files reorganised |
| 2 | Dynamic Dodge Shot | 1.6.0 -> **1.6.1** | `Dynamic Dodge Shot 114101 1.6.1 2026-11-15T22-08Z pQ0AZWQyO.zip` (839492, 0.2 MB) | No DLL (XML + hkx + esp); only the XML changed | 1 file |
| 3 | powerofthree's Tweaks | 1.16.0 -> **1.18.0** | `powerofthree's Tweaks 51073 1.18.0 2026-11-15T21-52Z UK35XqKaq.7z` (839485, 8.2 MB), FOMOD option **AE1170** | AE1170 DLL declares `compatibleVersions=[1.6.1170]`, `seVersionRequired=2.2.5`; file desc "Supports SE/AE 1.6.1170" | dll, pdb |
| 4 | powerofthree's Papyrus Extender | 6.4.3 (meta said 6.4.2) -> **6.5.2** | `Papyrus Extender 22854 6.5.2 2026-09-05T12-53Z Sx9oEwOl7.7z` (800720, 14.6 MB), FOMOD option **AE1170** | AE1170 DLL declares `compatibleVersions=[1.6.1170]`, `seVersionRequired=2.2.5`; changelog 6.5.0 drops only 1.6.640 | dll, pdb, PO3_SKSEFunctions.pex/.psc |
| 5 | Container Distribution Framework | 3.1.0 -> **3.1.4** | `Container Distribution Framework 120152 3.1.4 2026-10-24T04-57Z 9LMpgbfIm.zip` (825172, 6.5 MB; Steam build, not the GOG one) | NG flags AddressLibraryPostAE + StructsPost629 (same as the working 3.1.0); mod page (current): "requires Skyrim SE 1.6.1130+"; built 2026-10-24 | dll, pdb, ini (format only) |
| 6 | moreHUD SE | 5.4.6.0 -> **5.4.7.0** | `moreHUD Light Master - SE and AE 12688 5.4.7.0 2026-10-14T00-45Z tSBIcEJz3.7z` (819873, 4.7 MB; ESL variant, matching the installed one) | NG flags AddressLibraryPostAE + NoStructUse (same as 5.4.6); file desc "for both SE and AE" | bsa, dll, pdb; esl byte-identical |
| 7 | STB Widgets | 2.7 -> **3.0** | `STB Widgets 136148 3.0 2026-09-02T14-16Z FpnkHZYxp.7z` (799208, 3.9 MB), FOMOD options **Core + 16x9** | NG flags AddressLibraryPostAE + NoStructUse, no fixed version list (2.7 build declared the same flags); page "Works on Skyrim SE and AE"; DLL built 2026-09-02 13:11 UTC (= the 3.0 upload) | dll, pdb; swfs + ini identical |
| 8 | Widescreen Scale Removed for 1-6-1130 and higher | 1.0.4 -> **1.1.1** | `Widescreen Scale Removed 136793 1.1.1 2026-11-08T14-10Z 8gJHTO63D.7z` (834620, 3.7 MB) | NG flags AddressLibraryPostAE + StructsPost629; mod page lists "AE: 1.6.1130, 1.6.1170, 1.6.1179, 1.7.99, 1.7.104"; built 2026-11-08 | dll, pdb, ini (newline only) |
| 9 | Barter Limit Fix | d2025.1.9 (2022-09 DLL, v0.0.0.1) -> **1.0.2** | `Barter Limit Fix 77173 1.0.2 2026-09-03T14-58Z HZCMOyQKb.7z` (799756, 10.6 MB), FOMOD option **AE1170** | AE1170 DLL declares `compatibleVersions=[1.6.1170]`, `seVersionRequired=2.2.5`; changelog 1.0.2 "Fix 1.6.1170 dll package error" | dll, pdb |

Nothing was skipped. The alternative FOMOD folders (`AE` = 1.7.104-only, `seVersionRequired 2.3.0`; `SE` = 1.5.97)
were inspected and deliberately **not** installed.

## Per-mod detail

### 1. Animation Injector (197945) 1.0.8 -> 1.0.9
- Folder: `mods\Animation Injector`. Backup: `C:\Modlists\backups\mod-updates-20261125\Animation Injector\`.
- Replaced: `SKSE\Plugins\AnimationInjector.dll` (3,372,032 -> 3,887,104 B; FileVersion 1.0.9.0),
  `SKSE\Plugins\AnimationInjector.ini`, `AnimationInjector_README.md`, `AnimationInjector_README_EN.md`,
  `AnimationInjector_XML_GUIDE.md`, `AnimationInjector_XML_GUIDE_EN.md`, `AnimationInjector_SOURCE.txt`.
- Added: `AnimationInjector_LICENSE\LICENSE.txt`, `AnimationInjector_LICENSE\THIRD_PARTY_NOTICES.txt`.
- Removed (old payload replaced by the folder above): `AnimationInjector_LICENSE.txt`, `AnimationInjector_licenses\` (10 txt files).
- Unchanged: `Interface\AnimationInjectorLoading.swf` (byte-identical, 31 B stub in both versions).
- **INI merge**: diffed old vs new `AnimationInjector.ini` — every existing key has the same value (the installed
  INI was at defaults, as the audit noted); 1.0.9 only adds `[Display] iLadderToggleKey = 0`. Installing the new
  INI therefore preserves all values. Old INI is in the backup.
- The two settings the audit suggested as workarounds (`bLoadingProgress`, `bOrdinary`) were left at their
  defaults (true/true) so the 1.0.9 fix for the stuck loading panel can be observed; the new log will say why the
  panel stopped waiting if it times out (20 s).

### 2. Dynamic Dodge Shot (114101) 1.6.0 -> 1.6.1
- Folder: `mods\Dynamic Dodge Shot`. Backup: `...\mod-updates-20261125\Dynamic Dodge Shot\`.
- Replaced: `SKSE\Plugins\AnimationInjector\DynamicDodgeShot\DynamicDodgeShot.xml` only — the six
  `firstPerson="switch"` attributes became `otherView="switch"` (the 1.0.8 syntax that caused "unknown attribute
  'firstPerson' — entire file skipped"). `Dynamic Dodge Shot.esp`, the six `.hkx` and `DodgeFX.wav` are byte-identical.
- No INI. Plugin name unchanged (`Dynamic Dodge Shot.esp`, still at line 770 of plugins.txt).

### 3. powerofthree's Tweaks (51073) 1.16.0 -> 1.18.0
- Folder: `mods\powerofthree's Tweaks`. Backup: `...\mod-updates-20261125\powerofthree's Tweaks\`.
- Replaced: `SKSE\Plugins\po3_Tweaks.dll` (1,111,040 -> 1,232,384 B; FileVersion 1.18.0.1), `po3_Tweaks.pdb`.
  `scripts\po3_Tweaks.pex` and `source\scripts\po3_Tweaks.psc` are identical to the shipped `Required` set.
- **INI**: the mod folder does not contain `po3_Tweaks.ini`. The active copy is
  `mods\NGVO - MCM and INI Settings\SKSE\Plugins\po3_Tweaks.ini` (5,162 B; that mod is enabled and higher priority,
  line 123 vs 2252 in modlist.txt). It was **not modified**; a copy was saved to
  `C:\Modlists\backups\mod-updates-20261125\NGVO - MCM and INI Settings\SKSE\Plugins\po3_Tweaks.ini`.
  1.17+ migrates the old key names itself on first launch (changelog 1.17.0: "Existing INI settings will be
  automatically migrated to new style"); the DLL will rewrite the file through the MO2 VFS, i.e. in that settings
  mod (or in overwrite). Check it after the first launch; the backup holds the pre-migration values.
- No new requirements.

### 4. powerofthree's Papyrus Extender (22854) 6.4.3 -> 6.5.2
- Folder: `mods\powerofthree's Papyrus Extender`. Backup: `...\mod-updates-20261125\powerofthree's Papyrus Extender\`.
  (meta.ini said 6.4.2.0 but the installed DLL was FileVersion 6.4.3.1 from the 6.4.3 archive.)
- Replaced: `SKSE\Plugins\po3_PapyrusExtender.dll` (3,209,216 -> 3,072,512 B; FileVersion 6.5.2.1),
  `po3_PapyrusExtender.pdb`, `Scripts\PO3_SKSEFunctions.pex`, `Source\scripts\PO3_SKSEFunctions.psc`
  (new `GetActivePlugins` from 6.5.0). The other 7 pex / 7 psc files are identical.
- No INI, no plugin, no new requirements.

### 5. Container Distribution Framework (120152) 3.1.0 -> 3.1.4
- Folder: `mods\Container Distribution Framework`. Backup: `...\mod-updates-20261125\Container Distribution Framework\`.
- Replaced: `SKSE\Plugins\ContainerDistributionFramework.dll` (FileVersion 3.1.4.0, built 2026-10-24),
  `.pdb`, `.ini`.
- **INI**: old and new both have the single key `fMaxRefLookupDistance = 25000` (old wrote `25000.000000`, new
  `25000.0`, a blank line removed). No user edit existed, so nothing to merge.
- Runtime note: the file description only says "Known working versions: 1.7.99, 1.7.104" (Steam vs GOG split), but
  the mod description states the requirement as "Skyrim SE version 1.6.1130+", and the DLL declares the same
  NG version-independence flags as the 3.1.0 build that has been running on 1.6.1170. The Steam build (825172)
  was chosen, not the GOG one (825171).

### 6. moreHUD SE (12688) 5.4.6.0 -> 5.4.7.0 (Light Master / ESL variant)
- Folder: `mods\moreHUD SE`. Backup: `...\mod-updates-20261125\moreHUD SE\`.
- Replaced: `AHZmoreHUD.bsa` (455,602 -> 455,362 B — the restored 5.4.5 HUD swf), `SKSE\Plugins\AHZmoreHUDPlugin.dll`
  (FileVersion 5.4.7.0), `.pdb`. `AHZmoreHUD.esl` and `LICENSE.txt` are byte-identical — plugin name unchanged
  (`AHZmoreHUD.esl`, line 26 of plugins.txt).
- No INI.

### 7. STB Widgets (136148) 2.7 -> 3.0
- Folder: `mods\STB Widgets`. Backup: `...\mod-updates-20261125\STB Widgets\`.
- The 3.0 archive's inner folder is oddly named `STB Widgets 136148 2.8 ...`, but its DLL is a new build
  (PE timestamp 2026-09-02 13:11 UTC vs the installed 2026-07-09 build; the Nexus upload is 2026-09-02 14:16).
  FileVersion is a constant 1.0.0.0 in both, so the timestamp is the version evidence.
- FOMOD options installed: `1. Core` + `2. 16x9` (what the folder already contained; no SkyHUD / TrueHUD options
  were present before, none added).
- Replaced: `SKSE\Plugins\STB_Widgets.dll` (1,141,248 -> 1,142,784 B), `.pdb`. All 8 `interface\*.swf` and the
  16x9 `STB_Widgets.ini` are byte-identical to the installed ones.
- **INI**: the mod folder's `STB_Widgets.ini` was the stock 16x9 file (identical to new). The user's actual
  widget layout comes from `mods\[NO DELETE] Dragonborn UI Preset - Foxnne\SKSE\Plugins\STB_Widgets.ini`
  (higher priority, untouched).
- Runtime: changelog 2.9 says "Updated for 1.7.99" (added), nothing says 1.6.x was dropped; mod page says
  "Works on Skyrim SE and AE"; DLL declares AddressLibraryPostAE + NoStructUse with an empty fixed-version list
  (same scheme as the 2.7 build that runs today). Treat the first launch as the confirmation.

### 8. Widescreen Scale Removed (136793) 1.0.4 -> 1.1.1
- Folder: `mods\Widescreen Scale Removed for 1-6-1130 and higher`. Backup: `...\mod-updates-20261125\Widescreen Scale Removed for 1-6-1130 and higher\`.
- NG build exists: single DLL, mod page explicitly lists 1.6.1170 among supported AE versions.
- Replaced: `SKSE\Plugins\WidescreenScaleRemoved.dll` (618,496 -> 690,176 B; FileVersion 1.1.1.0), `.pdb`,
  `.ini` (content identical `[Debug] EnableDebugLog = false`; new file has a trailing newline).

### 9. Barter Limit Fix (77173) d2025.1.9 -> 1.0.2
- Folder: `mods\Barter Limit Fix`. Backup: `...\mod-updates-20261125\Barter Limit Fix\`.
- The installed DLL was the 2022-09-01 build (plugin version 0.0.0.1, 235 KB, CommonLibSSE by KernalsEgg & po3).
- FOMOD option installed: `AE1170`. Replaced: `SKSE\Plugins\BarterLimitFix.dll` (235,520 -> 846,336 B;
  FileVersion 1.0.1.1, declares 1.6.1170 / SKSE >= 2.2.5), `.pdb` (4.1 -> 23.2 MB).
- Left alone: `SKSE\Plugins\BarterLimitFix.log` (81 B stale log that sat in the mod folder; not shipped by the mod).
- No INI.

## meta.ini updates
For all nine: `version` and `newestVersion` set to the new version, `installationFile` set to the downloaded
archive name, `[installedFiles] 1\fileid` set to the Nexus file id (modid unchanged). Verified after writing.

## What to check on the first launch
1. SKSE log `skse64.log`: all nine DLLs load, no "disabled, incompatible with current runtime" lines
   (STB_Widgets, ContainerDistributionFramework, WidescreenScaleRemoved are the three whose runtime support rests
   on NG flags + page text rather than an explicit 1.6.1170 build).
2. `AnimationInjector.log`: `DynamicDodgeShot.xml` now parses (no "unknown attribute"), and the loading panel
   hides after a save load (or logs why it stopped waiting).
3. `po3_Tweaks.ini` in `NGVO - MCM and INI Settings` (or `overwrite`): migrated key names, values still yours.
4. No plugin order / Synthesis re-run needed: no .esp/.esl changed.

## Tooling left in the session scratchpad (disposable)
`...\scratchpad\tools\skse_verdata.py` (reads SKSEPlugin_Version data from a DLL), `pe_stamp.py`,
`nexus_info.py`, `nexus_moddesc.py`, `install_updates.py` (the copy/meta plan actually executed; supports `--dry`).
