"""Game and MO2 closed: switch 'Dismemberment next gen' off and the earlier set back on
(Dismembering Framework + DF - Official Humanoid Asset Pack + Next-Gen Decapitations), plugins at their 2026-11-18 positions.
usage: python dismember_swap.py"""
import os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
if bench.running() or bench.mo2_running(): sys.exit('game or Mod Organizer open')
P = 'C:/Modlists/NGVO 8.0 Beta/profiles/foxnne-nsfw/'; st = time.strftime('%Y%m%d-%H%M')
for f in ('modlist.txt', 'plugins.txt', 'loadorder.txt'): shutil.copy2(P + f, P + f + '.bak-dismember-swap-' + st)


def rd(f):
    raw = open(P + f, 'rb').read(); bom = raw.startswith(b'\xef\xbb\xbf'); t = raw.decode('utf-8-sig'); nl = '\r\n' if '\r\n' in t else '\n'
    return t.split(nl), nl, bom


def wr(f, L, nl, bom): open(P + f, 'wb').write((b'\xef\xbb\xbf' if bom else b'') + nl.join(L).encode('utf-8'))


L, nl, bom = rd('modlist.txt')
want = {'Dismemberment next gen': '-', 'Dismembering Framework': '+', 'Next-Gen Decapitations': '+', 'DF - Official Humanoid Asset Pack': '+'}
seen = set()
for i, l in enumerate(L):
    if l[1:] in want and l[:1] in '+-': L[i] = want[l[1:]] + l[1:]; seen.add(l[1:])
assert seen == set(want), set(want) - seen
wr('modlist.txt', L, nl, bom)
ADD = [('Dismembering Framework.esm', 'DodgeFramework.esl'), ('Next-Gen Decapitations.esp', 'CompleteVanillaEyeOverhaul_CVEObyLDD.esp'), ('DF - Official Humanoid Pack.esp', 'Next-Gen Decapitations.esp')]
for f, star in (('plugins.txt', '*'), ('loadorder.txt', '')):
    L, nl, bom = rd(f)
    L = [l for l in L if l.lstrip('*') != 'Dismemberment.esp']
    for name, after in ADD:
        if any(l.lstrip('*') == name for l in L): continue
        i = next(i for i, l in enumerate(L) if l.lstrip('*') == after); L.insert(i + 1, star + name)
    wr(f, L, nl, bom); print(f, [l for l in L if 'Dismember' in l or 'Decapitations' in l or l.lstrip('*').startswith('DF - ')])
print('done; backups .bak-dismember-swap-' + st)
