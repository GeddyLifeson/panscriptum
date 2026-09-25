"""
Dia-thìr Atlas -- the chronicle of Dia-thìr and its map, as one program.

Double-click "Diathir Atlas.bat" (Windows), or run:  python atlas.py

It serves this folder to your own machine only (127.0.0.1), opens your browser on the chronicle,
and keeps running until you close this window. Nothing is sent anywhere: the map generator runs
from the fmg/ folder here. Close the window (or press Ctrl+C) to stop it.
"""
import functools
import http.server
import os
import socket
import sys
import threading
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))


class Server(http.server.ThreadingHTTPServer):
    # the map-maker asks for about a hundred files at once when it starts; Python's default queue holds only 5
    # waiting connections, and on Windows the rest are refused outright, so random files fail to load
    request_queue_size = 1024
    daemon_threads = True


class Quiet(http.server.SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'   # keep connections open between files, so far fewer are needed
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml',
                      '.json': 'application/json', '.webmanifest': 'application/manifest+json', '.map': 'text/plain'}

    def guess_type(self, path):
        # decide the type from our own table first: on some Windows machines the registry says .js is text/plain,
        # and a browser will not run the map-maker's main script (a module) served as plain text
        ext = os.path.splitext(path)[1].lower()
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        return super().guess_type(path)

    def log_message(self, *args):
        pass

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')   # a rebuilt atlas is never served stale
        super().end_headers()


def free_port(preferred=8765):
    for port in [preferred] + list(range(preferred + 1, preferred + 50)):
        with socket.socket() as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    return 0


def check_files():
    """Say so plainly if a file the map needs is missing: an antivirus sometimes removes one when the zip is unpacked."""
    fmg = os.path.join(HERE, 'fmg')
    main_js = [f for f in os.listdir(fmg) if f.startswith('index-') and f.endswith('.js')] if os.path.isdir(fmg) else []
    missing = [n for n in ('index.html', 'Diathir.map') if not os.path.isfile(os.path.join(HERE, n))]
    if not os.path.isdir(fmg) or not main_js or not os.path.isfile(os.path.join(fmg, 'index.html')):
        missing.append('fmg/index-*.js (the map-maker)')
    if missing:
        print('A file the Atlas needs is missing: ' + ', '.join(missing))
        print('Your antivirus may have removed it when the zip was unpacked. Restore it from quarantine,')
        print('or add this folder to the antivirus exceptions, and unpack the zip again.')
        print()


def main():
    check_files()
    port = free_port()
    server = Server(('127.0.0.1', port), functools.partial(Quiet, directory=HERE))
    url = 'http://127.0.0.1:%d/index.html' % server.server_address[1]
    print('Dia-thìr Atlas is running at', url)
    print('Close this window, or press Ctrl+C, to stop it.')
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    if sys.version_info < (3, 7):
        sys.exit('Dia-thìr Atlas needs Python 3.7 or newer.')
    main()
