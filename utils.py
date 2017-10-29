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
import urllib
import requests
import json
import logging
import webapp2
import jinja2
from time import sleep


# +---------------------+
# | Third party imports |
# +---------------------+

from google.appengine.ext import ndb
from google.appengine.ext.db import TransactionFailedError


# +---------------------+
# | First party imports |
# +---------------------+

from warehouse_models import Item, cloneItem, User, possible_permissions
import auth
from auth import GetCurrentUser


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
def CommitDelete(item_key,user):
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
def CommitUnDelete(item_key):
    item = item_key.get()
    item.deleted = False
    item.marked_for_deletion = False
    item.suggested_by = ""
    item.put()

@ndb.transactional(xg=True, retries=1)
def CommitPurge(item_key):
    toDelete = [item_key] + [suggestion for suggestion in item_key.get().suggested_edits]
    while item_key.parent():
        item_key = item_key.parent()
        toDelete.append(item_key)
    # logging.info("\n\n\n")
    # logging.info(toDelete)
    for k in toDelete:
        k.delete()

@ndb.transactional(xg=True, retries=1)
def CommitEdit(old_key, new_item, was_orphan=False,suggestion=False):
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
def ValidateHTML(html_string):
    # TODO disable when deployed
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
def FindUpdatedItem(item):
    while item.outdated:
        item = item.child.get()
    return item
