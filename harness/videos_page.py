"""Builds gallery/videos.html from gallery/videos/videos.json (newest first). Each entry: one recorded trip with an HDR
copy (HEVC 10-bit PQ, for HDR phones and screens) and an SDR copy (H.264, tone-mapped, for everything else).
usage: python videos_page.py            (travel_video.py calls add() and build() after each recording)"""
import html, json, os, time
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'gallery'); VID = os.path.join(OUT, 'videos'); META = os.path.join(VID, 'videos.json')

PAGE = '''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NGVO videos</title>
<style>body{margin:0;padding:16px;background:#111;color:#ddd;font:15px system-ui}a{color:#8cf}h1{font-size:20px}small,i{color:#888;font-weight:400;font-style:normal}
.v{margin:18px 0;padding-top:14px;border-top:1px solid #333}video{width:100%%;max-width:1400px;height:auto;display:block;border-radius:8px;background:#000}
p{margin:6px 0}</style>
<p><a href="views.html">&larr; views</a></p><h1>NGVO videos <small>%d, updated %s. HDR plays on HDR screens (iPhone, Mac); SDR is for everything else.</small></h1>%s'''


def load(): return json.load(open(META)) if os.path.exists(META) else []


def add(entry):
    os.makedirs(VID, exist_ok=True)
    m = [e for e in load() if e['id'] != entry['id']]; m.append(entry)
    json.dump(m, open(META, 'w'), indent=1)


def build():
    m = sorted(load(), key=lambda e: e['id'], reverse=True); rows = []
    for e in m:
        hdr, sdr = e.get('hdr'), e.get('sdr')
        src = ''.join('<source src="videos/%s" type="%s">' % (f, t) for f, t in
                      [(hdr, 'video/mp4; codecs=hvc1'), (sdr, 'video/mp4')] if f)
        links = ' &middot; '.join('<a href="videos/%s">%s (%s MB)</a>' % (f, k, e.get(k + 'MB', '?')) for f, k in [(hdr, 'hdr'), (sdr, 'sdr')] if f)
        rows.append('<div class="v"><p><b>%s</b> <i>%s</i></p><video controls playsinline preload="metadata">%s</video><p><i>%s</i> &middot; %s</p></div>' % (
            html.escape(e['title']), html.escape(e.get('when', '')), src, html.escape(e.get('note', '')), links))
    open(os.path.join(OUT, 'videos.html'), 'w', encoding='utf-8').write(PAGE % (len(m), time.strftime('%Y-%m-%d %H:%M'), '\n'.join(rows)))


if __name__ == '__main__': build(); print('videos page built')
