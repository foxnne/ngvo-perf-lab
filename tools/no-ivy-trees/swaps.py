"""List root-level BOS / Seasons ini files of enabled mods (winning copy per file name)."""
import os, sys
sys.path.insert(0, r'C:\Users\foxnn\dev\biome-flora\tools')
import flib


def swap_files():
    win = {}
    dirs = [('<Stock Game>', flib.GAME)] + [(m, os.path.join(flib.MODS, m)) for m in reversed(flib.enabled_mods())] + [('<overwrite>', os.path.join(flib.ROOT, 'overwrite'))]
    for label, d in dirs:
        try:
            for f in os.listdir(d):
                fl = f.lower()
                if fl.endswith('_swap.ini'):
                    win[fl] = (label, os.path.join(d, f))
        except OSError:
            pass
        sd = os.path.join(d, 'Seasons')
        if os.path.isdir(sd):
            for f in os.listdir(sd):
                win['seasons/' + f.lower()] = (label, os.path.join(sd, f))
    return win


if __name__ == '__main__':
    w = swap_files()
    for k, (m, p) in sorted(w.items()):
        print('%-60s %-50s %d' % (k, m[:50], os.path.getsize(p)))
