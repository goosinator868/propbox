from google.appengine.ext import ndb

class Item(ndb.Model):
    '''Describes the structure of an "item" in the warehouse.'''
    creator_id = ndb.StringProperty(required=True)
    updated = ndb.DateTimeProperty(auto_now_add=True)
    name = ndb.StringProperty(required=True)
    image = ndb.BlobProperty(required=False)
    description = ndb.StringProperty(required=False)
    qr_code = ndb.IntegerProperty(required=False)
