# coding:utf-8
from argon2pure import argon2
from argon2pure import ARGON2D
from base64 import standard_b64decode
from base64 import standard_b64encode
from binascii import hexlify
from collections import OrderedDict
from datetime import datetime
from enum import Enum
import hmac as hmaclib
from pyaes import AESModeOfOperationCBC
from pyaes import Decrypter
from pyaes import Encrypter
from re import compile
from secrets import token_bytes
from uuid import uuid4
from yaml import dump_all
from yaml import safe_load
from yaml import SafeDumper


_UUID = compile(r"^[0-9a-f]{32}\Z")


def _is_uuid(name):
    return bool(_UUID.match(name))


def _pass2key(password, salt_b):
    pass_b = bytes(password, "utf-8")
    return argon2(pass_b, salt_b, 10, 1024, 1, tag_length=32, type_code=ARGON2D)


class _OrderedSafeDumper(SafeDumper):
    def increase_indent(self, flow=False, indentless=False):
        return super(_OrderedSafeDumper, self).increase_indent(flow, False)

    @staticmethod
    def ordered_dict_representer(dumper, data):
        return dumper.represent_mapping("tag:yaml.org,2002:map", data.items())

_OrderedSafeDumper.add_representer(OrderedDict, _OrderedSafeDumper.ordered_dict_representer)


class _NoteCrypto(object):
    def __init__(self, salt, iv, hmac):
        self.salt = salt
        self.iv = iv
        self.hmac = hmac


class NoteType(Enum):
    BASIC = "basic"


class Note(object):
    __HDR_START = "```yaml\n"
    __HDR_END = "\n```\n\n"

    def __init__(self):
        self.uuid = hexlify(uuid4().bytes).decode("ascii")
        self.date = datetime.now()
        self.title = ""
        self.tags = []
        self.type = NoteType.BASIC
        self.crypto = None
        self.text = ""

    def __str__(self):
        noteDict = OrderedDict([("title", self.title), ("tags", self.tags)])
        if self.type != NoteType.BASIC:
            noteDict["type"] = self.type.value
        if self.crypto:
            cryptoDict = OrderedDict([("salt", self.crypto.salt), ("iv", self.crypto.iv), ("hmac", self.crypto.hmac)])
            noteDict["crypto"] = cryptoDict
        yaml = dump_all([noteDict], default_flow_style=False, Dumper=_OrderedSafeDumper).strip()
        return self.__HDR_START + yaml + self.__HDR_END + self.text

    @classmethod
    def from_str(cls, filename, date, txt):
        if len(filename) < 32 or not _is_uuid(filename[:32]) or not txt or not txt.startswith(cls.__HDR_START)\
                or txt.index(cls.__HDR_END) < 0:
            return None

        endPos = txt.index(cls.__HDR_END)
        noteDict = safe_load(txt[len(cls.__HDR_START):endPos])

        note = Note()
        note.uuid = filename[:32]
        note.date = date
        note.title = noteDict["title"]
        note.tags = noteDict["tags"]
        if "crypto" in noteDict:
            cryptoDict = noteDict["crypto"]
            note.crypto = _NoteCrypto(cryptoDict["salt"], cryptoDict["iv"], cryptoDict["hmac"])
        note.text = txt[endPos + len(cls.__HDR_END):]
        return note

    def encrypt(self, password):
        if self.crypto:
            return False

        salt = token_bytes(16)
        iv = token_bytes(16)
        key = _pass2key(password, salt)

        encrypter = Encrypter(AESModeOfOperationCBC(key, iv))
        cipher = encrypter.feed(self.text.encode("utf-8"))
        cipher += encrypter.feed()

        hmac = hmaclib.new(key, iv, "sha256")
        hmac.update(cipher)

        cipher = standard_b64encode(cipher).decode("ascii")
        self.crypto = _NoteCrypto(hexlify(salt).decode("ascii"), hexlify(iv).decode("ascii"), hmac.hexdigest())
        self.text = cipher
        return True

    def decrypt(self, password):
        if not self.crypto:
            return False

        key = _pass2key(password, bytes.fromhex(self.crypto.salt))
        iv = bytes.fromhex(self.crypto.iv)
        cipher = standard_b64decode(self.text)
        hmac = hmaclib.new(key, iv, "sha256")
        hmac.update(cipher)
        if not hmaclib.compare_digest(bytes.fromhex(self.crypto.hmac), hmac.digest()):
            return False

        decrypter = Decrypter(AESModeOfOperationCBC(key, iv))
        text = decrypter.feed(cipher)
        text += decrypter.feed()
        text = text.decode("utf-8")

        self.crypto = None
        self.text = text
        return True
