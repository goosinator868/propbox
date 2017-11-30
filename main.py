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
# from time import sleep

# +---------------------+
# | Third party imports |
# +---------------------+

from google.appengine.api import app_identity
from google.appengine.api import images
from google.appengine.ext import blobstore
from google.appengine.ext import ndb
from google.appengine.ext.db import TransactionFailedError
import cloudstorage as gcs


# +---------------------+
# | First party imports |
# +---------------------+

from warehouse_models import Item, cloneItem, User, possible_permissions
from warehouse_models import List
import warehouse_models as wmodels
import auth
from auth import get_current_user
from utils import *

# +--------------------------+
# | TODO: Move this to utils |
# +--------------------------+
# Encoodes items into JSON, this only includes information being actively used
class ItemEncoder(json.JSONEncoder):
    def default(self, item):
        fields = {}
        fields['name'] = item.name  # used in qr-code check in/out
        fields['urlsafe_key'] = item.key.urlsafe() # used in qr-code check in/out
        return fields


# +------------------------+
# | Event Handlers Classes |
# +------------------------+

#Loads add item page and adds item to database
class AddItem(webapp2.RequestHandler):
    @auth.login_required
    def get(self):
        user = get_current_user(self.request)
        # logging.info(user.permissions != wmodels.ADMIN)
        if (user.permissions == wmodels.PENDING_USER or user.permissions == wmodels.DEACTIVATED_USER):
            self.redirect('/')
            return
        template = JINJA_ENVIRONMENT.get_template('templates/add_item.html')
        try:
            page = ""
            item_id = ndb.Key(urlsafe=self.request.get('item_id'))
            if item_id != None:
                item = item_id.get()
                item = findUpdatedItem(item_id)
                page = template.render({'item': item})
            else:
                item = None;
                page = template.render({'item': item})
            page = page.encode('utf-8')
            self.response.write(validateHTML(page))
        except:
            item = None;
            page = template.render({'item': item})
            page = page.encode('utf-8')
            self.response.write(validateHTML(page))

    @auth.login_required
    def post(self):
        user = get_current_user(self.request)
        if (user.permissions == wmodels.PENDING_USER or user.permissions == wmodels.DEACTIVATED_USER):
            self.redirect('/')
            return
        try:
            image_data = self.request.get('image', default_value='')
            image_url = ''
            if image_data == '' and self.request.get('duplicate') == "True":
                image_url = ndb.Key(urlsafe=self.request.get('original_item')).get().image_url
            elif image_data != '':
                image_url = saveImageInGCS(image_data)

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
            tags_list = parseTags(tags_string)

            # Create Item and add to the list
            duplication = self.request.get('times_to_duplicate')
            d = int(duplication)
            while d > 0:
                qr_code, _ = Item.allocate_ids(1)
                Item(
                    id=qr_code,
                    creator_id=auth.get_user_id(self.request),
                    creator_name=auth.get_user_name(self.request),
                    name=self.request.get('name'),
                    image_url=image_url,
                    item_type=costume_or_prop,
                    condition=self.request.get('condition'),
                    item_color=self.request.get_all('color'),
                    clothing_article_type=article_type,
                    clothing_size_num=costume_size_number,
                    qr_code=qr_code,
                    description=self.request.get('description', default_value=''),
                    clothing_size_string=costume_size_word,
                    tags=tags_list).put()
                d = d - 1;
                #sleep(0.1)

            next_page = self.request.get("next_page")
            if next_page == "Make Another Item":
                self.redirect("/add_item")
            else:
                self.redirect("/search_and_browse")
        except:
            # Should never be here unless the token has expired,
            # meaning that we forgot to refresh their token.
            self.redirect("/enforce_auth")

#Handler for editing an item.
class EditItem(webapp2.RequestHandler):
    @auth.login_required
    def get(self):
        user = get_current_user(self.request)
        if (user.permissions == wmodels.DEACTIVATED_USER or user.permissions == wmodels.PENDING_USER):
            self.redirect('/')
            return
        item_id = ndb.Key(urlsafe=self.request.get('item_id'))
        item = item_id.get()
        item = findUpdatedItem(item_id)
        user = get_current_user(self.request)
        template = JINJA_ENVIRONMENT.get_template('templates/edit_item.html')
        page = template.render({'item': item, 'user':user})
        page = page.encode('utf-8')
        self.response.write(validateHTML(page))

    @auth.login_required
    def post(self):
        user = get_current_user(self.request)
        if (user.permissions == wmodels.DEACTIVATED_USER or user.permissions == wmodels.PENDING_USER):
            self.redirect('/')
            return
        user = get_current_user(self.request)
        standard_user = user.permissions == "Standard user"
        old_item_key = ndb.Key(urlsafe=self.request.get('old_item_key'))
        old_item = old_item_key.get()
        new_item = cloneItem(old_item, old_item_key)
        image_data = self.request.get('image', default_value='')
        image_url = ''
        if image_data != '':
            new_item.image_url = saveImageInGCS(image_data)

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
        new_item.item_color = self.request.get_all('color')
        new_item.tags = parseTags(self.request.get('tags'))
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
            new_item_key = commitEdit(old_item_key, new_item,suggestion=standard_user)
            #sleep(0.1)
            self.redirect("/item_details?" + urllib.urlencode({'item_id':(old_item_key if standard_user else new_item_key).urlsafe()}))
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
        user = get_current_user(self.request)
        try:
            commitDelete(item_key, user)
            removeFromAllLists(item_key)
        except TransactionFailedError as e:
             # TODO: Expose this message to the user.
            logging.info('could not delete the item, please try again')
        # Redirect back to items view.
        #sleep(0.1)
        if user.permissions == "Standard user":
            self.redirect('/item_details?'+urllib.urlencode({'item_id':item_key.urlsafe()}))
        else:
            self.redirect("/search_and_browse")


# Deletes an item from the database for good. THIS CANNOT BE UNDONE.
# TODO: Make transactional.
class DeleteItemForever(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
        item_key = ndb.Key(urlsafe=self.request.get('item_id'))
        try:
            commitPurge(item_key)
        except TransactionFailedError as e:
             # TODO: Expose this message to the user.
            logging.info('could not purge the item, pelase try again')
        #sleep(0.1)
        self.redirect('/review_deletions')


# Undeletes an item, returning it to the main list. Reverses the changes made by DeleteItem.
class UndeleteItem(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
        item_key = ndb.Key(urlsafe=self.request.get('item_id'))
        try:
            commitUnDelete(item_key)
        except TransactionFailedError as e:
             # TODO: Expose this message to the user.
            logging.info('could not un-delete the item, please try again')
        #sleep(0.1) #CUT FOR DEPLOYING
        self.redirect('/review_deletions')


class AuthHandler(webapp2.RequestHandler):
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('templates/auth.html')
        page = template.render({})
        page = page.encode('utf-8')
        self.response.write(validateHTML(page))


class ReviewEdits(webapp2.RequestHandler):
    # Loads the edit page.
    @auth.login_required
    def post(self):
        self.get()

    @auth.login_required
    def get(self):
        user = get_current_user(self.request)
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
        self.response.write(validateHTML(page))


#Keeps the latest revision. Flags the revision as "approved" in the database.
class KeepRevision(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
        if get_current_user(self.request).permissions == "Standard user":
            self.redirect('/')
            return
        item = ndb.Key(urlsafe=self.request.get('item_id')).get()
        if self.request.get('proposed_edit') == "True":
            # logging.info("Accepting the proposed edit.")
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
        #sleep(0.1)
        self.redirect('/review_edits')


#Discards a revision.
class DiscardRevision(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
        if get_current_user(self.request).permissions == "Standard user":
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
        #sleep(0.1)
        self.redirect('/review_edits')


#Allows for undoing an item approval
class RevertItem(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
        if get_current_user(self.request).permissions == "Standard user":
            self.redirect('/')
            return
        item = ndb.Key(urlsafe=self.request.get('item_id')).get()
        item.approved = False
        item.put()
        #sleep(0.1)
        self.redirect('/review_edits')

class ViewItemDetails(webapp2.RequestHandler):
    @auth.login_required
    def get(self):
        # logging.info("View Item Details")
        user = get_current_user(self.request)
        template = JINJA_ENVIRONMENT.get_template('templates/item_details.html')
        item = ndb.Key(urlsafe=self.request.get('item_id')).get()
        pending_edit = (len(item.suggested_edits) > 0)
        lists = List.query(ndb.OR(List.owner == user.key, List.public == True)).fetch()
        page = template.render({'item':item,
                                'pending_edit':pending_edit,
                                'user':user,
                                'lists':lists})
        page = page.encode('utf-8')
        self.response.write(validateHTML(page))


#To admin-approve items that have been created or edited by lesser users.
class ReviewDeletions(webapp2.RequestHandler):
    @auth.login_required
    def get(self):
        # logging.info("Manage Deletions")
        user = get_current_user(self.request)
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
        self.response.write(validateHTML(page))


#Loads the search and browsing page.
# Renamed from SearchAndBrowse
class MainPage(webapp2.RequestHandler):
    @auth.login_required
    def get(self):
        user = get_current_user(self.request)
        #template = JINJA_ENVIRONMENT.get_template('templates/search_and_browse_items.html')
        template = JINJA_ENVIRONMENT.get_template('templates/index.html')
        user = get_current_user(self.request);
        lists = List.query(ndb.OR(List.owner == user.key, List.public == True)).fetch()
        try:
            # Filter search items
            item_name_filter = self.request.get('filter_by_name')
            item_type_filter = self.request.get('filter_by_item_type')
            item_condition_filter = self.request.get_all('filter_by_condition')
            item_color_filter = self.request.get_all('filter_by_color')
            item_color_grouping_filter = self.request.get('filter_by_color_grouping')
            item_article_filter = self.request.get_all('filter_by_article')
            costume_size_string_filter = self.request.get_all('filter_by_costume_size_string')
            costume_size_number_filter = self.request.get_all('filter_by_costume_size_number')
            tags_filter = self.request.get('filter_by_tags')
            tags_grouping_filter = self.request.get('filter_by_tag_grouping')
            availability_filter = self.request.get('filter_by_availability')
            user_id = auth.get_user_id(self.request)


            query = filterItems(
                item_name_filter,
                item_type_filter,
                item_condition_filter,
                item_color_filter,
                item_color_grouping_filter,
                item_article_filter,
                costume_size_string_filter,
                costume_size_number_filter,
                tags_filter,
                tags_grouping_filter)

            items = query.fetch()
            if (len(item_condition_filter) == 0):
                item_condition_filter.append("Good")
                item_condition_filter.append("Fair")
                item_condition_filter.append("Poor")
                item_condition_filter.append("Being repaired")

            if (item_type_filter == "" or item_type_filter == None):
                item_type_filter = "All"

            if (len(item_color_filter) == 0):
                item_color_filter.append("Red")
                item_color_filter.append("Orange")
                item_color_filter.append("Yellow")
                item_color_filter.append("Green")
                item_color_filter.append("Cyan")
                item_color_filter.append("Blue")
                item_color_filter.append("Indigo")
                item_color_filter.append("Purple")
                item_color_filter.append("Pink")
                item_color_filter.append("Brown")
                item_color_filter.append("Black")
                item_color_filter.append("White")
                item_color_filter.append("Gray")

            # send to display
            page = template.render({
                'lists': lists,
                'user': user,
                'items': items,
                'item_type_filter': item_type_filter,
                'item_name_filter': item_name_filter,
                'item_condition_filter': item_condition_filter,
                'item_color_filter': item_color_filter,
                'availability_filter': availability_filter,
                'user_id': user_id})
            page = page.encode('utf-8')
            self.response.write(validateHTML(page))

        # TODO: make this more specific OR preferably remove try/except infrastructure
        except:
            # first time opening or item has been added
            query = Item.query()
            items = query.fetch()
            # logging.info(items)
            page = template.render({
                'lists': lists,
                'user': user,
                'items': items,
                'item_type_filter': item_type_filter})
            page = page.encode('utf-8')
            self.response.write(validateHTML(page))


class ManageUsers(webapp2.RequestHandler):
    @auth.login_required
    def get(self):
        user = get_current_user(self.request)
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
        self.response.write(validateHTML(page))

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
        user = get_current_user(self.request)
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
        self.response.write(validateHTML(page))


class AccountDeactivated(webapp2.RequestHandler):
    @auth.firebase_login_required
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('templates/account_deactivated.html')
        page = template.render({})
        page = page.encode('utf-8')
        self.response.write(validateHTML(page))

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
        user = get_current_user(self.request)
        name = self.request.get('name')
        public = self.request.get('public') == 'public'
        l = List(name=name, owner=user.key, public=public)
        k = l.put()
        self.redirect('/view_lists')

class DeleteList(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
        user = get_current_user(self.request)
        l = ndb.Key(urlsafe=self.request.get('list')).get()
        if l.public and user.permissions in [wmodels.TRUSTED_USER, wmodels.ADMIN]:
            l.key.delete()
        elif l.owner == user.key:
            l.key.delete()

        self.redirect('/view_lists')

class ViewLists(webapp2.RequestHandler):
    @auth.login_required
    def get(self):
        user = get_current_user(self.request)
        lists = List.query(ndb.OR(
            List.owner == user.key,
            List.public == True,
            )).fetch()
        template = JINJA_ENVIRONMENT.get_template('templates/view_lists.html')
        page = template.render({'lists': lists, 'user': user})
        page = page.encode('utf-8')
        self.response.write(validateHTML(page))

class ViewList(webapp2.RequestHandler):
    @auth.login_required
    def get(self):
        user = get_current_user(self.request)
        l = ndb.Key(urlsafe=self.request.get('list')).get()
        updateList(l)
        if not l.public and user.key != l.owner:
            self.redirect('/view_lists')
            return
        items = [k.get() for k in l.items]
        template = JINJA_ENVIRONMENT.get_template('templates/view_list.html')
        page = template.render({'list': l, 'items': items, 'user': user})
        page = page.encode('utf-8')
        self.response.write(validateHTML(page))

class ChangeListPermissions(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
        user = get_current_user(self.request)
        l = ndb.Key(urlsafe=self.request.get('list')).get()
        if l.owner == user.key:
            l.public = self.request.get('public') == 'public'
            l.put()
        self.redirect('/view_list?list=' + l.key.urlsafe())

class AddToList(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
        user = get_current_user(self.request)
        l = ndb.Key(urlsafe=self.request.get('list')).get()
        updateList(l)
        codes = [i.get().qr_code for i in l.items]
        item = ndb.Key(urlsafe=self.request.get('item')).get()
        if (l.public and user.permissions in [wmodels.TRUSTED_USER, wmodels.ADMIN]) or user.key == l.owner:
            if item.qr_code not in codes:
                addToList(l.key, item.key)

class RemoveFromList(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
        user = get_current_user(self.request)
        l = ndb.Key(urlsafe=self.request.get('list')).get()
        updateList(l)
        codes = [i.get().qr_code for i in l.items]
        item = ndb.Key(urlsafe=self.request.get('item')).get()
        if (l.public and user.permissions in [wmodels.TRUSTED_USER, wmodels.ADMIN]) or user.key == l.owner:
            if item.qr_code in codes:
                removeFromList(l.key, i)


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
        self.response.write(validateHTML(page))

class ItemFromQRCode(webapp2.RequestHandler):
    @auth.login_required
    def get(self):
        qr_code = int(self.request.get('qr_code'))
        item = Item.query(ndb.AND(Item.qr_code == qr_code, Item.outdated == False)).filter().fetch()[0]
        self.response.write(ItemEncoder().encode(item))

class CheckIn(webapp2.RequestHandler):
    @auth.login_required
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('templates/check_in.html')
        page = template.render({})
        page = page.encode('utf-8')
        self.response.write(validateHTML(page))

    @auth.login_required
    def post(self):
        to_check_in = self.request.get_all('keys')
        while to_check_in:
            urlsafe_key = to_check_in.pop()
            item = ndb.Key(urlsafe=urlsafe_key).get()
            if item.key.parent() != None:
                to_check_in.append(item.key.parent().urlsafe())
            item.checked_out = False
            item.checked_out_reason = ""
            item.checked_out_by = ""
            item.checked_out_by_name = ""
            item.put()
            self.redirect("/")

class CheckOut(webapp2.RequestHandler):
    @auth.login_required
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('templates/check_out.html')
        page = template.render({})
        page = page.encode('utf-8')
        self.response.write(validateHTML(page))

    @auth.login_required
    def post(self):
        user = auth.get_user_id(self.request)
        to_check_out = self.request.get_all('keys')
        reason = self.request.get('reason')
        while to_check_out:
            urlsafe_key = to_check_out.pop()
            item = ndb.Key(urlsafe=urlsafe_key).get()
            if item.key.parent() != None:
                to_check_out.append(item.key.parent().urlsafe())
            item.checked_out = True
            item.checked_out_by = user
            item.checked_out_by_name = get_current_user(self.request).name
            item.checked_out_reason = reason
            item.put()
        self.redirect("/")

# Example deleting files, not yet implemented for images but I am keeping this
# here for a reference when I decide to implement deleting images.
  # def delete_files(self):
  #   self.response.write('Deleting files...\n')
  #   for filename in self.tmp_filenames_to_clean_up:
  #     self.response.write('Deleting file %s\n' % filename)
  #     try:
  #       gcs.delete(filename)
  #     except gcs.NotFoundError:
  #       pass

# +-------------------+
# | Environment Setup |
# +-------------------+

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
    ('/edit_item', EditItem),
    ('/enforce_auth', AuthHandler),
    ('/review_edits', ReviewEdits),
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
    # Lists
    ('/new_list', NewList),
    ('/change_list_permissions', ChangeListPermissions),
    ('/delete_list', DeleteList),
    ('/view_lists', ViewLists),
    ('/view_list', ViewList),
    ('/add_to_list', AddToList),
    ('/remove_from_list', RemoveFromList),
    ('/.*', MainPage),
], debug=True)
