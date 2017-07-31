"""
Create a basic admin interface that can be accessed at /admin Very
basic for now but could be extended in the future. For now it's mostly
useful to browse the database.

Note that right now, writing will corrupt the item due to JSON
fields not being understood. Therefore edit operations have been
disabled.
"""

import flask_admin as admin
from flask_admin.contrib.peewee import ModelView

from .db import Entry, EntryChange, Logbook, LogbookChange, EntryLock, Attachment


class LogbookAdmin(ModelView):
    inline_models = (Logbook,)
    column_list = ["id", "created_at", "last_changed_at", "name", "description", "attributes", "parent"]
    can_view_details = True
    can_create = False
    can_delete = True
    can_edit = False

    column_formatters = {
        "attributes": lambda _1, _2, entry, _3: ", ".join(u.get("name") for u in entry.attributes)
    }


class LogbookChangeAdmin(ModelView):
    # inline_models = (Entry, )
    can_view_details = True
    can_create = False
    can_delete = False
    can_edit = False

    column_list = ['id', 'entry', 'timestamp', 'changed', 'change_authors', 'change_ip']
    column_sortable_list = ('timestamp', )



class EntryAdmin(ModelView):
    inline_models = (Entry, )
    can_view_details = True
    can_create = False
    can_delete = True
    can_edit = False

    column_list = ['id', 'created_at', 'last_changed_at', 'title', 'logbook', 'authors', 'follows']
    column_sortable_list = ('created_at', 'last_changed_at', 'logbook', 'follows')
    column_searchable_list = ('title',)

    column_formatters = {
        "authors": lambda _1, _2, entry, _3: ", ".join(u.get("name") for u in entry.authors)
    }


class EntryChangeAdmin(ModelView):
    # inline_models = (Entry, )
    can_view_details = True
    can_create = False
    can_delete = False
    can_edit = False

    column_list = ['id', 'entry', 'timestamp', 'changed', 'change_authors', 'change_ip']
    column_sortable_list = ('entry', 'timestamp', )


class EntryLockAdmin(ModelView):
    can_view_details = True
    can_create = False
    can_delete = True
    can_edit = False

    column_list = ['id', 'entry', 'created_at', 'exipires_at', 'owned_by_ip', 'cancelled_at', 'cancelled_by_ip']
    column_sortable_list = ('entry', 'created_at', 'expires_at', 'cancelled_at')


class AttachmentAdmin(ModelView):
    can_view_details = True
    can_create = False
    can_delete = True
    can_edit = False

    column_list = ['id', 'entry', 'timestamp', 'filename', 'path', 'content_type']
    column_sortable_list = ('entry', 'timestamp')


def setup_admin(app):
    adm = admin.Admin(app, name='Elogy')
    adm.add_view(LogbookAdmin(Logbook))
    adm.add_view(LogbookChangeAdmin(LogbookChange))
    adm.add_view(EntryAdmin(Entry))
    adm.add_view(EntryChangeAdmin(EntryChange))
    adm.add_view(EntryLockAdmin(EntryLock))
    adm.add_view(AttachmentAdmin(Attachment))
