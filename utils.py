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


# +-------------------------+
# | Python built-in imports |
# +-------------------------+
import os
import requests
import logging
from hashlib import sha1
import base64

# +---------------------+
# | Third party imports |
# +---------------------+

from google.appengine.ext import ndb
from google.appengine.api import app_identity
from google.appengine.api import images
from google.appengine.ext import blobstore
import cloudstorage as gcs

# +---------------------+
# | First party imports |
# +---------------------+

from warehouse_models import Item, cloneItem, List


# +-----------------+
# | Item Exceptions |
# +-----------------+

class ItemDeletedException(Exception):
    '''Raised when trying to submit an edit to a deleted item.'''
    def __init__(self,*args,**kwargs):
        Exception.__init__(self,*args,**kwargs)

class ItemPurgedException(Exception):
    '''Raised when trying to submit an edit to an item that has been permanently deleted.'''
    def __init__(self,*args,**kwargs):
        Exception.__init__(self,*args,**kwargs)


# +-----------------------+
# | Transactional helpers |
# +-----------------------+

@ndb.transactional(xg=True, retries=1)
def commitDelete(item_key,user):
    item = item_key.get()
    if item.outdated:
        raise OutdatedEditException()
    if user.permissions=="Standard user":
        item.marked_for_deletion = True
    else:
        item.deleted = True
    item.suggested_by = user.name
    item.put()

@ndb.transactional(xg=True, retries=1)
def commitUnDelete(item_key):
    item = item_key.get()
    item.deleted = False
    item.marked_for_deletion = False
    item.suggested_by = ""
    item.put()

@ndb.transactional(xg=True, retries=1)
def commitPurge(item_key):
    toDelete = [item_key] + [suggestion for suggestion in item_key.get().suggested_edits]
    while item_key.parent():
        item_key = item_key.parent()
        toDelete.append(item_key)
    # logging.info("\n\n\n")
    # logging.info(toDelete)
    for k in toDelete:
        k.delete()

@ndb.transactional(xg=True, retries=1)
def commitEdit(old_key, new_item, suggestion=False):
    '''Stores the new item and ensures that the
       parent-child relationship is enforced between the
       old item and the new item.

       TRANSACTIONAL: This is transactional so all edits to the database
                      cannot be left in an unexpected state.

       SIDE EFFECT: Sets the parent of the new_item to be the old_key.

       Args:
            old_key: The key of the item that this is an edit to.
            new_item: The new version of the item to be commited.

       Returns:
            The key of the item that was commited, this could not be the new_item 
            since it may have been mutated to work with previous versions.
    '''
    old_item = old_key.get()
    # Check if item was deleted
    if old_item is None:
        raise ItemPurgedException()
    # Find newest version
    if old_item.outdated:
        while old_item.outdated:
            old_item = old_item.child.get()
        # Update the parent
        new_item = cloneItem(new_item, parentKey=old_item.key)
    # check if deleted but not purged
    if old_item.deleted:
        raise ItemDeletedException()
    old_item.outdated = not suggestion
    new_key = new_item.put()
    if suggestion:
        old_item.suggested_edits.append(new_key)
    else:
        old_item.child = new_key
    old_item.put()
    return new_item.key

@ndb.transactional(xg=True, retries=3)
def removeFromList(list_key, item_key):
    l = list_key.get()
    item = item_key.get();
    l.items.remove([i for i in l.items if i.get().qr_code == item.qr_code][0])
    l.put()

@ndb.transactional(retries=3)
def addToList(list_key, item_key):
    l = list_key.get()
    l.items.append(item_key)
    l.put()

def removeFromAllLists(item_key):
    lists = List.query().fetch()
    # NOTE: This still allows for a race if someone adds to a list
    # after this point in the function. This is okay since it will 
    # only lead to the number of items being off and is not worth
    # creating a huge transaction for every time.
    for l in lists:
        if item_key in l.items:
            removeFromList(l.key, item_key)

# +-----------------------+
# | Miscellaneous Helpers |
# +-----------------------+

def getImageHash(image_data):
    m = sha1()
    m.update(image_data)
    return m.hexdigest()

def saveImageInGCS(image_data):
    # ======================
    # Save file in GCS
    # ======================
    image_data = base64.b64decode(image_data)#image_data.encode('utf-8')
    bucket_name = os.environ.get('BUCKET_NAME',
                         app_identity.get_default_gcs_bucket_name())


    bucket = '/' + bucket_name
    filename = bucket + '/' + getImageHash(image_data) + '.png'
    write_retry_params = gcs.RetryParams(backoff_factor=1.1)
    gcs_file = gcs.open(filename,
                        'w',
                        content_type='image/png',
                        options={'x-goog-meta-foo': 'foo',
                                 'x-goog-meta-bar': 'bar'},
                        retry_params=write_retry_params)
    gcs_file.write(image_data)
    gcs_file.close()

    gcs_object_name = '/gs' + filename
    # logging.info(gcs_object_name)
    blob_key = blobstore.create_gs_key(gcs_object_name)
    image_url =  images.get_serving_url(blob_key)
    return image_url
    # ======================
    # End saving file to GCS
    # ======================

# Validates an html string using the w3 validator.
def validateHTML(html_string):
    # TODO disable when deployed

    # TODO: Currently, the w3 html validator is broken. Remove when the site is up and running again
    return html_string

    response = requests.post("https://validator.w3.org/nu/?out=json",
        data=html_string,
        headers={'Content-Type':'text/html; charset=utf-8'})
    messages = response.json()['messages']
    if messages:
        for m in messages:
            if m['type'] == 'error':
                messsage_for_human = u'Invalid HTML: {issue}\n{snippet} on line:{line}'.format(issue=m['message'], snippet=m['extract'],line=m['lastLine'])
                logging.error(messsage_for_human)
            else:
                messsage_for_human = u'Validator message: ' + str(m)
                logging.warning(messsage_for_human)
        return html_string + '<script>alert("{n} HTML errors found, check the logs for details");</script>'.format(n=len(messages))
    return html_string

# Finds the most recent version of an item.
def findUpdatedItem(item_key):
    updated = item_key.get()
    updated_key = item_key
    # Ensure item exists, if not find an ancestor that does.
    while updated is None and updated_key.parent():
        # Checks if item has been rolled back or deleted
        updated_key = item_key.parent()
        updated = updated_key.get()
    
    # If no ancestor exists the item has been deleted/purged
    # TODO test this case where item is deleted/purged
    if updated is None or updated_key is None:
        return None
    
    # We have a valid item, now ensure it is the most recent copy
    else:
        while updated.outdated:
            updated = updated.child.get()
    if updated.deleted:
        return None
    return updated

# Converts text list of tags to array of tags
def parseTags(tags_string):
    tags_list = []

    # Find newline character
    tag_end_index = tags_string.find("\n")

    # Check newline character exists in string
    while tag_end_index != -1:
        # Add tag to list
        tags_list.append(tags_string[:tag_end_index - 1].lower())
        # Shrink or delete string based on how much material is left in string
        if tag_end_index + 1 < len(tags_string):
            tags_string = tags_string[tag_end_index + 1:len(tags_string)]
        else:
            tags_string = ""

        tag_end_index = tags_string.find("\n")

    # Potentially still has a tag not covered. Adds last tag to list if possible
    if len(tags_string) != 0:
        tags_list.append(tags_string.lower())

    return tags_list

# Filters viewable items based on selected boxes in MainPage
def filterItems(item_name, item_type, item_condition, item_colors,
    item_color_grouping, costume_article, costume_size_string,
    costume_size_number, tags_filter, tag_grouping):
    # Check if costume or prop is selected individually
    if (item_type == "Costume"):
        if (len(costume_size_string) == 9):
            costume_size_string.append("N/A")
        elif (len(costume_size_string) == 0):
            costume_size_string.append("N/A")
            costume_size_string.append("XXS")
            costume_size_string.append("XS")
            costume_size_string.append("S")
            costume_size_string.append("M")
            costume_size_string.append("L")
            costume_size_string.append("XL")
            costume_size_string.append("XXL")
            costume_size_string.append("XXXL")

        if (len(costume_article) == 0):
            costume_article.append("Top")
            costume_article.append("Bottom")
            costume_article.append("Dress")
            costume_article.append("Shoes")
            costume_article.append("Hat")
            costume_article.append("Coat/Jacket")
            costume_article.append("Other")

        # Query separated into an if statement to diminish search time
        if (len(costume_size_number) == 0 or len(costume_size_number) == 26):
            query = Item.query(ndb.AND(Item.clothing_article_type.IN(costume_article),
                Item.clothing_size_string.IN(costume_size_string))).order(Item.name)
        else:
            query = Item.query(ndb.AND(Item.clothing_article_type.IN(costume_article),
                Item.clothing_size_string.IN(costume_size_string),
                Item.clothing_size_num.IN(costume_size_number))).order(Item.name)
    else:
        query = Item.query().order(Item.name)

    tags_list = parseTags(tags_filter)
    if len(tags_list) != 0:
        if tag_grouping == "inclusive":
            query = query.filter(Item.tags.IN(tags_list))
        else:
            for tag in tags_list:
                query = query.filter(Item.tags == tag)

    if len(item_colors) != 0:
        query1 = query;
        if item_color_grouping == "inclusive":
            query1 = query.filter(Item.item_color.IN(item_colors))
        else:
            for color in item_colors:
                query1 = query1.filter(Item.item_color == color)
        return query1

    return query


# TODO: actually remove rolled back and deleted items
def updateList(l):
    to_add = []
    to_remove = []
    for item_key in l.items:
        updated = findUpdatedItem(item_key)
        logging.info('Updated key:%s Item key:%s', updated.key if updated else None, item_key)
        if updated is None:
            to_remove.append(item_key)
        elif updated.key != item_key:
            to_add.append(updated.key)
            to_remove.append(item_key)
    
    # logging.info("Adding %s", [i.urlsafe() for i in to_add])
    # logging.info("Removing %s", [i.urlsafe() for i in to_remove])
    l.items = filter(lambda a: a not in to_remove, l.items)
    l.items.extend(to_add)

    if to_add or to_remove:
        l.put()
