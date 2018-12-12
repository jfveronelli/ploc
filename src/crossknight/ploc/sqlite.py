# coding:utf-8
from crossknight.ploc.domain import Note
from crossknight.ploc.domain import NoteCrypto
from crossknight.ploc.domain import NoteType
from crossknight.ploc.domain import ulist
from datetime import datetime
from peewee import CharField
from peewee import DateTimeField
from peewee import FixedCharField
from peewee import ForeignKeyField
from peewee import Model
from peewee import SqliteDatabase
from peewee import TextField


_DB_FILENAME = "ploc.db"
_ACCENTED_CHARS_TRANSLATION = str.maketrans({"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u"})


_db = SqliteDatabase(_DB_FILENAME, pragmas={
    "journal_mode": "wal",
    "foreign_keys": 1,
    "ignore_check_constraints": 0
})


def _comparable(txt):
    return txt.lower().translate(_ACCENTED_CHARS_TRANSLATION)


class _BaseModel(Model):
    class Meta:
        database = _db


class _Note(_BaseModel):
    class Meta:
        table_name = "note"
    uuid = FixedCharField(primary_key=True, max_length=32)
    date = DateTimeField()
    title = CharField()
    tags = TextField(null=True)
    type = CharField(index=True)
    crypto = CharField(null=True)
    text = TextField()


class _NoteTag(_BaseModel):
    class Meta:
        table_name = "note_tag"
        primary_key = False
        indexes = ((("uuid", "name"), True),)
    uuid = ForeignKeyField(_Note, on_delete="CASCADE", index=True)
    name = CharField(index=True)


class _RemovedNote(_BaseModel):
    class Meta:
        table_name = "removed_note"
    uuid = FixedCharField(primary_key=True, max_length=32)
    date = DateTimeField()


class Provider(object):
    def __init__(self):
        self.filename = _DB_FILENAME
        _db.create_tables([_Note, _NoteTag, _RemovedNote])

    @classmethod
    def _note2models(cls, note):
        tags = None if not note.tags else "\n".join(note.tags)
        crypto = None if not note.crypto else note.crypto.salt + note.crypto.iv + note.crypto.hmac
        noteModel = _Note(uuid=note.uuid, date=note.date, title=note.title, tags=tags, type=note.type.value,
                          crypto=crypto, text=note.text)
        tagModels = []
        for tag in note.tags:
            tagModels.append(_NoteTag(uuid=note.uuid, name=tag))
        return noteModel, tagModels

    # noinspection PyMethodMayBeStatic
    def tags(self):
        return sorted(map(lambda t: t[0], _NoteTag.select(_NoteTag.name).distinct().tuples()), key=_comparable)

    # noinspection PyMethodMayBeStatic
    def get(self, uuid):
        entity = _Note.get_by_id(uuid)
        note = Note()
        note.uuid = entity.uuid
        note.date = entity.date
        note.title = entity.title
        note.type = NoteType(entity.type)
        note.text = entity.text
        if entity.tags:
            note.tags = entity.tags.split("\n")
        if entity.crypto:
            note.crypto = NoteCrypto(entity.crypto[:32], entity.crypto[32:64], entity.crypto[64:])
        return note

    @_db.atomic()
    def add(self, note):
        noteModel, tagModels = self._note2models(note)
        noteModel.save(force_insert=True)
        for model in tagModels:
            model.save(force_insert=True)

    @_db.atomic()
    def update(self, note):
        noteModel, tagModels = self._note2models(note)
        noteModel.save()
        _NoteTag.delete().where(_NoteTag.uuid == note.uuid).execute()
        for model in tagModels:
            model.save(force_insert=True)

    @_db.atomic()
    def remove(self, uuid, date=None):
        _Note.delete().where(_Note.uuid == uuid).execute()
        _RemovedNote(uuid=uuid, date=date or datetime.now()).save(force_insert=True)

    @_db.atomic()
    def update_tag(self, tag, newTags=None):
        uuids = [t[0] for t in _NoteTag.select(_NoteTag.uuid).where(_NoteTag.name == tag).distinct().tuples()]
        if uuids:
            date = datetime.now()
            for uuid in uuids:
                tags = _Note.select(_Note.tags).where(_Note.uuid == uuid).tuples().get()[0].split("\n")
                pos = tags.index(tag)
                del tags[pos]
                if newTags:
                    for newTag in reversed(newTags):
                        tags.insert(pos, newTag)
                    tags = ulist(tags)
                _Note.update(date=date, tags="\n".join(tags)).where(_Note.uuid == uuid).execute()
            _NoteTag.delete().where(_NoteTag.name == tag).execute()
            if newTags:
                tags = []
                for tag in newTags:
                    for uuid in uuids:
                        tags.append({"uuid": uuid, "name": tag})
                _NoteTag.insert_many(tags).on_conflict_ignore().execute()

    @classmethod
    def close(cls):
        _db.close()
