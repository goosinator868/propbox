# Copyright (c) 2017 Future Gadget Laboratories.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# +---------------------+
# | Third-party imports |
# +---------------------+

from google.appengine.ext import ndb


# +------------------------+
# | Item Class and Helpers |
# +------------------------+

class List(ndb.Model):
    name = ndb.StringProperty(required=True)
    owner = ndb.KeyProperty(required=True)
    items = ndb.KeyProperty(repeated=True)
    public = ndb.BooleanProperty(default=False)


class Item(ndb.Model):
    '''Describes the structure of an "item" in the warehouse.'''
    creator_id = ndb.StringProperty(required=True)
    creator_name = ndb.StringProperty(required=True)
    updated = ndb.DateTimeProperty(auto_now_add=True)
    name = ndb.StringProperty(required=True)
    image_url = ndb.StringProperty(required=False)
    description = ndb.TextProperty(required=False)
    qr_code = ndb.IntegerProperty(required=False)
    item_type = ndb.StringProperty(required=True)
    item_color = ndb.StringProperty(repeated=True)
    condition = ndb.StringProperty(required=True)
    clothing_size_string = ndb.StringProperty(required=False)
    clothing_size_num = ndb.StringProperty(required=False)
    clothing_article_type = ndb.StringProperty(required=False)
    tags = ndb.StringProperty(repeated=True)
    checked_out = ndb.BooleanProperty(default=False)
    checked_out_reason = ndb.StringProperty(default="")
    checked_out_by = ndb.StringProperty(default="")
    checked_out_by_name = ndb.StringProperty(default="")
    #Newer Versions are children. Use Item.key.parent() to get older version.
    child = ndb.KeyProperty(required=False)
    #deleted is True if an item was deleted by a user but has not yet been purged from the system.
    deleted = ndb.BooleanProperty(required=True, default=False)
    marked_for_deletion = ndb.BooleanProperty(required=True, default=False)
    #outdated is True if there is a newer version to be shown; items with outdated=True will not be displayed.
    outdated = ndb.BooleanProperty(required=True, default=False)
    approved = ndb.BooleanProperty(required=True, default=False)
    suggested_edits = ndb.KeyProperty(required=False,repeated=True)
    is_suggestion = ndb.BooleanProperty(required=True, default=False)
    suggested_by = ndb.StringProperty(required=True, default="")

#Returns a clone of a given item.
def cloneItem(oldItem, parentKey=None):
    return Item(creator_id=oldItem.creator_id,
        creator_name=oldItem.creator_name,
        name=oldItem.name,
        description=oldItem.description,
        qr_code=oldItem.qr_code,
        approved=oldItem.approved,
        image_url=oldItem.image_url,
        parent=parentKey,
        item_type=oldItem.item_type,
        condition=oldItem.condition,
        clothing_size_string=oldItem.clothing_size_string,
        clothing_size_num=oldItem.clothing_size_num,
        clothing_article_type=oldItem.clothing_article_type,
        tags=oldItem.tags,
        checked_out = oldItem.checked_out,
        checked_out_reason = oldItem.checked_out_reason,
        checked_out_by = oldItem.checked_out_by,
        checked_out_by_name = oldItem.checked_out_by_name)


# +----------------------------+
# | User Permissions Constants |
# +----------------------------+

# Only these values should be stored in the User ==> permissions field.
STANDARD_USER = "Standard user"
TRUSTED_USER = "Trusted user"
ADMIN = "Admin"
PENDING_USER = "Pending user" # Pending user is for users who have recently joined the site, awaiting admin approval
DEACTIVATED_USER = "Deactivated user" # user has been deactivated by an admin


# +---------------+
# | Miscellaneous |
# +---------------+

possible_permissions = set([STANDARD_USER, TRUSTED_USER, ADMIN, PENDING_USER, DEACTIVATED_USER])

class User(ndb.Model):
    name = ndb.StringProperty(required=True)
    permissions = ndb.StringProperty(required=True)
