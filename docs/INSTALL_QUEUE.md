# Install queue (apply only with game AND MO2 closed, after the running suites finish)

Run `python harness/apply_queue.py` (refuses while SkyrimSE, MO2 or a suite is running; `--dry` to preview). It applies:
- Settle 1.0.3 (199431, Main option, AVX) + Settle - FSMP Clothing Clipping Fix Merge (AVX) above Faster HDT-SMP 4.1.1 (AVX build).
  The standalone FSMP Clothing Clipping Fix staged in `C:\Modlists\staging\fsmp-guard-4.1.1` is superseded: do NOT install it.
- Goat's RaceMenu Overlay FPS Helper 1.0.0 (199063): measure city scenario + draw calls before/after; check live overlays still show.
- Dialogue Ducker 1.0.2 (199195).
- Khajiit Warpaints to Face Paints (198747), ESL-flagged esp after VWA_VanillaWarpaintsAbsolution.esp.
- SkyrimNet OmniSight capture back on (user request 2026-11-17); watch a sprint run for the one-frame flash.
Dropped: Camilla replacer 199115 (keep DF Edit). Not now: GPU SMP Physics NG 199175. Skipped: TRX Khajiit Fur 198887 (no TRX addons).
- (added 16:55) Re-enable Combat Pathing Revolution + AE; HUD NG `btps-prompt` back to x 0, y 0, scale 1; Floating Subtitles fHeadOffset 12 -> 20
  (in `mods\foxnne - carried-over settings\MCM\Settings\FloatingSubtitles.ini`). All in apply_queue.py. Test: group fight (enemy spacing, any crash from CPR),
  prompt centred over NPCs, prompt vs subtitle overlap.
