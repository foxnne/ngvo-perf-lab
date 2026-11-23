"""Queue job (game closed): make aspens use DynDOLOD's own 3D tree LOD (passthru, built from the full model like the pines)
instead of the Aspens Ablaze _LOD_N.nif meshes, whose textures\\mx LOD textures render dark and high-contrast.
Moves the 18 aspen LOD meshes to C:/Modlists/backups/aspen-lod-meshes-20261121 and removes the aspen billboard rule
(restores the High rules file and the preset from their pre-aspen backups).  usage: python aspen_lod_passthru.py [undo]"""
import os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
if bench.running(): sys.exit('game open')
bench.close_mo2()
I = 'C:/Modlists/NGVO 8.0 Beta'; MOD = I + '/mods/Aspens Ablaze - Big Autumnal 2K (foxnne)/meshes/landscape/trees'
BK = 'C:/Modlists/backups/aspen-lod-meshes-20261121'
DD = I + '/tools/DynDOLOD/Edit Scripts/DynDOLOD'
RULES = DD + '/Rules/DynDOLOD_SSE_High.ini'; PRESET = DD + '/Presets/DynDOLOD_SSE_Default.ini'
undo = len(sys.argv) > 1 and sys.argv[1] == 'undo'
if not undo:
    os.makedirs(BK, exist_ok=True)
    n = 0
    for f in os.listdir(MOD):
        if f.lower().startswith('treeaspen') and '_lod_' in f.lower():
            shutil.move(os.path.join(MOD, f), os.path.join(BK, f)); n += 1
    print('moved', n, 'aspen LOD meshes to', BK)
    shutil.copy2(RULES, RULES + '.bak-aspenbillboard-20261121')
    shutil.copy2(RULES + '.bak-pre-aspenbillboard-20261121', RULES)
    shutil.copy2(PRESET, PRESET + '.bak-aspenbillboard-20261121')
    shutil.copy2(PRESET + '.bak-dynregen-20261121', PRESET)
    print('aspen billboard rule removed from rules + preset')
else:
    for f in os.listdir(BK):
        shutil.move(os.path.join(BK, f), os.path.join(MOD, f))
    print('aspen LOD meshes restored')
