# look

Material behind the current NGVO look, kept here as a backup and for anyone who wants to reuse it.

- `settings/SettingsUser.json`: the saved Community Shaders settings (the look itself) for the fork at
  https://github.com/foxnne/skyrim-community-shaders, branch `foxnne/llf-shadowless-spots`.
- `settings/dyndolod_added_rules.txt`: lines added to DynDOLOD's `Rules/DynDOLOD_SSE_High.ini` before the `tree` rule
  (giant Whiterun tree never fades; the large Nature of the Wild Lands trees keep 3D LOD at every level).
- `steps/`: variant files for `harness/look_step.py` (exposure, highlight roll-off, sky, shadow depth).
- `suki-analysis/`: notes and scripts from studying the Suki ENB look as a target.
- `bake_suki.py`: LUT bake experiment.

Cloud drafts live in `tools/nat3-volclouds`, tree LOD tools in `tools/no-ivy-trees`, the grass colour map and terrain
LOD tint scripts in `tools/grass-colour-map`. Reference images from other people's setups, generated textures and
meshes derived from mod assets are not included.
