"""
Rodos Atlas -- the chronicle of Rodos and its map, as one program.

Double-click "Rodos Atlas.bat" (Windows), or run:  python atlas.py

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


class Quiet(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml',
                      '.json': 'application/json', '.webmanifest': 'application/manifest+json', '.map': 'text/plain'}

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


def main():
    port = free_port()
    server = http.server.ThreadingHTTPServer(('127.0.0.1', port), functools.partial(Quiet, directory=HERE))
    url = 'http://127.0.0.1:%d/index.html' % server.server_address[1]
    print('Rodos Atlas is running at', url)
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
        sys.exit('Rodos Atlas needs Python 3.7 or newer.')
    main()
