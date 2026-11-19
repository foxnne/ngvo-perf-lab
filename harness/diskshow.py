"""Print audit/disk_usage.tsv by depth. usage: python diskshow.py [minGB=8] [prefix]"""
import os, sys
T = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'audit', 'disk_usage.tsv')
rows = [l.rstrip('\n').split('\t') for l in open(T, encoding='utf-8')]
rows = [(int(a), int(b), c) for a, b, c in rows]
mn = float(sys.argv[1]) if len(sys.argv) > 1 else 8
prefix = sys.argv[2].lower() if len(sys.argv) > 2 else 'c:' + chr(92)
for depth in range(1, 6):
    print('--- depth', depth)
    for s, n, p in rows:
        if p.rstrip(chr(92)).count(chr(92)) == depth and s > mn * 1e9 * (0.25 if depth == 1 else 1) and p.lower().startswith(prefix):
            print('%8.1f GB %8d  %s' % (s / 1e9, n, p))
