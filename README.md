# ngvo-perf-lab

Test harness, tools and notes for a Skyrim SE (1.6.1170) setup built on a personal fork of Community Shaders
(https://github.com/foxnne/skyrim-community-shaders, branch `foxnne/nr-pr6`). Shared as-is for anyone who finds it useful.
It is written for one machine and one modlist: paths are hard-coded and nothing here is a supported product.

- `harness/` - Python scripts that drive a running game through the fork's DevBench bridge: repeatable views, setting
  sweeps with contact sheets (`sky_sweep.py`), benchmarks and frame-cost attribution, a one-at-a-time job queue
  (`queue_runner.py`), build and deploy helpers.
- `audit/`, `docs/` - written findings: lighting integration map, surveys of related renderers, performance notes.
- `configs/` - settings snapshots used by the tests.
- `results/` - small numeric results (CSV/JSON); screenshots and captures are not included.
- `tools/` - offline tools:
  - `nat3-volclouds` - per-weather Physical Sky / volumetric cloud values generated from weather records.
  - `cloud-weather-map` - builds terrain-anchored local cloud maps from a terrain height map (`build_map.py`).
  - `terrain-heightmap` - 16-bit terrain shadow height maps, optionally including mountain/rock objects.
  - `tree-lod-lighting`, `floating-mesh`, `cloud-high-layer` - investigations with their scripts and notes.

Not included: game or mod assets, third-party plugin data, generated textures, the Neural Rendering runtime, API keys.
Outputs derived from other people's mods must be regenerated locally with the scripts.

Code and notes in this repository are under the MIT license. The Community Shaders fork itself is GPL-3.0.
