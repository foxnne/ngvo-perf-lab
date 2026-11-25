"""Serves ../gallery on 127.0.0.1:8930 (published to the tailnet by tailscale serve) with HTTP Range support,
which iPhone Safari needs to play the videos on videos.html; python -m http.server has no Range.
usage: python gallery_server.py"""
import functools, http.server, os, re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'gallery')


class Handler(http.server.SimpleHTTPRequestHandler):
    def send_head(self):
        rng = self.headers.get('Range')
        path = self.translate_path(self.path)
        m = re.match(r'bytes=(\d*)-(\d*)$', rng or '')
        if not m or not os.path.isfile(path):
            return super().send_head()
        size = os.path.getsize(path)
        start = int(m.group(1)) if m.group(1) else max(size - int(m.group(2) or 0), 0)
        end = int(m.group(2)) if m.group(1) and m.group(2) else size - 1
        if start >= size:
            self.send_error(416); return None
        end = min(end, size - 1)
        f = open(path, 'rb'); f.seek(start)
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(path))
        self.send_header('Content-Range', 'bytes %d-%d/%d' % (start, end, size))
        self.send_header('Content-Length', str(end - start + 1))
        self.send_header('Accept-Ranges', 'bytes')
        self.end_headers()
        self.range_left = end - start + 1
        return f

    def end_headers(self):
        if not self.headers.get('Range'):
            self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()

    def copyfile(self, source, outputfile):
        left = getattr(self, 'range_left', None)
        if left is None:
            return super().copyfile(source, outputfile)
        while left > 0:
            buf = source.read(min(1 << 20, left))
            if not buf: break
            try: outputfile.write(buf)
            except (ConnectionResetError, BrokenPipeError): break
            left -= len(buf)


if __name__ == '__main__':
    http.server.ThreadingHTTPServer(('127.0.0.1', 8930), functools.partial(Handler, directory=ROOT)).serve_forever()
