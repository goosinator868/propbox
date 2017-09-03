from google.appengine.ext import ndb

class Item(ndb.Model):
    '''Describes the structure of an "item" in the warehouse.'''
    creator_id = ndb.StringProperty(required=True)
    updated = ndb.DateTimeProperty(auto_now_add=True)
    name = ndb.StringProperty(required=True)
    description = ndb.StringProperty(required=False)
    qr_code = ndb.IntegerProperty(required=False)
    item_type = ndb.StringProperty(required=True)
    condition = ndb.StringProperty(required=True)
    clothing_size_string = ndb.StringProperty(required=False)
    clothing_size_num = ndb.StringProperty(required=False)
    clothing_article_type = ndb.StringProperty(required=False)
    tags = ndb.StringProperty(repeated=True)
