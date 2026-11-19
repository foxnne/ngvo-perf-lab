"""Builds a phone-friendly gallery of full-resolution shots: gallery/index.html with thumbnails that open the originals.
Serve with: python -m http.server 8930 --bind 127.0.0.1 --directory ../gallery   (tailscale serve publishes it to the tailnet)
usage: python gallery.py"""
import html, os, shutil, time
from PIL import Image
LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(LAB, 'results'); OUT = os.path.join(LAB, 'gallery'); os.makedirs(OUT, exist_ok=True)
# Keep this short: the page is opened on a phone. Only current, judgeable sets; older or superseded shots stay on disk in results/ but are not published.
def latest(sub):
    d = os.path.join(RES, sub)
    tags = sorted((t for t in os.listdir(d) if os.path.isdir(os.path.join(d, t))), key=lambda t: os.path.getmtime(os.path.join(d, t))) if os.path.isdir(d) else []
    return f'{sub}/{tags[-1]}' if tags else sub
SETS = [('Neural Rendering 100% vs 75%: native-resolution face crops (tap, then zoom)', ['npc_portraits/nr_100_vs_75_front.png', 'npc_portraits/nr_100_vs_75_three_quarter_left.png', 'npc_portraits/preset_compare_crops.png']),
        ('Chosen reference views', ['viewfinder_west/ilinalta_up1100_yaw252.png', 'viewfinder_plains/plains_up0700_yaw270.png']),
        ('Cloud preset, latest pass: ' + os.path.basename(latest('sky_preset')), latest('sky_preset')),
        ('NPC portraits (Neural Rendering on, pass p4)', 'npc_portraits/p4')]
EXT = ('.png', '.avif', '.jxr', '.jpg')
body = []
KEEP = set()                                           # files this build publishes; everything else is pruned at the end (no wipe first: a wipe left thumbnails missing while a page was open)
for title, src in SETS:
    files = []
    if isinstance(src, list): files = [os.path.join(RES, f) for f in src if os.path.exists(os.path.join(RES, f))]
    else:
        for root, _, names in os.walk(os.path.join(RES, src)):
            if 'unmatched' in root: continue
            files += [os.path.join(root, n) for n in sorted(names) if n.lower().endswith(EXT) and not n.startswith('sheet_')]
    if not files: continue
    body.append(f'<details{" open" if len(body) == 0 else ""}><summary>{html.escape(title)} <small>{len(files)}</small></summary><div class="g">')
    for f in files:
        rel = os.path.relpath(f, RES).replace(os.sep, '/'); dst = os.path.join(OUT, 'full', rel); os.makedirs(os.path.dirname(dst), exist_ok=True)
        if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(f): shutil.copy2(f, dst)
        th = os.path.join(OUT, 'thumb', os.path.splitext(rel)[0] + '.jpg'); os.makedirs(os.path.dirname(th), exist_ok=True)
        if not os.path.exists(th) or os.path.getmtime(th) < os.path.getmtime(f):
            try: im = Image.open(f).convert('RGB'); im.thumbnail((480, 480)); im.save(th, quality=78)
            except Exception: th = None
        name = html.escape(os.path.splitext(os.path.basename(f))[0]); mb = os.path.getsize(f) / 1e6
        KEEP.add(os.path.normpath(dst))
        if th: KEEP.add(os.path.normpath(th))
        # no lazy-loading: Safari does not always load lazy images inside a <details> that is opened later. Version tag defeats stale caches.
        img = f'<img width="480" height="201" src="thumb/{os.path.splitext(rel)[0]}.jpg?v={int(os.path.getmtime(f))}">' if th else ''
        body.append(f'<a href="full/{rel}">{img}<span>{name} <i>{mb:.1f} MB</i></span></a>')
    body.append('</div></details>')
page = '''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NGVO shots</title>
<style>body{margin:0;padding:16px;background:#111;color:#ddd;font:15px system-ui}h1{font-size:20px}summary{font-size:16px;margin:18px 0 8px;cursor:pointer}small{color:#888;font-weight:400}
.g{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px}a{color:#ddd;text-decoration:none;background:#1c1c1c;border-radius:8px;overflow:hidden;display:block}
img{width:100%%;height:auto;display:block;background:#222}span{display:block;padding:6px 8px;font-size:12px;word-break:break-all}i{color:#888;font-style:normal}</style>
<h1>NGVO shots <small>built %s. Tap a thumbnail for the full-resolution original.</small></h1>%s''' % (time.strftime('%Y-%m-%d %H:%M'), '\n'.join(body))
open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(page)
for sub in ('full', 'thumb'):
    for root, dirs, names in os.walk(os.path.join(OUT, sub), topdown=False):
        for n in names:
            if os.path.normpath(os.path.join(root, n)) not in KEEP: os.remove(os.path.join(root, n))
        if not os.listdir(root): os.rmdir(root)
print('gallery built:', sum(b.startswith('<a ') for b in body), 'shots')
