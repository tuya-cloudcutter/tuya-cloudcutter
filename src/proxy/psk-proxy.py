import base64
import json
import socket
import ssl
import sys
import time
import os

import tornado.httpserver
import tornado.ioloop
import tornado.web

from pskcontext import PSKContext
from tuyacipher import TuyaCipher

cipher = None
other_cipher = None

def object_to_json(obj):
    return json.dumps(obj, separators=(',',':'))

class TuyaServerHandler(tornado.web.RequestHandler):
    def initialize(self, authkey: bytes):
        global cipher
        self.authkey = authkey
        cipher = TuyaCipher(authkey)

    def reply(self, response: dict):
        encrypted = self.cipher.encrypt(response)
        encrypted = base64.b64encode(encrypted)

        timestamp = int(time.time())
        response = {"result": encrypted, "t": time.time()}
        signature = self.cipher.sign_server(response)

        response["sign"] = signature
        response = object_to_json(response)

        self.finish(response)

    def set_default_headers(self):
        self.set_header("Content-Type", "text/plain; charset=utf-8")
        self.set_header("Connection", "keep-alive")
        self.set_header("Server", "Tuya-Sec")


class GetURLHandler(TuyaServerHandler):
    def post(self):
        response = {"caArr":None,"httpUrl":{"addr":"http://10.42.42.1/d.json","ips":["10.42.42.1"]},"mqttUrl":{"addr":"10.42.42.1:1883","ips":["10.42.42.1"]},"ttl":600}
        response = object_to_json(response)

        self.finish(response)

class ProxyHandler(TuyaServerHandler):
    def initialize(self, authkey: bytes, sslcontext: ssl.SSLContext, host: str, port: int, profiles_dir: os.PathLike):
        super().initialize(authkey)
        self.host = host
        self.port = port
        self.sslcontext = sslcontext
        self.profiles_dir = profiles_dir

    def post(self):
        global other_cipher
        endpoint = self.get_query_argument("a")
        received, received_body, decoded, sent_request = self._outbound_request(self.request)
        print("DEBUG: decoded POST response", decoded)
        try:
            response = json.loads(decoded)
        except Exception as e:
            print("Exception unpacking json", e)
            response = decoded

        if "active" in endpoint:
            try:
                other_cipher = TuyaCipher(response["result"]["secKey"].encode("utf-8"))
            except Exception as e:
                print("Some error exchanging TuyaCipher", e)
                pass

        self._store_request_response(endpoint, sent_request, response)
        self.finish(received_body)

    def _store_request_response(self, endpoint, sent_request, response):
        if response["success"]:
            with open(os.path.join(self.profiles_dir, f"dump_recv_{endpoint}.json"), "wt") as file:
                file.write(json.dumps(response))
            with open(os.path.join(self.profiles_dir, f"dump_sent_{endpoint}.txt"), "wt") as file:
                file.write(sent_request.decode("utf-8"))

    def _outbound_request(self, request):
        request.headers["Host"] = self.host
        headers_formatted = "\r\n".join([f"{k}: {v}" for k, v in request.headers.items()])
        outbound_req = f"{request.method} {request.path}?{request.query} HTTP/1.1\r\n{headers_formatted}\r\n\r\n".encode("utf-8")
        outbound_req += request.body
        print(outbound_req)
        received = bytearray()
        with self.sslcontext.wrap_socket(socket.create_connection((self.host, self.port))) as csocket:
            csocket.settimeout(1.0)
            csocket.send(outbound_req)
            try:
                data = csocket.recv(10000)
                while len(data) > 0:
                    received += data
                    data = csocket.recv(10000)
            except socket.timeout:
                pass
        body_start = received.index(b"\r\n\r\n") + 4
        received_body = received[body_start:]
        response = json.loads(received_body.decode("utf-8").strip())
        print(response)

        decoded = cipher.decrypt(base64.b64decode(response["result"]))

        try:
            decoded = decoded.decode("utf-8").strip("\n").strip("\r").strip()
        except:
            decoded = other_cipher.decrypt(base64.b64decode(response["result"]))
            decoded = decoded.decode("utf-8").strip("\n").strip("\r").strip()

        return received, bytes(received_body), decoded, outbound_req


if __name__ == '__main__':
    if len(sys.argv) < 4:
        sys.exit("WRONG, NINCOMPOOP")

    _, uuid, psk, authkey = [x.encode() for x in sys.argv]
    context = PSKContext(authkey=authkey, uuid=uuid, psk=psk)
    profiles_dir = os.getenv("DEVICE_PROFILES_DIR", "")

    handler_config = dict(authkey=authkey)
    proxy_config = dict(sslcontext=context, host="a3.tuyaeu.com", port=443, profiles_dir=profiles_dir, **handler_config)

    application = tornado.web.Application([
        (r'/v1/url_config', GetURLHandler, handler_config),
        (r'/d.json', ProxyHandler, proxy_config),
    ])


    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(80)

    https_server = tornado.httpserver.HTTPServer(application, ssl_options=context)
    https_server.listen(443)

    tornado.ioloop.IOLoop.current().start()
