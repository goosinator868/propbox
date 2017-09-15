from google.appengine.ext import ndb

class Item(ndb.Model):
    '''Describes the structure of an "item" in the warehouse.'''
    creator_id = ndb.StringProperty(required=True)
    creator_name = ndb.StringProperty(required=True)
    updated = ndb.DateTimeProperty(auto_now_add=True)
    name = ndb.StringProperty(required=True)
    image = ndb.BlobProperty(required=False)
    description = ndb.TextProperty(required=False)
    qr_code = ndb.IntegerProperty(required=False)
    item_type = ndb.StringProperty(required=True)
    condition = ndb.StringProperty(required=True)
    clothing_size_string = ndb.StringProperty(required=False)
    clothing_size_num = ndb.StringProperty(required=False)
    clothing_article_type = ndb.StringProperty(required=False)
    tags = ndb.StringProperty(repeated=True)
    checked_out = ndb.BooleanProperty(default=False)
    checked_out_reason = ndb.StringProperty(default="")
    checked_out_by = ndb.StringProperty(default="")
    #Newer Versions are children. Use Item.key.parent() to get older version.
    child = ndb.KeyProperty(required=False)
    #deleted is True if an item was deleted by a user but has not yet been purged from the system.
    deleted = ndb.BooleanProperty(required=True, default=False)
    #outdated is True if there is a newer version to be shown; items with outdated=True will not be displayed.
    outdated = ndb.BooleanProperty(required=True, default=False)
    approved = ndb.BooleanProperty(required=True, default=False)
    orphan = ndb.BooleanProperty(required=True, default=False)

#Returns a clone of a given item.
def cloneItem(oldItem, parentKey=None):
    return Item(creator_id=oldItem.creator_id,
        creator_name=oldItem.creator_name,
        name=oldItem.name,
        description=oldItem.description,
        qr_code=oldItem.qr_code,
        approved=oldItem.approved,
        image=oldItem.image,
        parent=parentKey,
        item_type=oldItem.item_type,
        condition=oldItem.condition,
        clothing_size_string=oldItem.clothing_size_string,
        clothing_size_num=oldItem.clothing_size_num,
        clothing_article_type=oldItem.clothing_article_type,
        tags=oldItem.tags,
        checked_out = oldItem.checked_out,
        checked_out_reason = oldItem.checked_out_reason,
        checked_out_by = oldItem.checked_out_by)

# Only these values should be stored in the User ==> permissions field.
STANDARD_USER = "STANDARD_USER"
TRUSTED_USER = "TRUSTED_USER"
ADMIN = "ADMIN"

possible_permissions = set([STANDARD_USER, TRUSTED_USER, ADMIN])

class User(ndb.Model):
    name = ndb.StringProperty(required=True)
    permissions = ndb.StringProperty(required=True)