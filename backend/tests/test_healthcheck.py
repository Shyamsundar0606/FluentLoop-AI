from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from app.core.healthcheck import check_http_status


class OkHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format, *args):
        return


class FailHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(503)
        self.end_headers()
        self.wfile.write(b"error")

    def log_message(self, format, *args):
        return


def test_check_http_status_returns_true_for_healthy_service() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), OkHandler)
    port = server.server_address[1]
    thread = Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    try:
        assert check_http_status(f"http://127.0.0.1:{port}/health", timeout=3) is True
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_check_http_status_returns_false_for_unhealthy_service() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), FailHandler)
    port = server.server_address[1]
    thread = Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    try:
        assert check_http_status(f"http://127.0.0.1:{port}/health", timeout=3) is False
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
