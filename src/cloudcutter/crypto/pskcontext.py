import secrets
import ssl
from sslpsk3.sslpsk3 import _ssl_set_psk_client_callback, _ssl_set_psk_server_callback

from Cryptodome.Cipher import AES
from hashlib import md5, sha256

class PSKContext(ssl.SSLContext):
    DEFAULT_HINT = b'1dHRsc2NjbHltbGx3eWh50000000000000000'

    def __new__(cls, authkey: bytes = None, uuid: bytes = None, psk: bytes = None):
        # Tornado requires an SSLContext. Each connection gets a separate transport
        # below, since this compatibility class is also used in client mode.
        return super().__new__(cls, ssl.PROTOCOL_TLS_SERVER)

    def __init__(self, authkey: bytes = None, uuid: bytes = None, psk: bytes = None):
        self.psk = b'' if psk is None else psk
        self.uuid = b'' if uuid is None else uuid
        self.authkey = b'' if authkey is None else authkey

    def wrap_socket(self, sock, **kwargs):
        server_side = kwargs.get('server_side', False)
        kwargs.pop('server_hostname', None)
        handshake = kwargs.pop('do_handshake_on_connect', True)
        transport = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER if server_side else ssl.PROTOCOL_TLS_CLIENT)
        if not server_side:
            transport.check_hostname = False
            transport.verify_mode = ssl.CERT_NONE  # PSK authenticates this connection.
        transport.minimum_version = transport.maximum_version = ssl.TLSVersion.TLSv1_2
        transport.set_ciphers('PSK-AES128-CBC-SHA256')
        wrapped = transport.wrap_socket(sock, do_handshake_on_connect=False, **kwargs)
        try:
            # Tuya identities contain arbitrary non-NUL bytes. CPython 3.13's
            # native PSK callback decodes them as UTF-8, which is not valid here.
            # sslpsk3 1.1.1's OpenSSL callbacks preserve bytes; only its obsolete
            # ssl.wrap_socket convenience wrapper must be avoided. Keep that exact
            # dependency pin: 2.x changes these callbacks to text as well.
            callback = lambda value: self._psk_and_pskid(value, server_side)
            if server_side:
                _ssl_set_psk_server_callback(wrapped, callback, self.DEFAULT_HINT)
            else:
                _ssl_set_psk_client_callback(wrapped, callback)
            if handshake:
                wrapped.do_handshake()
            return wrapped
        except BaseException:
            wrapped.close()
            raise

    def _psk_and_pskid(self, identity_or_hint: bytes, server_side: bool):
        if not identity_or_hint:
            return b'' if server_side else (b'', b'')
        psk_id_version = identity_or_hint[0]
        if not self.psk or psk_id_version == 1:
            print(f"Using PSK v1 - Received PSK ID version {psk_id_version:02x}")
            psk, psk_id = self._psk_id_v1(identity_or_hint, server_side)
        else:
            print(f"Using PSK v2 - Received PSK ID version {psk_id_version:02x}")
            psk, psk_id = self._psk_id_v2(identity_or_hint, server_side)
        return psk if server_side else (psk, psk_id)

    def _psk_id_v1(self, identity_or_hint: bytes, server_side: bool):
        if server_side:
            init_id = identity_or_hint
            key = md5(self.DEFAULT_HINT[-16:]).digest()
        else:
            if not self.uuid:
                raise ValueError('Cannot create a PSKv1 session in client mode without a known uuid')
            hint = identity_or_hint
            authkey_hash = md5(self.authkey).digest()
            uuid_hash = md5(self.uuid).digest()
            rand_data = secrets.token_bytes(0x10)
            init_id = b'\x01' + rand_data + uuid_hash + b'_' + authkey_hash
            init_id = init_id.replace(b'\x00', b'?')
            key = md5(hint[-16:]).digest()

        iv = md5(init_id[1:]).digest()
        cipher = AES.new(key, AES.MODE_CBC, iv)
        psk = cipher.encrypt(init_id[1:33])
        return (psk, init_id)

    def _psk_id_v2(self, identity_or_hint: bytes, server_side: bool):
        if server_side:
            if not self.psk:
                raise ValueError('Cannot establish a PSKv2 session without a known PSK')
            return (self.psk, identity_or_hint)

        if not self.uuid:
            raise ValueError('Cannot create a PSKv2 session in client mode without a known uuid')

        uuid_hash = sha256(self.uuid).digest()
        rand_data = secrets.token_bytes(0x10)
        init_id = b'\x02' + rand_data + uuid_hash
        return (self.psk, init_id.replace(b'\x00', b'?'))
