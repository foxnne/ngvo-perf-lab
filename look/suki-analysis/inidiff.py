"""helper: parse ENB inis, diff per-weather files against the global enbseries.ini. usage: python -I inidiff.py [file ...]"""
import os, sys, glob, re, collections
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ref', 'nlva', 'insane')
def parse(p):
    d = collections.OrderedDict(); sec = None
    for line in open(p, encoding='latin-1'):
        line = line.strip()
        if not line or line.startswith('//') or line.startswith(';'): continue
        m = re.match(r'\[(.+)\]', line)
        if m: sec = m.group(1).upper(); continue
        if '=' in line and sec:
            k, v = line.split('=', 1); d[(sec, k.strip())] = v.strip()
    return d
def num(v):
    try: return float(v)
    except: return None
G = parse(os.path.join(ROOT, 'enbseries.ini'))
def diff(name, secs=None, thresh=0.0):
    W = parse(os.path.join(ROOT, 'enbseries', name)); out = []
    for k, v in W.items():
        if secs and k[0] not in secs: continue
        g = G.get(k)
        if g is None: out.append((k, None, v)); continue
        a, b = num(g), num(v)
        if a is not None and b is not None:
            if abs(a - b) > thresh: out.append((k, g, v))
        elif g.replace(' ', '') != v.replace(' ', ''): out.append((k, g, v))
    return W, out
if __name__ == '__main__':
    for n in sys.argv[1:]:
        W, o = diff(n); print('=====', n, len(W), 'keys,', len(o), 'differ')
        for k, g, v in o: print('  [%s] %s: %s -> %s' % (k[0], k[1], g, v))
