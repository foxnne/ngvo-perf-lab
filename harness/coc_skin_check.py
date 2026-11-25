"""Black arms/hands on a character that skipped the character creator (user 2026-11-25): start the game to the main
menu, `coc riverwood` from there (a fresh default character), then read what the player's body pieces are drawn
with (testbed inspect_actor: textures, loaded state, skin tint colour). Writes results/skin/coc_<time>.json.
usage: python coc_skin_check.py [cell=riverwood]"""
import json, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs, shots
CELL = sys.argv[1] if len(sys.argv) > 1 else 'riverwood'
OUT = os.path.join(shots.ROOT, 'results', 'skin'); os.makedirs(OUT, exist_ok=True)

if bench.running(): sys.exit('game already running')
if bench.mo2_running(): bench.close_mo2()
subprocess.Popen(['explorer.exe', os.path.join(HERE, 'launch-ngvo.lnk').replace('/', chr(92))])
t0 = time.time()
while time.time() - t0 < 120 and not bench.running(): time.sleep(3)
if not bench.running(): sys.exit('game did not start')
while time.time() - t0 < 600:
    try:
        if 'Main Menu' in cs.call('menu', {'action': 'list'})['openMenus']: break
    except Exception: pass
    time.sleep(5)
print('main menu after %.0f s' % (time.time() - t0), flush=True)
time.sleep(25)
bench.console('coc ' + CELL); print('coc', CELL, flush=True)
time.sleep(15)
if not bench.settle(maxwait=240): sys.exit('cell did not load')
time.sleep(8)


def pieces(tag):
    r = cs.call('communityshaders.testbed', {'action': 'inspect_actor', 'actor': 'player'})
    json.dump(r, open(os.path.join(OUT, 'coc_%s_%s.json' % (time.strftime('%H%M%S'), tag)), 'w'), indent=1)
    print('\n== %s: %s %s, %d pieces' % (tag, r.get('actor'), r.get('formID'), len(r.get('pieces', []))))
    for p in r.get('pieces', []):
        if p.get('feature') in (4, 5) or any(k in p.get('name', '').lower() for k in ('body', 'hand', 'feet', 'head')):
            d = p.get('diffuse') or {}
            print('  %-40s cull=%s feat=%s tint=%s diffuse=%s loaded=%s' % (p['name'][:40], p.get('culled'), p.get('feature'),
                  p.get('tintColor'), (d.get('name') or '')[-45:], d.get('loaded')))


pieces('after_coc')
# The default coc character wears armour, helmet, gloves and boots: undress to see the arms and hands.
bench.console('player.unequipall'); time.sleep(4)
pieces('unequipped')
bench.console('tm'); time.sleep(1)
shot = os.path.join(OUT, 'coc_%s_unequipped.png' % time.strftime('%H%M%S'))
subprocess.run([r'C:\Users\foxnn\dev\ffmpeg.exe', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i',
                'ddagrab=output_idx=0:framerate=5:output_fmt=16bit', '-vf',
                'hwdownload,format=rgbaf16le,zscale=transferin=linear:primariesin=709:matrixin=gbr:rangein=full:npl=100:'
                'transfer=iec61966-2-1:primaries=709:matrix=gbr:range=full,format=rgb24', '-frames:v', '1', shot])
bench.console('tm')
print('screenshot:', shot)
cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
