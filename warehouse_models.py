from google.appengine.ext import ndb

class Item(ndb.Model):
    '''Describes the structure of an "item" in the warehouse.'''
    creator_id = ndb.StringProperty(required=True)
    updated = ndb.DateTimeProperty(auto_now_add=True)
    name = ndb.StringProperty(required=True)
    description = ndb.StringProperty(required=False)
    qr_code = ndb.IntegerProperty(required=False)
    #older_version and newer_version hold keys to other versions of the item in the database.
    older_version = ndb.KeyProperty(required=False)
    newer_version = ndb.KeyProperty(required=False)
    #deleted is True if an item was deleted by a user but has not yet been purged from the system.
    deleted = ndb.BooleanProperty(required=True,default=False)
    #outdated is True if there is a newer version to be shown; items with outdated=True will not be displayed.
    outdated = ndb.BooleanProperty(required=True,default=False)