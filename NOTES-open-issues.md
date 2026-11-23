- 2026-11-19 14:15:42: launch crash + hang. Access violation in CommunityShaders.dll+01C8BA8, SceneSettingsManager::SettingEntry::operator= (reading 0x88 past rsi, one byte short of a page end = copying from a freed/short vector element), at data-loaded time right after "[SceneSettings] Registered MenuOpenCloseEventHandler". CrashLogger wrote only the header and the process hung at one core busy; bridge unresponsive. Launch was a bench run with --cs-set (TreeWind NearTrees false). First occurrence; log: SKSE/crash-2026-11-19-14-15-42.log. If it repeats: look for a container of SettingEntry mutated while iterated (scene settings load vs. bridge/feature set at startup).

## 2026-11-19 19:31:48 crash on the first launch after a build (save load)
EXCEPTION_ACCESS_VIOLATION in CommunityShaders.dll State::UpdateSharedData (movss xmm0,[rdx]) while loading preRestart_auri right after
the fog-pool fix build (33266c209) was deployed. The next launches of the same build ran four test jobs without a crash. The launch
after that (b4-warmup) reported NR / frame generation settings as None on the first read. Similar first-launch failure (bridge 504)
after the 19:07 build. Log: Documents/My Games/Skyrim Special Edition/SKSE/crash-2026-11-19-19-31-48.log
Also 17:35:27: SkyrimSE.exe+14EAFFA access violation entering WhiterunBanneredMare during the baseline shoot (interior shots missing).
