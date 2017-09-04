# Python built-in imports.
import os
import urllib
import logging
import webapp2
import jinja2
from time import sleep

# Third party imports.
from google.appengine.ext import ndb
from google.appengine.ext.db import TransactionFailedError

# First party imports
from warehouse_models import Item, cloneItem
import auth
#from enums import *

# # Little helper function for rendering the main page.
# def FetchList():
#     return {'items':Item.query(Item.outdated == False, Item.deleted == False, Item.orphan == False).order(-Item.updated).fetch()}

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
def CommitDelete(item_key):
    item = item_key.get()
    if item.outdated:
        raise OutdatedEditException()
    item.deleted = True
    item.put()

@ndb.transactional(xg=True, retries=1)
def CommitUnDelete(item_key):
    item = item_key.get()
    item.deleted = False
    item.put()

@ndb.transactional(xg=True, retries=1)
def CommitPurge(item_key):
    toDelete = [item_key]
    while item_key.parent():
        item_key = item_key.parent()
        toDelete.append(item_key)
    # logging.info("\n\n\n")
    # logging.info(toDelete)
    for k in toDelete:
        k.delete()

@ndb.transactional(xg=True, retries=1)
def CommitEdit(old_key, new_item, was_orphan=False):
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
    old_item.outdated = True
    new_item.parent = old_key
    new_key = new_item.put()
    old_item.child = new_key
    old_item.put()


## Handlers
class MainPage(webapp2.RequestHandler):
    @auth.login_required
    def get(self):
        # Load html template
        template = JINJA_ENVIRONMENT.get_template('templates/index.html')
        try:
            # Filter search items
            item_name_filter = self.request.get('filter_by_name')
            item_type_filter = self.request.get('filter_by_item_type')
            item_condition_filter = self.request.get('filter_by_condition', allow_multiple=True)
            item_article_filter = self.request.get('filter_by_article', allow_multiple=True)
            costume_size_string_filter = self.request.get('filter_by_costume_size_string', allow_multiple=True)
            costume_size_number_filter = self.request.get('filter_by_costume_size_number', allow_multiple=True)
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
            # send to display
            self.response.write(template.render({'items': items, 'item_name_filter': item_name_filter}))
        except:
            # first time opening or item has been added
            query = Item.query()
            items = query.fetch()
            self.response.write(template.render({'items': items, 'item_name_filter': item_name_filter}))

class AddItem(webapp2.RequestHandler):
    #TODO: Find out why this ends up loading the review edits page.
    @auth.login_required
    def post(self):
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
                creator_id=auth.get_user_id(self.request),
                name=self.request.get('name'),
                image=img,
                item_type=costume_or_prop,
                condition=self.request.get('condition'),
                clothing_article_type=article_type,
                clothing_size_num=costume_size_number,
                qr_code=1234,
                description=self.request.get('description', default_value=''),
                clothing_size_string=costume_size_word,
                tags=tags_list)
            newItem.put()
            sleep(0.1)
            self.redirect("/")
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
        self.response.write(template.render({'old_item': old_item, 'new_item': new_item}))

    @auth.login_required
    def post(self):
        old_item = ndb.Key(urlsafe=self.request.get('old_item_key')).get()
        new_item = ndb.Key(urlsafe=self.request.get('new_item_key')).get()
        # Update the fields of the pending item.
        new_item.creator_id = auth.get_user_id(self.request)
        new_item.name = self.request.get('name')
        new_item.description = self.request.get('description', default_value='')
        new_item.orphan = False
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


class EditItem(webapp2.RequestHandler):
    @auth.login_required
    def get(self):
        item_id = ndb.Key(urlsafe=self.request.get('item_id'))
        item = item_id.get()
        item = FindUpdatedItem(item)
        template = JINJA_ENVIRONMENT.get_template('templates/edit_item.html')
        self.response.write(template.render({'item': item}))

    @auth.login_required
    def post(self):
        old_item_key = ndb.Key(urlsafe=self.request.get('old_item_key'))
        new_item = cloneItem(old_item_key.get(), old_item_key)
        new_item.creator_id = auth.get_user_id(self.request)
        new_item.name=self.request.get('name')
        new_item.description=self.request.get('description', default_value='')

        try:
            CommitEdit(old_item_key, new_item)
            sleep(0.1)
            self.redirect("/")
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
        id_string = self.request.get('item_id')
        try:
            CommitDelete(ndb.Key(urlsafe=id_string))
        except OutdatedEditException as e:
            # TODO: Expose this message to the user.
            logging.info('you are trying to delete an old version of this item, please reload the page and try again if you really wish to delete this item.')
        except TransactionFailedError as e:
             # TODO: Expose this message to the user.
            logging.info('could not purge the item, pelase try again')
        # Redirect back to items view.
        sleep(0.1)
        self.redirect("/")

class ViewImage(webapp2.RequestHandler):
    def get(self):
        item_key = ndb.Key(urlsafe=self.request.get('entity_id'))
        item = item_key.get()
        self.response.headers['Content-Type'] = 'image/png'
        self.response.out.write(item.image)

# Deletes an item from the database for good. THIS CANNOT BE UNDONE.
# TODO: Make transactional.
class DeleteItemForever(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
        #template = JINJA_ENVIRONMENT.get_template('templates/review_edits.html')
        item_key = ndb.Key(urlsafe=self.request.get('item_id'))
        # TODO: ensure this has no children.
        # TODO: delete all parents.
        try:
            CommitPurge(item_key)
        except TransactionFailedError as e:
             # TODO: Expose this message to the user.
            logging.info('could not purge the item, pelase try again')
        sleep(0.1)
        self.redirect('/review_edits')

# Undeletes an item, returning it to the main list. Reverses the changes made by DeleteItem.
# TODO: Make transactional.
class UndeleteItem(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
        #template = JINJA_ENVIRONMENT.get_template('templates/review_edits.html')
        item_key = ndb.Key(urlsafe=self.request.get('item_id'))
        try:
            CommitUnDelete(item_key)
        except TransactionFailedError as e:
             # TODO: Expose this message to the user.
            logging.info('could not un-delete the item, pelase try again')
        sleep(0.1) #CUT FOR DEPLOYING
        self.redirect('/')


class AuthHandler(webapp2.RequestHandler):
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('templates/auth.html')
        self.response.write(template.render({}))

# Filters viewable items based on selected boxes in MainPage
def FilterItems(item_name, item_type, item_condition, costume_article,
    costume_size_string, costume_size_number, tags_filter, tag_grouping):
    # Check if costume or prop is selected individually
    if (item_type != "All" and item_type != ""):
        if (item_type == "Costume"):
            if (len(costume_size_string) == 5):
                costume_size_string.append("N/A")

            # Query separated into an if statement to diminish search time
            if (len(costume_size_number) == 21):
                query = Item.query(ndb.AND(Item.item_type == item_type,
                    Item.clothing_article_type.IN(costume_article),
                    Item.clothing_size_string.IN(costume_size_string))).order(Item.name)
            else:
                query = Item.query(ndb.AND(Item.item_type == item_type,
                    Item.clothing_article_type.IN(costume_article),
                    Item.clothing_size_string.IN(costume_size_string),
                    Item.clothing_size_num.IN(costume_size_number))).order(Item.name)
        else:
            query = Item.query(Item.item_type == item_type).order(Item.name)
    else:
        query = Item.query().order(Item.name)

    query = query.filter(Item.condition.IN(item_condition))

    tags_list = ParseTags(tags_filter)
    if len(tags_list) != 0:
        if tag_grouping == "inclusive":
            query = query.filter(Item.tags.IN(tags_list))
        else:
            for tag in tags_list:
                query = query.filter(Item.tags == tag)
    return query

# Converts text list of tags to array of tags
def ParseTags(tags_string):
    tags_list = []

    # Find newline character
    tag_end_index = tags_string.find("\n")

    # Check newline character exists in string
    while tag_end_index != -1:
        # Add tag to list
        tags_list.append(tags_string[:tag_end_index - 1])
        # Shrink or delete string based on how much material is left in string
        if tag_end_index + 1 < len(tags_string):
            tags_string = tags_string[tag_end_index + 1:len(tags_string)]
        else:
            tags_string = ""

        tag_end_index = tags_string.find("\n")

    # Potentially still has a tag not covered. Adds last tag to list if possible
    if len(tags_string) != 0:
        tags_list.append(tags_string)

    return tags_list

class ReviewEdits(webapp2.RequestHandler):
# Loads the edit page.
# TODO: FIGURE OUT WHY THIS PAGE LOADS WHEN ADDING A SECOND ITEM.
    def post(self):
        self.get()
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('templates/review_edits.html')
        items = Item.query().order(-Item.updated).fetch()
        deleted = []
        hasOldVersion = []
        newAndOld = []
        for item in items:
            if item.deleted and item.child == None:
                deleted.append(item)
            elif item.key.parent():
                hasOldVersion.append(item)
        for newest in hasOldVersion:
            logging.info(newest)
            if newest.outdated is False and newest.deleted is False and newest.approved is False:
                history = []
                parent = newest.key.parent()
                while parent:
                    history.append(parent.get())
                    parent = parent.parent()
                count = range(len(history))
                logging.info(history)
                newAndOld.append([newest, history, count])
        self.response.write(template.render({'deleted':deleted,'revised':newAndOld}))

#Keeps the latest revision. Flags the revision as "approved" in the database.
class KeepRevision(webapp2.RequestHandler):
    def post(self):
        item = ndb.Key(urlsafe=self.request.get('item_id')).get()
        item.approved = True
        item.put()
        sleep(0.1)
        self.redirect('/review_edits')

#Discards a revision.
class DiscardRevision(webapp2.RequestHandler):
    def post(self):
        selected_item = ndb.Key(urlsafe=self.request.get('item_id'))
        si = selected_item.get()
        si.approved = True
        si.outdated = False
        si.put()
        discarded_item = ndb.Key(urlsafe=self.request.get('newest_id'))
        while discarded_item != selected_item: 
            logging.info(discarded_item.get().description)
            next_item = discarded_item.parent()
            discarded_item.delete()
            discarded_item = next_item
            logging.info(discarded_item.get().description)
        sleep(0.1)
        self.redirect('/review_edits')

#Allows for undoing an item approval
class RevertItem(webapp2.RequestHandler):
    def post(self):
        item = ndb.Key(urlsafe=self.request.get('item_id')).get()
        item.approved = False
        item.put()
        sleep(0.1)
        self.redirect('/review_edits')


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

app = webapp2.WSGIApplication([
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
    ('/.*', MainPage),
], debug=True)
