"""The live views page for the phone: one picture per view, always the latest, same file names every time, with the
settings the game had for each shot and a history per view.

gallery/views.html              all views (thumbnails)
gallery/views/<name>.html       one view: the uncompressed latest shot, then its history with what changed between shots
gallery/views/<name>.png        latest shot, full size, labelled (overwritten every time)
gallery/views/h/<name>/<stamp>.png|.jpg|.json   history: full shot (last KEEP only), thumbnail, settings snapshot

publish(name, labelled_png, info, snap) is called by shots.py; `python views_page.py` only rebuilds the pages.
Served by: python -m http.server 8930 --bind 127.0.0.1 --directory ../gallery  (tailscale serve already publishes that
port to the tailnet as https://foxnne-desktop.fennec-stairs.ts.net/views.html)."""
import html, json, os, shutil, subprocess, time
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(os.path.dirname(HERE), 'gallery'); VD = os.path.join(OUT, 'views'); META = os.path.join(VD, 'meta.json')
COMMON = ['ilinalta_backlit', 'whiterun_plains', 'reach_rocks', 'pale_tower_coast', 'pale_snow_forest']
KEEP = 6      # full-size shots kept per view (each is 5-10 MB); older ones keep thumbnail, settings and change list
FORK = r'C:\Users\foxnn\dev\skyrim-community-shaders'
PRESETS = r'C:\Modlists\NGVO 8.0 Beta\mods\CS Settings\SKSE\Plugins\CommunityShaders\SettingsUser.json'


def flat(d, pre=''):
    out = {}
    for k, v in (d.items() if isinstance(d, dict) else enumerate(d) if isinstance(d, list) else []):
        key = '%s%s' % (pre, k)
        if isinstance(v, (dict, list)): out.update(flat(v, key + '.'))
        else: out[key] = v
    return out


def snapshot():
    """Everything that decides how the frame looks, read from the running game: every loaded feature's settings, the
    active pack, and which shader source built it."""
    import cs
    snap = {'features': {}}
    try:
        l = cs.call('communityshaders.feature', {'action': 'list'}); fs = l.get('features', l) if isinstance(l, dict) else l
        for f in fs:
            n = f.get('shortName') if isinstance(f, dict) else f
            if not n or (isinstance(f, dict) and f.get('loaded') is False): continue
            try:
                g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': n}); snap['features'][n] = g.get('settings', g)
            except Exception: pass
    except Exception as e: snap['error'] = repr(e)
    try:
        snap['source'] = subprocess.run(['git', '-C', FORK, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
        snap['source_uncommitted'] = [x[3:] for x in subprocess.run(['git', '-C', FORK, 'status', '--porcelain'], capture_output=True, text=True).stdout.splitlines() if x[:2].strip() == 'M']
        if os.path.exists(PRESETS): snap['pack'] = (json.load(open(PRESETS)).get('Presets') or {}).get('activePackId')
    except Exception: pass
    return snap


def changes(old, new, limit=60):
    a, b = flat(old.get('features', {})), flat(new.get('features', {})); out = []
    for k in sorted(set(a) | set(b), key=str):
        x, y = a.get(k), b.get(k)
        if isinstance(x, (int, float)) and isinstance(y, (int, float)) and abs(x - y) <= 1e-5 * max(1, abs(x), abs(y)): continue
        if x != y: out.append('%s: %s -> %s' % (k, x, y))
    for k in ('pack', 'source'):
        if old.get(k) != new.get(k): out.append('%s: %s -> %s' % (k, old.get(k), new.get(k)))
    if old.get('source_uncommitted') != new.get('source_uncommitted'): out.append('edited shader source files: %s' % ', '.join(new.get('source_uncommitted') or ['none']))
    return out[:limit] + (['... and %d more' % (len(out) - limit)] if len(out) > limit else [])


def publish(name, png, info, snap=None):
    """Overwrite the view's picture, and keep the shot with its settings in the view's history."""
    H = os.path.join(VD, 'h', name); os.makedirs(H, exist_ok=True); os.makedirs(os.path.join(VD, 't'), exist_ok=True)
    stamp = time.strftime('%Y%m%d-%H%M%S'); M = json.load(open(META)) if os.path.exists(META) else {}
    shutil.copy2(png, os.path.join(VD, name + '.png')); shutil.copy2(png, os.path.join(H, stamp + '.png'))
    im = Image.open(png).convert('RGB'); im.thumbnail((900, 900)); im.save(os.path.join(VD, 't', name + '.jpg'), quality=82)
    im.thumbnail((420, 420)); im.save(os.path.join(H, stamp + '.jpg'), quality=80)
    hist = M.get(name, {}).get('history', []); entry = dict(info, stamp=stamp, shot=time.strftime('%Y-%m-%d %H:%M'))
    if snap is not None:
        prev = next((h for h in hist if os.path.exists(os.path.join(H, h['stamp'] + '.json'))), None)
        entry['changes'] = changes(json.load(open(os.path.join(H, prev['stamp'] + '.json'))), snap) if prev else []
        entry['first'] = prev is None
        json.dump(snap, open(os.path.join(H, stamp + '.json'), 'w'))
    hist.insert(0, entry)
    for old in hist[KEEP:]:
        f = os.path.join(H, old['stamp'] + '.png')
        if os.path.exists(f): os.remove(f)
    M[name] = dict(info, shot=entry['shot'], v=int(time.time()), history=hist[:40]); json.dump(M, open(META, 'w'), indent=1); build()


def restore(name, stamp=None):
    """Put the game's settings back to what they were for a shot (live only, nothing is saved to disk)."""
    import cs
    hist = json.load(open(META))[name]['history']; H = os.path.join(VD, 'h', name)
    h = next(x for x in hist if stamp in (None, x['stamp']) and os.path.exists(os.path.join(H, x['stamp'] + '.json')))
    snap = json.load(open(os.path.join(H, h['stamp'] + '.json')))
    for n, st in snap['features'].items(): cs.call('communityshaders.feature', {'action': 'set', 'shortName': n, 'settings': st})
    print('settings of %s %s are live (%d features). Not saved: load settings in the menu or restart to drop them.' % (name, h['stamp'], len(snap['features'])))
    if snap.get('pack'): print('the shot used pack %s and shader source %s; those are not switched by this.' % (snap['pack'], snap.get('source')))


DETAIL = '''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>%s</title>
<style>body{margin:0;padding:16px;background:#111;color:#ddd;font:15px system-ui}a{color:#8cf}img{max-width:100%%;height:auto;display:block;border-radius:8px}
.h{display:grid;grid-template-columns:minmax(120px,300px) 1fr;gap:12px;margin:14px 0;padding-top:14px;border-top:1px solid #333}i{color:#888;font-style:normal;font-size:12px}
ul{padding-left:18px;font:12px ui-monospace,monospace;word-break:break-all}code{display:block;margin-top:6px;font-size:11px;color:#9a9}summary{cursor:pointer;margin-top:6px}</style>
<p><a href="../views.html">&larr; all views</a></p><h1>%s</h1><a href="%s.png?v=%d"><img src="%s.png?v=%d"></a>
<p><i>Tap the picture for the uncompressed original. History below, newest first.</i></p>%s'''


def detail(name, m):
    rows = []
    for k, h in enumerate(m.get('history', [])):
        H = 'h/%s/%s' % (name, h['stamp']); base = os.path.join(VD, 'h', name, h['stamp']); full = os.path.exists(base + '.png')
        cond = ' &middot; '.join(x for x in [h.get('weather'), h.get('hour')] if x)
        ch = h.get('changes') or []
        block = ''
        if os.path.exists(base + '.json'):
            block = '<p><i>first shot with settings recorded</i></p>' if h.get('first') else '<p><i>no settings changed since the shot before</i></p>' if not ch else \
                '<details%s><summary>%d settings changed since the shot before</summary><ul>%s</ul></details>' % (' open' if k == 0 else '', len(ch), ''.join('<li>%s</li>' % html.escape(c) for c in ch))
            block += '<a href="%s.json">all settings</a><code>undo to this: python shots.py restore %s %s</code>' % (H, name, h['stamp'])
        rows.append('<div class="h"><a%s><img src="%s.jpg"></a><div><b>%s</b> %s %s<br><i>%s</i>%s</div></div>' % (
            ' href="%s.png"' % H if full else '', H, h['shot'], cond, '(current)' if k == 0 else '', 'full size kept' if full else 'thumbnail only', block))
    page = DETAIL % (html.escape(name), html.escape(name.replace('_', ' ')), name, m['v'], name, m['v'], '\n'.join(rows))
    open(os.path.join(VD, name + '.html'), 'w', encoding='utf-8').write(page)


PAGE = '''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NGVO views</title>
<style>body{margin:0;padding:16px;background:#111;color:#ddd;font:15px system-ui}h1{font-size:20px}h2{font-size:16px;margin:22px 0 8px}small{color:#888;font-weight:400}
.g{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:10px}a{color:#ddd;text-decoration:none;background:#1c1c1c;border-radius:8px;overflow:hidden;display:block}
img{width:100%%;height:auto;display:block;background:#222}span{display:block;padding:6px 8px;font-size:13px}i{color:#888;font-style:normal;font-size:12px}b{color:#f80}</style>
<h1>NGVO views <small>%d views, updated %s. Each picture is the latest shot of that view; tap for the uncompressed original, its settings and its history.</small></h1>
<p><a href="videos.html" style="display:inline;background:none;color:#8cf">Fast-travel videos &rarr;</a></p>%s'''


def build():
    M = json.load(open(META)) if os.path.exists(META) else {}
    # Newest first (user 2026-11-24): one list ordered by when each view was last shot, grouped by day.
    def group(n): return 'common view' if n in COMMON else 'sky study' if n.startswith('sky_') else 'sea horizon' if n.startswith('sea_') else ''
    body = []; day = None
    for n in sorted(M, key=lambda n: (M[n].get('shot', ''), M[n].get('v', 0)), reverse=True):
        m = M[n]; d = m.get('shot', '')[:10]
        if d != day:
            if day is not None: body.append('</div>')
            day = d; body.append('<h2>Shot %s <small>%d</small></h2><div class="g">' % (html.escape(d), sum(1 for x in M.values() if x.get('shot', '')[:10] == d)))
        cond = ' &middot; '.join(x for x in [m.get('weather'), m.get('hour'), group(n)] if x); detail(n, m)
        warn = '<b>land missing?</b> ' if m.get('holes') else ''
        body.append('<a href="views/%s.html?v=%d"><img src="views/t/%s.jpg?v=%d"><span>%s<br><i>%s%s &middot; shot %s &middot; %d in history</i></span></a>' % (
            n, m['v'], n, m['v'], html.escape(n.replace('_', ' ')), warn, cond, m['shot'], len(m.get('history', []))))
    if day is not None: body.append('</div>')
    open(os.path.join(OUT, 'views.html'), 'w', encoding='utf-8').write(PAGE % (len(M), time.strftime('%Y-%m-%d %H:%M'), '\n'.join(body)))


if __name__ == '__main__': build(); print('views page built')
