import json, collections, os
BS = chr(92)
h2 = json.load(open(r'C:\Users\foxnn\dev\no-ivy-trees\work\hits2.json'))
c = collections.defaultdict(set)
for r, d in h2.items():
    for s in d['shapes']:
        if s['ivy'] and ('ivy' in s['name'].lower() or (s['tex'] and 'ivy' in s['tex'][0].lower())):
            c[(d['win'][1], os.path.dirname(r))].add(os.path.basename(s['tex'][0]).lower() if s['tex'] else s['name'])
for k, v in sorted(c.items(), key=lambda x: x[0][1]):
    print(k[0][:40], '|', k[1], '|', sorted(v)[:4])
