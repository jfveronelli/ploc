# coding:utf-8
from crossknight.ploc.domain import is_uuid
from crossknight.ploc.domain import Note
from crossknight.ploc.domain import NoteCrypto
from crossknight.ploc.domain import NoteStatus
from crossknight.ploc.domain import NoteSummary
from crossknight.ploc.domain import NoteType
from crossknight.ploc.domain import ulist
from datetime import datetime
from datetime import timedelta
from peewee import CharField
from peewee import DateTimeField
from peewee import FixedCharField
from peewee import ForeignKeyField
from peewee import IntegrityError
from peewee import Model
from peewee import SqliteDatabase
from peewee import TextField
from zipfile import ZIP_DEFLATED
from zipfile import ZipFile
from zipfile import ZipInfo


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
    def __note2models(cls, note):
        tags = None if not note.tags else "\n".join(note.tags)
        crypto = None if not note.crypto else note.crypto.salt + note.crypto.iv + note.crypto.hmac
        noteModel = _Note(uuid=note.uuid, date=note.date, title=note.title, tags=tags, type=note.type.value,
                          crypto=crypto, text=note.text)
        tagModels = []
        for tag in note.tags:
            tagModels.append(_NoteTag(uuid=note.uuid, name=tag))
        return noteModel, tagModels

    @classmethod
    def __model2note(cls, model):
        note = Note()
        note.uuid = model.uuid
        note.date = model.date
        note.title = model.title
        note.tags = cls.__unpack_tags(model.tags)
        note.type = NoteType(model.type)
        note.crypto = cls.__unpack_crypto(model.crypto)
        note.text = model.text
        return note

    @classmethod
    def __unpack_tags(cls, text):
        return text.split("\n") if text else []

    @classmethod
    def __unpack_crypto(cls, text):
        return NoteCrypto(text[:32], text[32:64], text[64:]) if text else None

    @classmethod
    def __localtimetuple(cls, ndate):
        local = ndate.astimezone()
        if round(local.microsecond / 1000000) >= 1:
            local += timedelta(seconds=1)
        return local.year, local.month, local.day, local.hour, local.minute, local.second

    @classmethod
    def __is_note_file(cls, filename):
        return len(filename) == 35 and filename.endswith(".md") and is_uuid(filename[:32])

    @classmethod
    def list(cls, tags=None, ntype=None, text=None):
        query = _Note.select(_Note.uuid, _Note.date, _Note.title, _Note.tags, _Note.type, _Note.crypto)
        andFilters = []
        if tags:
            subquery = _NoteTag.select(_NoteTag.uuid).where(_NoteTag.name.in_(tags)).distinct()
            andFilters.append(_Note.uuid.in_(subquery))
        if ntype:
            andFilters.append(_Note.type == ntype.value)
        if text:
            andFilters.append(_Note.title.contains(text) | _Note.tags.contains(text) |
                              (_Note.crypto.is_null() & _Note.text.contains(text)))
        if andFilters:
            query = query.where(*tuple(andFilters))

        summaries = []
        for (uuid, ndate, title, tags, ntype, crypto) in query.tuples():
            tags = cls.__unpack_tags(tags)
            crypto = cls.__unpack_crypto(crypto)
            summaries.append(NoteSummary(uuid, ndate, title, tags, NoteType(ntype), crypto))
        summaries.sort(key=lambda s: _comparable(s.title))
        return summaries

    # noinspection PyMethodMayBeStatic
    def tags(self):
        return sorted(map(lambda t: t[0], _NoteTag.select(_NoteTag.name).distinct().tuples()), key=_comparable)

    def get(self, uuid):
        return self.__model2note(_Note.get_by_id(uuid))

    @_db.atomic()
    def add(self, note):
        noteModel, tagModels = self.__note2models(note)
        noteModel.save(force_insert=True)
        for model in tagModels:
            model.save(force_insert=True)

    @_db.atomic()
    def update(self, note):
        noteModel, tagModels = self.__note2models(note)
        noteModel.save()
        _NoteTag.delete().where(_NoteTag.uuid == note.uuid).execute()
        for model in tagModels:
            model.save(force_insert=True)

    @_db.atomic()
    def remove(self, uuid, ndate=None):
        _Note.delete().where(_Note.uuid == uuid).execute()
        _RemovedNote(uuid=uuid, date=ndate or datetime.now()).save(force_insert=True)

    @_db.atomic()
    def update_tag(self, tag, newTags=None):
        uuids = [t[0] for t in _NoteTag.select(_NoteTag.uuid).where(_NoteTag.name == tag).distinct().tuples()]
        if uuids:
            ndate = datetime.now()
            for uuid in uuids:
                tags = _Note.select(_Note.tags).where(_Note.uuid == uuid).tuples().get()[0].split("\n")
                pos = tags.index(tag)
                del tags[pos]
                if newTags:
                    for newTag in reversed(newTags):
                        tags.insert(pos, newTag)
                    tags = ulist(tags)
                _Note.update(date=ndate, tags="\n".join(tags)).where(_Note.uuid == uuid).execute()
            _NoteTag.delete().where(_NoteTag.name == tag).execute()
            if newTags:
                tags = []
                for tag in newTags:
                    for uuid in uuids:
                        tags.append({"uuid": uuid, "name": tag})
                _NoteTag.insert_many(tags).on_conflict_ignore().execute()

    def export(self, uuids, filepath):
        with ZipFile(filepath, "w", ZIP_DEFLATED) as zipped:
            for uuid in uuids:
                note = self.get(uuid)
                fileinfo = ZipInfo(uuid + ".md", self.__localtimetuple(note.date))
                zipped.writestr(fileinfo, str(note).encode("utf-8"))

    def import_from(self, filepath):
        imported = 0
        duplicated = 0
        corrupted = 0
        with ZipFile(filepath) as zipped:
            for fileinfo in filter(lambda i: self.__is_note_file(i.filename), zipped.infolist()):
                ndate = datetime(*fileinfo.date_time)
                with zipped.open(fileinfo) as notefile:
                    note = Note.from_text(fileinfo.filename, ndate, notefile.read())
                if note:
                    try:
                        self.add(note)
                        imported += 1
                    except IntegrityError:
                        duplicated += 1
                else:
                    corrupted += 1
        return imported, duplicated, corrupted

    # noinspection PyMethodMayBeStatic
    def state(self):
        result = {}
        for (uuid, ndate) in _RemovedNote.select(_RemovedNote.uuid, _RemovedNote.date).tuples():
            result[uuid] = NoteStatus(uuid, ndate, False)
        for (uuid, ndate) in _Note.select(_Note.uuid, _Note.date).tuples():
            result[uuid] = NoteStatus(uuid, ndate, True)
        return result

    @_db.atomic()
    def wipe(self):
        _Note.delete().execute()
        _NoteTag.delete().execute()
        _RemovedNote.delete().execute()

    @classmethod
    def close(cls):
        _db.close()
