"""Queue job: apply a CINEMACAM preset as if loaded on its Presets page (all pages it holds), game closed.
Copies every key of the preset into the live overwrite/SKSE/Plugins/Cinemacam.ini; sections and keys the preset does
not hold (General, hotkeys) are kept. Backup next to it. usage: python cinemacam_preset_job.py TAG PRESET.ini"""
import configparser, os, shutil, sys, time
TAG, PRESET = sys.argv[1], sys.argv[2]
LIVE = r'C:\Modlists\NGVO 8.0 Beta\overwrite\SKSE\Plugins\Cinemacam.ini'
def rd(p):
    c = configparser.RawConfigParser(strict=False); c.optionxform = str; c.read(p, encoding='utf-8-sig'); return c
a, b = rd(PRESET), rd(LIVE)
shutil.copy2(LIVE, LIVE + '.bak-pre-' + TAG + '-' + time.strftime('%Y%m%d'))
n = 0
for s in a.sections():
    if not b.has_section(s): b.add_section(s)
    for k, v in a[s].items():
        if b[s].get(k) != v: b[s][k] = v; n += 1
with open(LIVE, 'w', encoding='utf-8') as f: b.write(f, space_around_delimiters=False)
print('applied', os.path.basename(PRESET), n, 'values changed', flush=True)
