from enum import Enum, auto
import json
import Cryptodome.Util.Padding as padding

from Cryptodome.Cipher import AES
from hashlib import md5

class TuyaCipherKeyChoice(Enum):
    AUTHKEY = auto()
    SECKEY = auto()


class TuyaCipher(object):
    def __init__(self, authkey: bytes):
        self.authkey = authkey

    def set_seckey(self, seckey: bytes):
        self.seckey = seckey

    def encrypt(self, data: dict, key_choice: TuyaCipherKeyChoice = TuyaCipherKeyChoice.AUTHKEY) -> bytes:
        jsondata = json.dumps(data, separators=(",",":"))
        jsondata = padding.pad(jsondata.encode("utf-8"), block_size=16)
        cipher = self._build_cipher(key_choice)
        encrypted = cipher.encrypt(jsondata)
        return encrypted

    def decrypt(self, data: bytes, key_choice: TuyaCipherKeyChoice = TuyaCipherKeyChoice.AUTHKEY) -> bytes:
        return self.__decrypt_with_retry(data, key_choice)

    def sign_server(self, params: dict, key_choice: TuyaCipherKeyChoice = TuyaCipherKeyChoice.AUTHKEY) -> str:
        return self.sign_client(params, key_choice)[8:24]

    def sign_client(self, params: dict, key_choice: TuyaCipherKeyChoice = TuyaCipherKeyChoice.AUTHKEY) -> str:
        sorted_params = sorted(list(params.items()))
        body = "||".join([f"{k}={v}" for k, v in sorted_params]) + "||"
        key = self.__get_key_by_choice(key_choice)
        signature_body = body.encode("utf-8") + key
        return md5(signature_body).hexdigest()

    def __decrypt_with_retry(self, data: bytes, key_choice: TuyaCipherKeyChoice = TuyaCipherKeyChoice.AUTHKEY, retry: bool = True) -> bytes:
        cipher = self._build_cipher(key_choice)
        decrypted = cipher.decrypt(data)

        # if decrypted[-2:] == b"\x0d\x0a":
        #     print("Decrypted data contained newline")
        #     decrypted = decrypted[:-2]

        try:
            return padding.unpad(decrypted, block_size=16)
        except Exception as e:
            print(f"Decryption failed due to padding error with key choice {key_choice}. ", end="")
            if not retry:
                print(f"Retrying is false - bailing out")
                raise e
            print("Retrying with other key choice")
            key_choice = TuyaCipherKeyChoice.AUTHKEY if key_choice == TuyaCipherKeyChoice.SECKEY else TuyaCipherKeyChoice.SECKEY
            return self.__decrypt_with_retry(data, key_choice, False)

    def _build_cipher(self, key_choice: TuyaCipherKeyChoice):
        key = self.__get_key_by_choice(key_choice)
        return AES.new(key[:16], AES.MODE_ECB)

    def __get_key_by_choice(self, key_choice: TuyaCipherKeyChoice):
        return self.authkey if key_choice == TuyaCipherKeyChoice.AUTHKEY else self.seckey
