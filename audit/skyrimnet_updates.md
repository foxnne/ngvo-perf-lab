# SkyrimNet ecosystem update check (2026-11-17, profile foxnne-nsfw, read-only)

## Versions

| Mod (enabled folder) | Installed | Latest (date) | Newer? | Source / exact file |
|---|---|---|---|---|
| SkyrimNet 1.2.0-rc2 | 1.2.0-rc2 (GitHub) | 1.2.0 (11-17) | YES | Nexus 198346 file 840262 `Skyrimnet 1.2.0 198346 1.2.0 2026-11-17T06-59Z 8gJHTOghH.zip`, 243,650,114 B - already in downloads; byte-size identical to GitHub `v1.2.0-rc3` asset |
| OStimNet for SkyrimNet 2.6.2 | 2.6.2 | 2.7.1 GitHub (11-17 17:04Z); Nexus still 2.7.0 | YES | GitHub tetherball88/OStimNet `OStimNet_v2.7.1.zip` 2,009,380 B https://github.com/tetherball88/OStimNet/releases/download/v2.7.1/OStimNet_v2.7.1.zip (Nexus 169603 file 840153 = 2.7.0, 1954 KB - skip) |
| OStim Navigator 2.3.0 (ships SkyrimNet prompts) | 2.3.0 | 2.4.0 (11-15) | YES | GitHub tetherball88/OStimNavigator `OStimNavigator_v2.4.0.zip` 3,265,869 B |
| NarrativeEngine | 0.9.2 | 0.10.0 (11-15) | YES | GitHub pdusen/skyrimnet-plugin-narrative-engine `NarrativeEngine-v0.10.0.zip` 2,116,738 B |
| BodyLanguage 2.1.1 | 2.1.1 | 2.2.2 (11-12) | YES | Nexus 198353 file 837054 `BodyLanguage 198353 2.2.2 ...Ks18nTAwy.zip` 1,026,323 B - already in downloads |
| Phantasm (standalone) | 1.0.0 | 1.2.0 (11-14) | YES* | Nexus 197470 file 838283 `Phantasm 1.2.0 197470 1.2.0 2026-11-14T00-29Z oPpNfLPhM.zip` 1424 KB |
| SeverActions 4.9.0 | 4.9.0 | 4.9.0 (11-15) | no | GitHub Severause/SeverActions |
| IntelEngine 3.8.2 | 3.8.2 | 3.8.2 (11-14) | no | GitHub galanx/IntelEngine-GamePlugin |
| DragonSense 0.5.0 | 0.5.0 | 0.5.0 (11-12) | no | GitHub nan0bug00/DragonSense |
| Battle Summaries 1.5.0 | 1.5.0 | 1.5.0 (11-03) | no | GitHub urtubesrclogged/BattleSummaries |
| PlayerSignals 0.2.1 | 0.2.1 | 0.2.1 (11-04) | no | GitHub Gerkinfeltser/PlayerSignals |
| Physical Letters 1.1.1 / Ink and Quill 0.2.0 | same | 1.1.1 / 0.2.0 | no | GitHub zevck/Physical-Letters, zevck/Ink-and-Quill |
| Hypnosis 1.2.0 | 1.2.0 | 1.2.0 (10-24) | no | Nexus 194797 |
| Magelight UI | 1.9.0 | 1.9.0 | no | Nexus 193303 |
| Lastwords / Walk With Me (+Gestures) / Papyrus MessageBox | 1.7.0 / 0.3.1 / 1.0.0 | same | no | Nexus 197972 / 191283 / 83578 |
| OStimNet and Drago Sanguine PPA Patches | "1.0" | per-pack files from 2026-07, none newer | no | Nexus 184264 (which packs were installed: not verified) |
| OMind 0.8.0 | 0.8.0 | UNVERIFIED | ? | no source in meta.ini/readme, not in SkyrimNet plugin registry or GitHub search |
| STAE Sitcom Prompts, foxnne Follower Bios | local | n/a | no | local content, already in 1.2 overlay layout |

*Phantasm: SeverActions 4.9.0 (higher priority) already bundles Phantasm.dll 1.2.0 and Magelight 1.9.0 and wins the conflict, so 1.2.0 is what actually loads; the standalone folder is just stale.

## Install plan (MO2 and game closed)
1. SkyrimNet: install file 840262 as new folder `SkyrimNet 1.2.0` at the same priority slot as `SkyrimNet 1.2.0-rc2`, enable it, disable rc2. Do not touch `overwrite\SKSE\Plugins\SkyrimNet\`.
2. OStimNet: new folder `OStimNet for SkyrimNet 2.7.1` from GitHub, disable 2.6.2.
3. OStim Navigator: new folder `OStim Navigator 2.4.0`, disable 2.3.0.
4. NarrativeEngine: new folder `NarrativeEngine 0.10.0` (fresh folder/Replace, never Merge), disable old.
5. BodyLanguage: new folder `BodyLanguage 2.2.2` from the archive in downloads, disable 2.1.1; re-apply any BodyLanguage.ini edits.
6. Phantasm: replace standalone with 1.2.0 (or disable it; SeverActions' copy is in use). Keep `SeverActions 4.9.0\SKSE\Plugins\Phantasm.ini` (edited 11-16).

## Must preserve in overwrite\SKSE\Plugins\SkyrimNet\
`config\` (all *.yaml incl. Providers/Hotkey/OpenRouter, `plugins\` for BattleSummaries, Hypnosis, IntelEngine, NarrativeEngine, OStimNet, SeverActions, `overrides\`, `model_presets\`, `voice_cache\`, `.library-migrated`), `overlay\` (currently only `_history\prompts`), `data\` (per-save .db memory databases + bard_songs), `voices\`, `models\`, `saves\`, `content-registry.json`. Also `overwrite\SKSE\Plugins\IntelEngine`, `PhysicalLetters`, `MCM\Settings\PhysicalLetters.ini`.

## Changelog warnings
- SkyrimNet 1.2.0 final vs rc2: release notes are the same feature set (PocketTTS GGUF/GPU, Magelight wheel on F12, `minion` and `vampire_feed` events, fixes); no prompt/overlay layout change, no clean-save or config-reset instruction. CUDA GPU paths (PocketTTS and Whisper) now need CUDA 13.5, otherwise silent fallback to Vulkan/CPU. Old `models/pocket_tts` may be deleted; cloned voices regenerate once per model. New over-head subtitle defaults are offered, not forced.
- No addon states "requires SkyrimNet 1.2.0". IntelEngine says "Requires SkyrimNet Beta 27 or newer".
- OStimNet 2.7.0 crashes to desktop when a scene ends on AE 1.6.x (incl. 1.6.1170); fixed in 2.7.1 - do not install the Nexus 2.7.0 file. 2.7.0+ replaces the UIExtensions requirement with Magelight UI (present, 1.9.0).
- OStim Navigator 2.4.0 moved from PrismaUI to Magelight UI (both installed).
- NarrativeEngine 0.10.0: upgrading from 0.9.x discards in-progress plots, combat/travel event history and the Director decision log in the save (format change). 0.9.2 note: Replace, not Merge.
- BodyLanguage 2.2.x: new `[Exclusions]` section in BodyLanguage.ini, new BeastParts.json; child NPCs excluded.
- SeverActions 4.9.0 bundles Magelight UI 1.9.0 + Phantasm 1.2.0: "let the newer copy win".

Not verified: OMind source/latest; Nexus changelog text for Phantasm 1.1.x; whether Nexus will post OStimNet 2.7.1.
