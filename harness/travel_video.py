"""Record real fast-travel flights (Sky Above arcs) as shareable videos (user 2026-11-25: "a video of a travel or two").
Screen capture with ffmpeg's Desktop Duplication grabber + NVENC, HUD and performance overlay hidden during each flight.
usage: python travel_video.py [--start "Whiterun Stables"] [--trips "Riften Stables,Solitude Sawmill"] [--hour 9]
                              [--weather SkyrimClear] [--note "..."] [--sdr-white 200]
output: results/videos/<time>_<n>_<dest>.mp4 (HDR10 master, 2580x1080 30 fps); HDR + SDR copies on gallery/videos.html"""
import os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs, shots
FFMPEG = r'C:\Users\foxnn\dev\ffmpeg.exe'
def arg(name, default): return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default
START = arg('--start', 'Whiterun Stables')
TRIPS = arg('--trips', 'Riften Stables,Solitude Sawmill').split(',')
HOUR = float(arg('--hour', '9'))
WEATHER = arg('--weather', '')       # optional: weather at take-off (editor ID or 0x form ID); the trip itself is left alone
NOTE = arg('--note', 'Sky Above smooth arc, HUD hidden')
OUT = os.path.join(shots.ROOT, 'results', 'videos'); os.makedirs(OUT, exist_ok=True)
GALLERY = os.path.join(shots.ROOT, 'gallery', 'videos')
SFT_LOG = os.path.expanduser('~/Documents/My Games/Skyrim Special Edition/SKSE/SeamlessFastTravel.log')
# The desktop runs in Windows HDR. Its 8-bit and 10-bit captures are Windows' SDR conversion with 80 nits as white,
# 2.5x brighter than the 200-nit SDR white the screen shows (measured 2026-11-25 on the overlay's white text). So the
# capture is the linear 16-bit one, encoded straight to HDR10 (what the screen shows, nit for nit); the SDR copy is
# made from that afterwards with SDR_WHITE as white. 30 fps: the 16-bit download + conversion keeps up only at 30.
SDR_WHITE = float(arg('--sdr-white', '100'))  # the tone mapper's peak (OpenDRT tn_Lp = 100); the UI alone reaches the 200-nit desktop SDR white


def flights_ended():
    try: return open(SFT_LOG, encoding='utf-8', errors='replace').read().count('Flight ended')
    except Exception: return 0


def fly(dest, timeout=180):
    n0 = flights_ended(); t0 = time.time()
    cs.world(action='fasttravel', name=dest)
    while time.time() - t0 < timeout and flights_ended() <= n0:
        if bench.menus().get('messageBoxOpen'):      # SkyrimNet's "older save" prompt can come up at the destination load
            time.sleep(1); bench.tap('right'); time.sleep(.6); bench.tap('enter'); print('  answered a message box (Delete History)', flush=True)
        time.sleep(0.5)
    return flights_ended() > n0


def record_start(path):
    return subprocess.Popen([FFMPEG, '-hide_banner', '-loglevel', 'error', '-y', '-filter_threads', '16',
                             '-f', 'lavfi', '-i', 'ddagrab=output_idx=0:framerate=30:output_fmt=16bit', '-filter_threads', '16',
                             '-vf', 'hwdownload,format=rgbaf16le,zscale=w=2580:h=1080:filter=bilinear:transferin=linear:primariesin=709:'
                                    'matrixin=gbr:rangein=full:npl=80:transfer=smpte2084:primaries=2020:matrix=2020_ncl:range=limited,format=p010le',
                             '-c:v', 'hevc_nvenc', '-profile:v', 'main10', '-preset', 'p5', '-rc', 'vbr', '-cq', '18', '-b:v', '0', '-tag:v', 'hvc1',
                             '-color_primaries', 'bt2020', '-color_trc', 'smpte2084', '-colorspace', 'bt2020nc', '-color_range', 'tv',
                             '-movflags', '+faststart', path], stdin=subprocess.PIPE)


def record_stop(p):
    try: p.communicate(b'q', timeout=30)
    except subprocess.TimeoutExpired: p.kill()


def publish(src, title, note):
    """HDR copy (HEVC 10-bit PQ, ~10 Mbit/s) and SDR copy (H.264, SDR_WHITE as white) into gallery/videos, then the page."""
    import videos_page
    os.makedirs(GALLERY, exist_ok=True)
    base = os.path.splitext(os.path.basename(src))[0]
    hdr, sdr = base + '_hdr.mp4', base + '_sdr.mp4'
    subprocess.run([FFMPEG, '-hide_banner', '-loglevel', 'error', '-y', '-i', src, '-c:v', 'hevc_nvenc', '-profile:v', 'main10', '-preset', 'p7',
                    '-rc', 'vbr', '-b:v', '10M', '-maxrate', '16M', '-bufsize', '32M', '-tag:v', 'hvc1', '-color_primaries', 'bt2020',
                    '-color_trc', 'smpte2084', '-colorspace', 'bt2020nc', '-color_range', 'tv', '-movflags', '+faststart',
                    os.path.join(GALLERY, hdr)], check=True)
    subprocess.run([FFMPEG, '-hide_banner', '-loglevel', 'error', '-y', '-i', src, '-vf',
                    'zscale=matrixin=2020_ncl:rangein=limited:primariesin=2020:transferin=smpte2084:transfer=linear:npl=%g:primaries=709:'
                    'matrix=gbr:range=full,format=gbrpf32le,zscale=transfer=bt709:matrix=709:range=limited,format=yuv420p' % SDR_WHITE,
                    '-c:v', 'h264_nvenc', '-preset', 'p7', '-rc', 'vbr', '-b:v', '8M', '-maxrate', '14M', '-bufsize', '28M',
                    '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-color_range', 'tv', '-movflags', '+faststart',
                    os.path.join(GALLERY, sdr)], check=True)
    mb = lambda f: round(os.path.getsize(os.path.join(GALLERY, f)) / 1e6)
    videos_page.add({'id': base, 'title': title, 'when': time.strftime('%Y-%m-%d %H:%M'), 'note': note,
                     'hdr': hdr, 'sdr': sdr, 'hdrMB': mb(hdr), 'sdrMB': mb(sdr)})
    videos_page.build()
    return hdr, sdr


if __name__ == '__main__':
    if not bench.running(): bench.launch()
    if bench.pos() is None: sys.exit('no player position')
    v = cs.call('communityshaders.testbed', {'action': 'view_get'})
    if v['cell'].get('interior'):
        bench.console('cow Tamriel 4 -3'); time.sleep(8); shots.ready(25, 150)
    bench.console('tgm'); time.sleep(1)
    if START:
        print('to the start:', START, flush=True)
        fly(START); shots.ready(15, 120)
    po = cs.call('communityshaders.feature', {'action': 'get', 'shortName': 'PerformanceOverlay'})
    cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'PerformanceOverlay', 'settings': dict(po, ShowInOverlay=False)})
    cs.world(action='hour', value=HOUR); time.sleep(8)
    if WEATHER:
        cs.world(action='weather', **({'id': WEATHER} if WEATHER.startswith('0x') else {'name': WEATHER})); time.sleep(10)
    stamp = time.strftime('%Y%m%d_%H%M'); done = []; here = START or arg('--from', 'here')
    try:
        for i, dest in enumerate(TRIPS, 1):
            if not bench.running(): sys.exit('GAME DIED')
            path = os.path.join(OUT, '%s_%d_%s.mp4' % (stamp, i, ''.join(c for c in dest if c.isalnum())))
            bench.console('tm'); time.sleep(1.0)          # hide HUD
            rec = record_start(path); time.sleep(3.0)     # a few seconds standing before take-off
            ok = fly(dest); time.sleep(6.0)               # and a few after landing
            record_stop(rec); bench.console('tm')
            print('%s: flight %s, %s' % (dest, 'ended' if ok else 'TIMED OUT', path), flush=True)
            done.append((path, '%s to %s' % (here, dest), NOTE)); here = dest
            shots.ready(10, 90); time.sleep(4)
    finally:
        cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'PerformanceOverlay', 'settings': dict(po, ShowInOverlay=True)})
    for path, title, note in done:
        print('published:', publish(path, title, note), flush=True)
