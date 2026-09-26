"""Serve the RODAIS folder on 127.0.0.1 for the headless Azgaar driver (the Atlas server's settings:
a large request queue and keep-alive, so Azgaar's hundred-odd module requests at start-up never fail).

    python3 serve.py PORT          prints "READY <port>" once listening
"""
import functools
import http.server
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Server(http.server.ThreadingHTTPServer):
    request_queue_size = 1024
    daemon_threads = True
    allow_reuse_address = True


class Quiet(http.server.SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml',
                      '.json': 'application/json', '.webmanifest': 'application/manifest+json', '.map': 'text/plain'}

    def guess_type(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        return super().guess_type(path)

    def log_message(self, *args):
        pass

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    root = sys.argv[2] if len(sys.argv) > 2 else ROOT
    server = Server(('127.0.0.1', port), functools.partial(Quiet, directory=root))
    print('READY', server.server_address[1], flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
