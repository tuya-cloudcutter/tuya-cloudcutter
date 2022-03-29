import secrets
import ssl
import sslpsk

from Cryptodome.Cipher import AES
from hashlib import md5, sha256

class PSKContext(ssl.SSLContext):
    DEFAULT_HINT = b'1dHRsc2NjbHltbGx3eWh50000000000000000'

    def __init__(self, authkey: bytes, uuid: bytes = None, psk: bytes = None):
        self.psk = b'' if psk is None else psk
        self.uuid = b'' if uuid is None else uuid

    def wrap_socket(self, sock, **kwargs):
        server_side = kwargs.get('server_side', False)
        _ = kwargs.pop('server_hostname', None)
        kwargs['psk'] = lambda identity_or_hint: self._psk_and_pskid(identity_or_hint, server_side)
        kwargs['ssl_version'] = ssl.PROTOCOL_TLSv1_2
        kwargs['ciphers'] = 'PSK-AES128-CBC-SHA256'
        if server_side:
            kwargs['hint'] = self.DEFAULT_HINT
        return sslpsk.wrap_socket(sock, **kwargs)

    def _psk_and_pskid(self, identity_or_hint: bytes, server_side: bool):
        if not self.psk or identity_or_hint[0] == 1:
            print("Using PSK v1")
            psk, psk_id = self._psk_id_v1(identity_or_hint, server_side)
        else:
            print("Using PSK v2")
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
