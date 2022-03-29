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
from tuyacipher import TuyaCipher, TuyaCipherKeyChoice

import hmac
from hashlib import sha256

cipher = None

def object_to_json(obj):
    return json.dumps(obj, separators=(',',':'))

class TuyaServerHandler(tornado.web.RequestHandler):
    def initialize(self, authkey: bytes):
        global cipher
        self.authkey = authkey
        cipher = TuyaCipher(authkey)
        cipher.set_seckey(b'5b4e54679e2d7ce8')

    def reply(self, key_choice, response: dict):
        encrypted = cipher.encrypt(response, key_choice)
        encrypted = base64.b64encode(encrypted).decode("utf-8")

        timestamp = int(time.time())
        response = {"result": encrypted, "t": timestamp}
        signature = cipher.sign_server(response, key_choice)

        response["sign"] = signature
        response = object_to_json(response) + "\n"

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

class FilesHandler(tornado.web.StaticFileHandler):
    def parse_url_path(self, url_path):
        if not url_path or url_path.endswith('/'):
            url_path = url_path + str('index.html')
        return url_path

class ProxyHandler(TuyaServerHandler):
    def initialize(self, authkey: bytes, sslcontext: ssl.SSLContext, host: str, port: int, profiles_dir: os.PathLike):
        super().initialize(authkey)
        self.host = host
        self.port = port
        self.sslcontext = sslcontext
        self.profiles_dir = profiles_dir

    def post(self):
        global cipher
        endpoint = self.get_query_argument("a")
        other_body = None
        key_choice = TuyaCipherKeyChoice.AUTHKEY if ("active" in endpoint) else TuyaCipherKeyChoice.SECKEY
        if not ("upgrade.get" in endpoint or "upgrade.status.update" in endpoint):
            received, received_body, decoded, sent_request = self._outbound_request(self.request, key_choice, other_body)
            print("DEBUG: decoded POST response", decoded)
            try:
                response = json.loads(decoded)
            except Exception as e:
                print("Exception unpacking json", e)
                response = decoded

            if "active" in endpoint:
                try:
                    cipher.set_seckey(response["result"]["secKey"].encode("utf-8"))
                except Exception as e:
                    print("Some error exchanging TuyaCipher", e)
                    pass
        elif "upgrade.status.update" in endpoint:
            self.reply(key_choice, {"success": True})
            return
        else:
            with open("../files/upgrade.bin", "rb") as fs:
                upgdata = fs.read()

            fsha = sha256(upgdata).hexdigest().upper().encode("utf-8")
            filehmac = hmac.digest(cipher.seckey, fsha, sha256).hex().upper()
            print("filehmac", filehmac)
            response = {
                    "result": {
                        "url": "http://10.42.42.1:80/files/upgrade.bin",
                        #"pskUrl": "https://10.42.42.1/files/upgrade.bin",
                        #"httpsUrl": "https://10.42.42.1/files/upgrade.bin",
                        "hmac": filehmac,
                        "version": "2.9.15",
                        "size": str(len(upgdata)),
                        "type": 0,
                    },
                    "success": True,
                    "t": int(time.time()),
            }
            self.reply(key_choice, response)
            return

        self._store_request_response(endpoint, sent_request, response)
        self.finish(received_body)

    def _store_request_response(self, endpoint, sent_request, response):
        if response["success"]:
            with open(os.path.join(self.profiles_dir, f"dump_recv_{endpoint}.json"), "wt") as file:
                file.write(json.dumps(response))
            with open(os.path.join(self.profiles_dir, f"dump_sent_{endpoint}.txt"), "wt") as file:
                file.write(sent_request.decode("utf-8"))

    def _outbound_request(self, request, key_choice, other_body=None):
        request.headers["Host"] = self.host
        headers_formatted = "\r\n".join([f"{k}: {v}" for k, v in request.headers.items()])
        outbound_req = f"{request.method} {request.path}?{request.query} HTTP/1.1\r\n{headers_formatted}\r\n\r\n".encode("utf-8")
        if other_body is None:
            outbound_req += request.body
        else:
            outbound_req += other_body
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

        decoded = cipher.decrypt(base64.b64decode(response["result"]), key_choice)
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
    files_handler_config = dict(path="../files/")
    application = tornado.web.Application([
        (r'/v1/url_config', GetURLHandler, handler_config),
        (r'/d.json', ProxyHandler, proxy_config),
        (r'/files/(.*)', FilesHandler, files_handler_config),
    ])


    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(80)

    https_server = tornado.httpserver.HTTPServer(application, ssl_options=context)
    https_server.listen(443)

    tornado.ioloop.IOLoop.current().start()
