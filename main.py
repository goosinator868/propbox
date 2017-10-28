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

# Python built-in imports.
import copy
import os
import urllib
import requests
import json
import logging
import webapp2
import jinja2
from time import sleep

# Third party imports.
from google.appengine.ext import ndb
from google.appengine.ext.db import TransactionFailedError

# First party imports
from warehouse_models import Item, cloneItem, User, possible_permissions
from warehouse_models import List
import auth
from auth import GetCurrentUser

# Encoodes items into JSON, this only includes information being actively used
class ItemEncoder(json.JSONEncoder):
    def default(self, item):
        fields = {}
        fields['name'] = item.name  # used in qr-code check in/out
        fields['urlsafe_key'] = item.key.urlsafe() # used in qr-code check in/out
        return fields

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

# Transaction helpers.
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


## Handlers

#Loads add item page and adds item to database
class AddItem(webapp2.RequestHandler):
    @auth.login_required
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('templates/add_item.html')
        page = template.render({})
        page = page.encode('utf-8')
        self.response.write(ValidateHTML(page))

    @auth.login_required
    def post(self):
        qr_code, _ = Item.allocate_ids(1)
        img = self.request.get('image', default_value='')
        if img == '':
            img = None
        try:
            article_type = self.request.get('article')
            costume_or_prop = self.request.get('item_type')
            costume_size_number = self.request.get('clothing_size_number')
            costume_size_word = self.request.get('clothing_size_string')
            tags_string = self.request.get('tags')
            # Override certain inputs due to costume and prop defaults
            if costume_or_prop == "Costume" and article_type == "N/A":
                # An article type was not selected thus is filtered as an
                # 'Other' item by default
                article_type = "Other"
            elif costume_or_prop == "Prop":
                # Props do not have sizes or article types
                article_type = "N/A"
                costume_size_number = "N/A"
                costume_size_word = "N/A"

            # tags is a string. Needs to parsed into an array
            tags_list = ParseTags(tags_string)

            # Create Item and add to the list
            newItem = Item(
                id=qr_code,
                creator_id=auth.get_user_id(self.request),
                creator_name=auth.get_user_name(self.request),
                name=self.request.get('name'),
                image=img,
                item_type=costume_or_prop,
                condition=self.request.get('condition'),
                clothing_article_type=article_type,
                clothing_size_num=costume_size_number,
                qr_code=qr_code,
                description=self.request.get('description', default_value=''),
                clothing_size_string=costume_size_word,
                tags=tags_list)
            newItem.put()
            sleep(0.1)
            self.redirect("/search_and_browse")
        except:
            # Should never be here unless the token has expired,
            # meaning that we forgot to refresh their token.
            self.redirect("/enforce_auth")

class ResolveEdits(webapp2.RequestHandler):
    @auth.login_required
    def get(self):
        new_item = ndb.Key(urlsafe=self.request.get('new_item_key')).get()
        old_item = new_item.key.parent().get()
        old_item = FindUpdatedItem(old_item)
        template = JINJA_ENVIRONMENT.get_template('templates/resolve_edits.html')
        page = template.render({'old_item': old_item, 'new_item': new_item})
        page = page.encode('utf-8')
        self.response.write(ValidateHTML(page))

    @auth.login_required
    def post(self):
        old_item = ndb.Key(urlsafe=self.request.get('old_item_key')).get()
        new_item = ndb.Key(urlsafe=self.request.get('new_item_key')).get()
        # Update the fields of the pending item.
        new_item.creator_id = auth.get_user_id(self.request)
        new_item.name = self.request.get('name')
        new_item.description = self.request.get('description', default_value='')
        new_item.orphan = False
        new_item.suggested_by = GetCurrentUser(self.request).name
        try:
            CommitEdit(old_item.key, new_item, was_orphan=True)
            self.redirect("/")
        except OutdatedEditException as e:
            new_item.orphan = True
            new_item_key = new_item.put()
            self.redirect("/resolve_edits?" + urllib.urlencode({'new_item_key': new_key.urlsafe()}))
        except AlreadyCommitedException as e:
            # TODO: Make this visible to the user.
            logging.info('someone resolved this edit before you.')
            self.redirect("/review_edits")
        except (ItemPurgedException, ItemDeletedException) as e:
            # TODO: Make this visible to the user.
            logging.info('Item was deleted by someone else before your edits could be saved.')
            self.redirect("/review_edits")
        except TransactionFailedError as e:
             # TODO: Panic should never reach this, it should be caught by the other exceptions.
             logging.critical('transaction failed without reason being determined')

#Handler for editing an item.
class EditItem(webapp2.RequestHandler):
    @auth.login_required
    def get(self):
        item_id = ndb.Key(urlsafe=self.request.get('item_id'))
        item = item_id.get()
        item = FindUpdatedItem(item)
        user = GetCurrentUser(self.request)
        template = JINJA_ENVIRONMENT.get_template('templates/edit_item.html')
        page = template.render({'item': item, 'user':user})
        page = page.encode('utf-8')
        self.response.write(ValidateHTML(page))

    @auth.login_required
    def post(self):
        # permissions logic
        user = GetCurrentUser(self.request)
        standard_user = user.permissions == "Standard user"
        old_item_key = ndb.Key(urlsafe=self.request.get('old_item_key'))
        old_item = old_item_key.get()
        new_item = cloneItem(old_item, old_item_key)
        new_item.creator_id = user.key.string_id()
        new_item.creator_name = user.name
        new_item.approved = (not standard_user)
        new_item.is_suggestion = (standard_user)
        if not standard_user:
            for key in old_item.suggested_edits:
                key.delete()
            old_item.suggested_edits = []
            old_item.put()
        else:
            new_item.suggested_by = user.name
        new_item.name=self.request.get('name')
        # edit item logic
        new_item.name = self.request.get('name')
        new_item.clothing_article_type = self.request.get('article')
        new_item.description = self.request.get('description', default_value='')
        new_item.item_type = self.request.get('item_type')
        new_item.costume_size_num = self.request.get('clothing_size_number')
        new_item.clothing_size_string = self.request.get('clothing_size_string')
        new_item.tags = ParseTags(self.request.get('tags'))
        new_item.condition = self.request.get('condition')

        # Override certain inputs due to costume and prop defaults
        if new_item.item_type == "Costume" and new_item.clothing_article_type == "N/A":
            # An article type was not selected thus is filtered as an
            # 'Other' item by default
            new_item.clothing_article_type = "Other"
        elif new_item.item_type == "Prop":
            # Props do not have sizes or article types
            new_item.clothing_article_type = "N/A"
            new_item.costume_size_num = "N/A"
            new_item.costume_size_string = "N/A"

        # check-out logic below
        if self.request.get('check_out_bool') == "checked":
            new_item.checked_out = True
            new_item.checked_out_reason = self.request.get('check_out_reason')
            new_item.checked_out_by = new_item.creator_id
        else:
            new_item.checked_out = False
            new_item.checked_out_reason = ""
            new_item.checked_out_by = ""

        try:
            CommitEdit(old_item_key, new_item,suggestion=standard_user)
            sleep(0.1)
            self.redirect("/item_details?" + urllib.urlencode({'item_id':(old_item_key if standard_user else new_item.key).urlsafe()}))
        except OutdatedEditException as e:
            new_item.orphan = True
            new_item_key = new_item.put()
            self.redirect('/resolve_edits?' + urllib.urlencode({'new_item_key': new_item_key.urlsafe()}))
        except (ItemPurgedException, ItemDeletedException) as e:
            # TODO: Make this visible to the user.
            logging.info('Item was deleted by someone else before your edits could be saved.')
        except TransactionFailedError as e:
             # TODO: Panic should never reach this, it should be caught by the other exceptions.
             logging.critical('transaction failed without reason being determined')

# Marks an item for deletion. DOES NOT ACTUALLY DELETE.
# TODO: Make transactional.
class DeleteItem(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
        #template = JINJA_ENVIRONMENT.get_template('templates/index.html')
        item_key = ndb.Key(urlsafe=self.request.get('item_id'))
        user = GetCurrentUser(self.request)
        try:
            CommitDelete(item_key, user)
        except OutdatedEditException as e:
            # TODO: Expose this message to the user.
            logging.info('you are trying to delete an old version of this item, please reload the page and try again if you really wish to delete this item.')
        except TransactionFailedError as e:
             # TODO: Expose this message to the user.
            logging.info('could not purge the item, please try again')
        # Redirect back to items view.
        sleep(0.1)
        if user.permissions == "Standard user":
            self.redirect('/item_details?'+urllib.urlencode({'item_id':item_key.urlsafe()}))
        else:
            self.redirect("/search_and_browse")

class ViewImage(webapp2.RequestHandler):
    def get(self):
        item_key = ndb.Key(urlsafe=self.request.get('image_id'))
        item = item_key.get()
        self.response.headers['Content-Type'] = 'image/png'
        self.response.out.write(item.image)

# Deletes an item from the database for good. THIS CANNOT BE UNDONE.
# TODO: Make transactional.
class DeleteItemForever(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
        item_key = ndb.Key(urlsafe=self.request.get('item_id'))
        try:
            CommitPurge(item_key)
        except TransactionFailedError as e:
             # TODO: Expose this message to the user.
            logging.info('could not purge the item, pelase try again')
        sleep(0.1)
        self.redirect('/review_deletions')

# Undeletes an item, returning it to the main list. Reverses the changes made by DeleteItem.
class UndeleteItem(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
        item_key = ndb.Key(urlsafe=self.request.get('item_id'))
        try:
            CommitUnDelete(item_key)
        except TransactionFailedError as e:
             # TODO: Expose this message to the user.
            logging.info('could not un-delete the item, please try again')
        sleep(0.1) #CUT FOR DEPLOYING
        self.redirect('/review_deletions')


class AuthHandler(webapp2.RequestHandler):
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('templates/auth.html')
        page = template.render({})
        page = page.encode('utf-8')
        self.response.write(ValidateHTML(page))

# Filters viewable items based on selected boxes in MainPage
def FilterItems(item_name, item_type, item_condition, costume_article,
    costume_size_string, costume_size_number, tags_filter, tag_grouping):
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

    tags_list = ParseTags(tags_filter)
    if len(tags_list) != 0:
        if tag_grouping == "inclusive":
            query = query.filter(Item.tags.IN(tags_list))
        else:
            for tag in tags_list:
                query = query.filter(Item.tags == tag)

    #query = query.filter(Item.condition.IN(item_condition))
    return query

# Converts text list of tags to array of tags
def ParseTags(tags_string):
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

class ReviewEdits(webapp2.RequestHandler):
    # Loads the edit page.
    @auth.login_required
    def post(self):
        self.get()

    @auth.login_required
    def get(self):
        user = GetCurrentUser(self.request)
        if (user.permissions == "Standard user"):
            self.redirect('/')
            return
        template = JINJA_ENVIRONMENT.get_template('templates/review_edits.html')
        items = Item.query().order(-Item.updated).fetch()
        hasOldVersion = []
        revert_list = []
        suggestions = []
        for item in items:
             if item.is_suggestion:
                suggestions.append(item)
             elif item.key.parent():
                 hasOldVersion.append(item)
        for newest in hasOldVersion:
            if newest.outdated is False and newest.deleted is False and newest.approved is False:
                history = []
                parent = newest.key.parent()
                while parent:
                    history.append(parent.get())
                    parent = parent.parent()
                count = range(len(history))
                revert_list.append([newest, history, count])
        bases = set([])
        for suggestion in suggestions:
            bases.add(suggestion.key.parent())
        suggestion_list = []
        for base in bases:
            suggest = [base.get(),[key.get() for key in base.get().suggested_edits]]
            suggest.append(range(len(suggest[1])))
            suggestion_list.append(suggest)
        # logging.info("\n\n\n\n\n\n\n\n\n\n\n\n\n\n\nList")
        # for r in revert_list:
        #     logging.info("\n\n")
        #     logging.info(r)
        page = template.render({'revert':revert_list, 'suggest':suggestion_list})
        page = page.encode('utf-8')
        self.response.write(ValidateHTML(page))

#Keeps the latest revision. Flags the revision as "approved" in the database.
class KeepRevision(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
        if GetCurrentUser(self.request).permissions == "Standard user":
            self.redirect('/')
            return
        item = ndb.Key(urlsafe=self.request.get('item_id')).get()
        if self.request.get('proposed_edit') == "True":
            logging.info("Accepting the proposed edit.")
            parent = ndb.Key(urlsafe=self.request.get('parent_id')).get()
            parent.child = item.key
            for edit in parent.suggested_edits:
                if edit is not item.key:
                    edit.delete()
            parent.suggested_edits = []
            parent.outdated=True
            item.is_suggestion=False
            parent.put()
        item.approved = True
        item.put()
        sleep(0.1)
        self.redirect('/review_edits')

#Discards a revision.
class DiscardRevision(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
        if GetCurrentUser(self.request).permissions == "Standard user":
            self.redirect('/')
            return
        if self.request.get('revert') == "True":
            selected_item = ndb.Key(urlsafe=self.request.get('item_id'))
            si = selected_item.get()
            si.approved = True
            si.outdated = False
            si.child = None
            si.put()
            discarded_item = ndb.Key(urlsafe=self.request.get('newest_id'))
            while discarded_item != selected_item:
                next_item = discarded_item.parent()
                discarded_item.delete()
                discarded_item = next_item
        else:
            item = ndb.Key(urlsafe=self.request.get('item_id')).get()
            for thing in item.suggested_edits:
                thing.delete()
            item.suggested_edits = []
            item.approved = True
            item.put()
        sleep(0.1)
        self.redirect('/review_edits')

#Allows for undoing an item approval
class RevertItem(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
        if GetCurrentUser(self.request).permissions == "Standard user":
            self.redirect('/')
            return
        item = ndb.Key(urlsafe=self.request.get('item_id')).get()
        item.approved = False
        item.put()
        sleep(0.1)
        self.redirect('/review_edits')

class ViewItemDetails(webapp2.RequestHandler):
    @auth.login_required
    def get(self):
        logging.info("View Item Details")
        user = GetCurrentUser(self.request)
        template = JINJA_ENVIRONMENT.get_template('templates/item_details.html')
        item = ndb.Key(urlsafe=self.request.get('item_id')).get()
        pending_edit = (len(item.suggested_edits) > 0)
        page = template.render({'item':item, 'pending_edit':pending_edit, 'user':user})
        page = page.encode('utf-8')
        self.response.write(ValidateHTML(page))

#To admin-approve items that have been created or edited by lesser users.
class ReviewDeletions(webapp2.RequestHandler):
    @auth.login_required
    def get(self):
        logging.info("Manage Deletions")
        user = GetCurrentUser(self.request)
        if (user.permissions == "Standard user"):
            self.redirect('/')
            return
        template = JINJA_ENVIRONMENT.get_template('templates/review_deletions.html')
        items = Item.query().order(-Item.updated).fetch()
        deleted = []
        for item in items:
            if (item.marked_for_deletion or item.deleted) and item.child == None:
                deleted.append(item)
        page = template.render({'deleted':deleted})
        page = page.encode('utf-8')
        self.response.write(ValidateHTML(page))

#Loads the search and browsing page.
# Renamed from SearchAndBrowse
class MainPage(webapp2.RequestHandler):
    @auth.login_required
    def get(self):
        #template = JINJA_ENVIRONMENT.get_template('templates/search_and_browse_items.html')
        template = JINJA_ENVIRONMENT.get_template('templates/index.html')
        user = GetCurrentUser(self.request);
        try:
            # Filter search items
            item_name_filter = self.request.get('filter_by_name')
            item_type_filter = self.request.get('filter_by_item_type')
            item_condition_filter = self.request.get_all('filter_by_condition')
            item_article_filter = self.request.get_all('filter_by_article')
            costume_size_string_filter = self.request.get_all('filter_by_costume_size_string')
            costume_size_number_filter = self.request.get_all('filter_by_costume_size_number')
            tags_filter = self.request.get('filter_by_tags')
            tags_grouping_filter = self.request.get('filter_by_tag_grouping')

            query = FilterItems(
                item_name_filter,
                item_type_filter,
                item_condition_filter,
                item_article_filter,
                costume_size_string_filter,
                costume_size_number_filter,
                tags_filter, tags_grouping_filter)

            items = query.fetch()
            if (len(item_condition_filter) == 0):
                item_condition_filter.append("Good")
                item_condition_filter.append("Fair")
                item_condition_filter.append("Poor")
                item_condition_filter.append("Being repaired")

            if (item_type_filter == "" or item_type_filter == None):
                item_type_filter = "All"
            # send to display
            page = template.render({'user':user,'items': items, 'item_type_filter': item_type_filter, 'item_name_filter': item_name_filter, 'item_condition_filter': item_condition_filter})
            page = page.encode('utf-8')
            self.response.write(ValidateHTML(page))
        except:
            # first time opening or item has been added
            query = Item.query()
            items = query.fetch()
            page = template.render({'user':user,'items': items, 'item_name_filter': item_name_filter})
            page = page.encode('utf-8')
            self.response.write(ValidateHTML(page))

class ManageUsers(webapp2.RequestHandler):
    @auth.login_required
    def get(self):
        user = GetCurrentUser(self.request)
        if (user.permissions != "Admin"):
            self.redirect('/')
            return
        template = JINJA_ENVIRONMENT.get_template('templates/manage_users.html')
        users = User.query().fetch()
        users.remove(user)
        active_users = [user for user in users if user.permissions != "Deactivated user" and user.permissions != "Pending user"]
        deactivated_users = [user for user in users if user.permissions == "Deactivated user"]
        pending_users = [user for user in users if user.permissions == "Pending user"]
        page = template.render(
            {'users': users,
             'active_users': active_users,
             'deactivated_users': deactivated_users,
             'pending_users': pending_users,
             'permission_levels': list(possible_permissions)})
        page = page.encode('utf-8')
        self.response.write(ValidateHTML(page))

    @auth.login_required
    def post(self):
        user_key = ndb.Key(urlsafe=self.request.get('user_key'))
        user = user_key.get()
        user.permissions = self.request.get('permission_level')
        user.put()
        self.redirect('/manage_users')

class PostAuth(webapp2.RequestHandler):
    @auth.login_required
    def get(self):
        user = GetCurrentUser(self.request)
        firebase_name = auth.get_user_name(self.request)
        # Rare case that someone changed their name.
        if user.name != firebase_name:
            user.name = firebase_name
            # TODO: search all edits by this user and change the names there.
            user.put()
        self.redirect('/')

class PendingApproval(webapp2.RequestHandler):
    @auth.firebase_login_required
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('templates/pending_approval.html')
        page = template.render({})
        page = page.encode('utf-8')
        self.response.write(ValidateHTML(page))

class AccountDeactivated(webapp2.RequestHandler):
    @auth.firebase_login_required
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('templates/account_deactivated.html')
        page = template.render({})
        page = page.encode('utf-8')
        self.response.write(ValidateHTML(page))

# ============================================
# Lists
# ============================================
# TODO: Pages:
#         CheckOutViaQRCode
#         CheckInViaQRCode
#         ViewLists (also add new list)
#         View single list
#           * Check out group
#           * Check in group
#           * Print QR codes
#         PrintQRCodes
#       Edits:
#          Add to list option on items
#          Check out/in option on items
#

class NewList(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
        name = self.request.get('name')
        l = List(name=name)
        k = l.put()
        self.response.write(k.urlsafe())

class ViewLists(webapp2.RequestHandler):
    @auth.login_required
    def get(self):
        user = GetCurrentUser(self.request)
        lists = List.Query(List.user == user.key).fetch()
        template = JINJA_ENVIRONMENT.get_template('templates/view_lists.html')
        page = tempalate.render({'lists': lists})
        page = page.encode('utf-8')
        self.response.write(ValidateHTML(page))

class EditList(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
        listkey = self.request.get('list')
        l = ndb.Key(urlsafe=listkey).get()

        new_contents = self.request.get('new_contents')
        del l.items[:]

        for urlsafe_key in new_contents:
            l.items.append(ndb.Key(urlsafe=urlsafe_key))
        l.put()


class PrintQRCodes(webapp2.RequestHandler):
    @auth.login_required
    def get(self):
        keys = self.request.get_all('keys')
        items = []
        for k in keys:
            items.append(ndb.Key(urlsafe=k).get())
        template = JINJA_ENVIRONMENT.get_template('templates/print_qr_codes.html')
        page = template.render({'items': items})
        page = page.encode('utf-8')
        self.response.write(ValidateHTML(page))

class ItemFromQRCode(webapp2.RequestHandler):
    @auth.login_required
    def get(self):
        qr_code = int(self.request.get('qr_code'))
        item = Item.query(ndb.AND(Item.qr_code == qr_code, Item.outdated == False)).filter().fetch()[0]
        logging.info(item)
        self.response.write(ItemEncoder().encode(item))

class CheckIn(webapp2.RequestHandler):
    @auth.login_required
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('templates/check_in.html')
        page = template.render({})
        page = page.encode('utf-8')
        self.response.write(ValidateHTML(page))

    @auth.login_required
    def post(self):
        to_check_in = self.request.get('to_check_in')
        for urlsafe_key in to_check_in:
            item = item = ndb.Key(urlsafe=urlsafe_key)
            item.checked_out = False
            item.put()

class CheckOut(webapp2.RequestHandler):
    @auth.login_required
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('templates/check_out.html')
        page = template.render({})
        page = page.encode('utf-8')
        self.response.write(ValidateHTML(page))

    @auth.login_required
    def post(self):
        to_check_in = self.request.get('to_check_out')
        for urlsafe_key in to_check_in:
            item = ndb.Key(urlsafe=urlsafe_key)
            item.checked_out = True
            item.put()


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

app = webapp2.WSGIApplication([
    ('/account_deactivated', AccountDeactivated),
    ('/delete_item', DeleteItem),
    ('/delete_item_forever', DeleteItemForever),
    ('/undelete_item', UndeleteItem),
    ('/add_item', AddItem),
    ('/view_image', ViewImage),
    ('/edit_item', EditItem),
    ('/enforce_auth', AuthHandler),
    ('/review_edits', ReviewEdits),
    ('/resolve_edits', ResolveEdits),
    ('/discard_revision',DiscardRevision),
    ('/keep_revision',KeepRevision),
    ('/revert_item', RevertItem),
    ('/manage_users', ManageUsers),
    ('/post_auth', PostAuth),
    ('/pending_approval', PendingApproval),
    ('/check_in', CheckIn),
    ('/check_out', CheckOut),
    ('/item_details', ViewItemDetails),
    ('/review_deletions', ReviewDeletions),
    ('/print_qr_codes', PrintQRCodes),
    ('/item_from_qr_code', ItemFromQRCode),
    ('/.*', MainPage),
], debug=True)
