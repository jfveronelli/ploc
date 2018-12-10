# coding:utf-8
from crossknight.ploc.domain import Note
from datetime import datetime
from unittest import TestCase


class ModuleTest(TestCase):
    FILENAME_ENCRYPTED = "01d80488a18e42e6a2767b140d45ddb9.md"
    FILENAME_PLAIN = "01d80488a18e42e6a2767b140d45ddc9.md"

    def __read_file(self, filename):
        with open("resources/" + filename, "r") as file:
            return file.read()

    def testReadNote(self):
        date = datetime.now()
        txt = self.__read_file(self.FILENAME_ENCRYPTED)

        note = Note.from_str(self.FILENAME_ENCRYPTED, date, txt)

        self.assertEqual(str, type(note.uuid))
        self.assertEqual("01d80488a18e42e6a2767b140d45ddb9", note.uuid)
        self.assertEqual(date, note.date)
        self.assertEqual(str, type(note.title))
        self.assertEqual("Aaaaa", note.title)
        self.assertEqual(1, len(note.tags))
        self.assertEqual(str, type(note.tags[0]))
        self.assertEqual("!today", note.tags[0])
        self.assertEqual(str, type(note.crypto.salt))
        self.assertEqual("8306ef737874bd0cf8e2f2b5ff7a2ec5", note.crypto.salt)
        self.assertEqual(str, type(note.crypto.iv))
        self.assertEqual("9ab105d4c753280ed7e9e5f9efe839d5", note.crypto.iv)
        self.assertEqual(str, type(note.crypto.hmac))
        self.assertEqual("f3276c88bce9ec0e559fe07a39d1c3aac551d635679c25dc07322b70ab6eb825", note.crypto.hmac)
        self.assertEqual(str, type(note.text))
        self.assertEqual("QjyW7OaUyP7M2WR81CH8Eg==", note.text)

    def testDecryptNote(self):
        note = Note.from_str(self.FILENAME_ENCRYPTED, datetime.now(), self.__read_file(self.FILENAME_ENCRYPTED))

        result = note.decrypt("hola")

        self.assertTrue(result)
        self.assertIsNone(note.crypto)
        self.assertEqual(str, type(note.text))
        self.assertEqual("Hola mundo!", note.text)

    def testEncryptAndDecryptNote(self):
        note = Note.from_str(self.FILENAME_PLAIN, datetime.now(), self.__read_file(self.FILENAME_PLAIN))

        result = note.encrypt("hola")

        self.assertTrue(result)
        self.assertEqual(str, type(note.crypto.salt))
        self.assertEqual(32, len(note.crypto.salt))
        self.assertEqual(str, type(note.crypto.iv))
        self.assertEqual(32, len(note.crypto.iv))
        self.assertEqual(str, type(note.crypto.hmac))
        self.assertEqual(64, len(note.crypto.hmac))
        self.assertEqual(str, type(note.text))
        self.assertTrue(len(note.text) > 14)

        result = note.decrypt("hola")

        self.assertTrue(result)
        self.assertIsNone(note.crypto)
        self.assertEqual(str, type(note.text))
        self.assertEqual("Hola mundo!", note.text)

    def testWriteNote(self):
        txt = self.__read_file(self.FILENAME_ENCRYPTED)
        note = Note.from_str(self.FILENAME_ENCRYPTED, datetime.now(), txt)

        result = str(note)

        self.assertEqual(str, type(txt))
        self.assertEqual(txt, result)
