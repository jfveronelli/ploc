# coding:utf-8
from crossknight.ploc.domain import Note
from crossknight.ploc.domain import NoteCrypto
from crossknight.ploc.domain import NoteType
from crossknight.ploc.sqlite import Provider
from os import remove
from peewee import DoesNotExist
from peewee import IntegrityError
from unittest import TestCase


class ModuleTest(TestCase):

    def setUp(self):
        self.provider = Provider()

    def tearDown(self):
        self.provider.close()
        remove(self.provider.filename)

    def testList(self):
        note1 = Note()
        self.provider.add(note1)
        note2 = Note()
        note2.tags = ["AAA", "BBB"]
        note2.crypto = NoteCrypto("8306ef737874bd0cf8e22225ff7a2ec5", "9ab105d4c753280ed7e9e5f9efe839d5",
                                  "f3276c88bce9ec0e559fe07a39d1c3aac551d635679c25dc07322b70ab6eb825")
        note2.text = "Hola Mundo!"
        self.provider.add(note2)
        note3 = Note()
        note3.title = "ArmuNdo"
        note3.tags = ["AAA", "BBB"]
        self.provider.add(note3)
        note4 = Note()
        note4.title = "Alnundo"
        note4.tags = ["AAA", "BBB"]
        note4.text = "Hola Mundo!"
        self.provider.add(note4)
        note5 = Note()
        note5.title = "Ágdundo"
        note5.tags = ["AAA", "BBB", "EDMUNDO"]
        note5.crypto = NoteCrypto("8306ef737874bd0cf8e22225ff7a2ec5", "9ab105d4c753280ed7e9e5f9efe839d5",
                                  "f3276c88bce9ec0e559fe07a39d1c3aac551d635679c25dc07322b70ab6eb825")
        self.provider.add(note5)

        res = self.provider.list(["BBB", "XXX"], NoteType.BASIC, "mUn")

        self.assertEqual(3, len(res))
        self.assertEqual(note5.uuid, res[0].uuid)
        self.assertEqual(note5.date, res[0].date)
        self.assertEqual(note5.title, res[0].title)
        self.assertEqual(note5.tags, res[0].tags)
        self.assertEqual(note5.type, res[0].type)
        self.assertEqual(note5.crypto, res[0].crypto)
        self.assertEqual(note4.uuid, res[1].uuid)
        self.assertEqual(note4.date, res[1].date)
        self.assertEqual(note4.title, res[1].title)
        self.assertEqual(note4.tags, res[1].tags)
        self.assertEqual(note4.type, res[1].type)
        self.assertEqual(note4.crypto, res[1].crypto)
        self.assertEqual(note3.uuid, res[2].uuid)
        self.assertEqual(note3.date, res[2].date)
        self.assertEqual(note3.title, res[2].title)
        self.assertEqual(note3.tags, res[2].tags)
        self.assertEqual(note3.type, res[2].type)
        self.assertEqual(note3.crypto, res[2].crypto)

    def testAddAndGetNote(self):
        note = Note()
        note.title = "AAAA"
        note.tags = ["BBB", "CCC"]
        note.crypto = NoteCrypto("8306ef737874bd0cf8e2f2b5ff7a2ec5", "9ab105d4c753280ed7e9e5f9efe839d5",
                "f3276c88bce9ec0e559fe07a39d1c3aac551d635679c25dc07322b70ab6eb825")
        note.text = "Hola mundo!"

        self.provider.add(note)
        res = self.provider.get(note.uuid)

        self.assertEqual(str, type(res.uuid))
        self.assertEqual(note.uuid, res.uuid)
        self.assertEqual(note.date, res.date)
        self.assertEqual(str, type(res.title))
        self.assertEqual(note.title, res.title)
        self.assertEqual(note.tags, res.tags)
        self.assertEqual(str, type(res.tags[0]))
        self.assertEqual(str, type(res.tags[1]))
        self.assertEqual(note.type, res.type)
        self.assertEqual(str, type(res.crypto.salt))
        self.assertEqual(note.crypto.salt, res.crypto.salt)
        self.assertEqual(str, type(res.crypto.iv))
        self.assertEqual(note.crypto.iv, res.crypto.iv)
        self.assertEqual(str, type(res.crypto.hmac))
        self.assertEqual(note.crypto.hmac, res.crypto.hmac)
        self.assertEqual(str, type(res.text))
        self.assertEqual(note.text, res.text)

    def testAddSameNoteTwiceMustFail(self):
        note = Note()
        self.provider.add(note)

        try:
            self.provider.add(note)
            self.fail("Expected an error")
        except IntegrityError:
            pass

    def testUpdateNote(self):
        note = Note()
        note.title = "Hola"
        note.tags = ["AAA", "CCC"]
        self.provider.add(note)
        note.title = "Chau"
        note.tags = ["BBB", "CCC"]

        self.provider.update(note)

        res = self.provider.get(note.uuid)
        self.assertEqual(note.title, res.title)
        self.assertEqual(note.tags, res.tags)

    def testRemoveNote(self):
        note = Note()
        self.provider.add(note)

        self.provider.remove(note.uuid)

        try:
            self.provider.get(note.uuid)
            self.fail("Expected an error")
        except DoesNotExist:
            pass

    def testTags(self):
        note1 = Note()
        note1.tags = ["master", "MÁCINTOSH"]
        note2 = Note()
        note2.tags = ["slave", "master"]
        self.provider.add(note1)
        self.provider.add(note2)

        tags = self.provider.tags()

        self.assertEqual(3, len(tags))
        self.assertEqual("MÁCINTOSH", tags[0])
        self.assertEqual("master", tags[1])
        self.assertEqual("slave", tags[2])

    def testUpdateTagToRemoveOnly(self):
        note1 = Note()
        note1.tags = ["AAA", "BBB"]
        self.provider.add(note1)
        note2 = Note()
        note2.tags = ["BBB", "CCC"]
        self.provider.add(note2)

        self.provider.update_tag("BBB")

        res1 = self.provider.get(note1.uuid)
        self.assertEqual(1, len(res1.tags))
        self.assertEqual(note1.tags[0], res1.tags[0])
        res2 = self.provider.get(note2.uuid)
        self.assertEqual(1, len(res2.tags))
        self.assertEqual(note2.tags[1], res2.tags[0])

    def testUpdateTagToRemoveAndAdd(self):
        note1 = Note()
        note1.tags = ["AAA", "BBB"]
        self.provider.add(note1)
        note2 = Note()
        note2.tags = ["BBB", "CCC"]
        self.provider.add(note2)

        self.provider.update_tag("BBB", ["DDD", "EEE"])

        res1 = self.provider.get(note1.uuid)
        self.assertEqual(3, len(res1.tags))
        self.assertEqual("AAA", res1.tags[0])
        self.assertEqual("DDD", res1.tags[1])
        self.assertEqual("EEE", res1.tags[2])
        res2 = self.provider.get(note2.uuid)
        self.assertEqual(3, len(res2.tags))
        self.assertEqual("DDD", res2.tags[0])
        self.assertEqual("EEE", res2.tags[1])
        self.assertEqual("CCC", res2.tags[2])

    def testState(self):
        note1 = Note()
        self.provider.remove(note1.uuid)
        note2 = Note()
        self.provider.add(note2)

        res = self.provider.state()

        self.assertEqual(2, len(res))
        self.assertEqual(note1.uuid, res[note1.uuid].uuid)
        self.assertIsNotNone(res[note1.uuid].date)
        self.assertFalse(res[note1.uuid].active)
        self.assertEqual(note2.uuid, res[note2.uuid].uuid)
        self.assertEqual(note2.date, res[note2.uuid].date)
        self.assertTrue(res[note2.uuid].active)

    def testWipe(self):
        note1 = Note()
        self.provider.remove(note1.uuid)
        note2 = Note()
        note2.tags = ["AAA", "BBB"]
        self.provider.add(note2)

        self.provider.wipe()

        self.assertFalse(self.provider.tags())
        self.assertFalse(self.provider.state())
