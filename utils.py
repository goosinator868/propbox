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

import requests
import logging


# +---------------------+
# | Third party imports |
# +---------------------+

from google.appengine.ext import ndb


# +---------------------+
# | First party imports |
# +---------------------+

from warehouse_models import Item


# +-----------------+
# | Item Exceptions |
# +-----------------+

class OutdatedEditException(Exception):
    '''Raised when trying to submit an edit to an out of date item.'''
    def __init__(self,*args,**kwargs):
        Exception.__init__(self,*args,**kwargs)

class ItemDeletedException(Exception):
    '''Raised when trying to submit an edit to a deleted item.'''
    def __init__(self,*args,**kwargs):
        Exception.__init__(self,*args,**kwargs)

class AlreadyCommitedException(Exception):
    '''Raised when trying to resolve an orphan that has already been resolved.'''
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
def commitEdit(old_key, new_item, was_orphan=False,suggestion=False):
    '''Stores the new item and ensures that the
       parent-child relationship is enforced between the
       old item and the new item.

       TRANSACTIONAL: This is transactional so all edits to the database
                      cannot be left in an unexpected state.

       SIDE EFFECT: Sets the parent of the new_item to be the old_key.

       Args:
            old_key: The key of the item that this is an edit to.
            new_item: The new version of the item to be commited.
            was_orphan: If the item was already stored in the database as an orphan
                        (likely due to a edit item race)
    '''
    old_item = old_key.get()
    if old_item is None:
        raise ItemPurgedException()
    if old_item.outdated:
        raise OutdatedEditException()
    if old_item.deleted:
        raise ItemDeletedException()
    if was_orphan:
        if not new_item.key.get().orphan:
            raise AlreadyCommitedException()
        # Create a new copy with the correct parent
        copy = cloneItem(new_item, parentKey=old_key)
        new_item.key.delete()
        new_item = copy
    old_item.outdated = not suggestion
    new_key = new_item.put()
    if suggestion:
        old_item.suggested_edits.append(new_key)
    else:
        old_item.child = new_key
    old_item.put()


# +-----------------------+
# | Miscellaneous Helpers |
# +-----------------------+

# Validates an html string using the w3 validator.
def validateHTML(html_string):
    # TODO disable when deployed

    # TODO: Currently, the w3 html validator is broken. Remove when the site is up and running again
    # return html_string

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
def findUpdatedItem(item):
    while item.outdated:
        item = item.child.get()
    return item

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
