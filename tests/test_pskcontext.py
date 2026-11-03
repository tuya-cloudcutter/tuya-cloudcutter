"""Real loopback TLS handshakes; no device, radio, cloud or firmware transfer."""
import gc
from pathlib import Path
import socket
import ssl
import sys
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from cloudcutter.crypto.pskcontext import PSKContext
from sslpsk3.sslpsk3 import _callbacks


class PSKContextTests(unittest.TestCase):
    def exchange(self, psk=None, nonblocking=False):
        server_context = PSKContext(psk=psk)
        client_context = PSKContext(authkey=b'a' * 32, uuid=b'u' * 16, psk=psk)
        observed, errors = [], []
        original = server_context._psk_and_pskid
        def capture(identity, side):
            observed.append(identity)
            return original(identity, side)
        server_context._psk_and_pskid = capture
        listener = socket.socket()
        self.addCleanup(listener.close)
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        listener.settimeout(5)
        def serve():
            try:
                raw, _ = listener.accept()
                with raw:
                    raw.settimeout(5)
                    with server_context.wrap_socket(raw, server_side=True,
                                                   do_handshake_on_connect=not nonblocking) as tls:
                        if nonblocking:
                            tls.setblocking(False)
                            import select
                            import time
                            deadline = time.monotonic() + 5
                            while True:
                                try:
                                    tls.do_handshake()
                                    break
                                except ssl.SSLWantReadError:
                                    select.select([tls], [], [], 0.1)
                                except ssl.SSLWantWriteError:
                                    select.select([], [tls], [], 0.1)
                                if time.monotonic() > deadline:
                                    raise TimeoutError('Nonblocking handshake deadline')
                            tls.settimeout(5)
                        self.assertEqual(tls.version(), 'TLSv1.2')
                        self.assertEqual(tls.cipher()[0], 'PSK-AES128-CBC-SHA256')
                        self.assertEqual(tls.recv(4), b'ping')
                        tls.sendall(b'pong')
            except BaseException as exc:
                errors.append(exc)
        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        # Both PSKv1/v2 identities include invalid UTF-8 in their random section.
        with patch('cloudcutter.crypto.pskcontext.secrets.token_bytes', return_value=b'\xff\x80' * 8):
            with socket.create_connection(listener.getsockname(), timeout=5) as raw:
                with client_context.wrap_socket(raw) as tls:
                    tls.sendall(b'ping')
                    self.assertEqual(tls.recv(4), b'pong')
        thread.join(6)
        self.assertFalse(thread.is_alive())
        if errors:
            raise errors[0]
        self.assertIsInstance(observed[0], bytes)
        self.assertIn(b'\xff\x80', observed[0])

    def test_binary_pskv1_round_trip(self):
        self.exchange()

    def test_binary_pskv2_round_trip(self):
        self.exchange(psk=b'k' * 32)

    def test_tornado_style_deferred_nonblocking_handshake(self):
        self.exchange(nonblocking=True)

    def test_callback_registry_releases_sockets(self):
        gc.collect()
        before = len(_callbacks)
        for _ in range(3):
            self.exchange()
        gc.collect()
        self.assertEqual(len(_callbacks), before)

    def test_empty_identity_is_rejected(self):
        self.assertEqual(PSKContext()._psk_and_pskid(b'', True), b'')

    def test_real_tornado_https_server(self):
        import asyncio
        import queue
        import tornado.httpserver
        import tornado.web
        ready, errors = queue.Queue(), []
        class Ping(tornado.web.RequestHandler):
            def get(self):
                self.finish('pong')
        async def run_server():
            stop = asyncio.Event()
            server = tornado.httpserver.HTTPServer(tornado.web.Application([(r'/', Ping)]),
                                                  ssl_options=PSKContext())
            server.listen(0, '127.0.0.1')
            port = next(iter(server._sockets.values())).getsockname()[1]
            ready.put((port, asyncio.get_running_loop(), stop))
            try:
                await stop.wait()
            finally:
                server.stop()
                await server.close_all_connections()
        def serve():
            try:
                asyncio.run(run_server())
            except BaseException as exc:
                errors.append(exc)
        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        port, loop, stop = ready.get(timeout=5)
        try:
            with patch('cloudcutter.crypto.pskcontext.secrets.token_bytes', return_value=b'\xff\x80' * 8):
                with socket.create_connection(('127.0.0.1', port), timeout=5) as raw:
                    with PSKContext(authkey=b'a'*32, uuid=b'u'*16).wrap_socket(raw) as tls:
                        tls.sendall(b'GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
                        response = b''
                        while chunk := tls.recv(4096):
                            response += chunk
                        self.assertIn(b'200 OK', response)
                        self.assertTrue(response.endswith(b'pong'))
        finally:
            loop.call_soon_threadsafe(stop.set)
            thread.join(6)
        self.assertFalse(thread.is_alive())
        if errors:
            raise errors[0]


if __name__ == '__main__':
    unittest.main()
