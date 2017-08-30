# Python built-in imports.
import os
import urllib
import logging
import webapp2
import jinja2
from time import sleep

# Third party imports.
from google.appengine.ext import ndb

# First party imports
from warehouse_models import Item, cloneItem
import auth

# Little helper function for rendering the main page.
def FetchList():
    return {'items':Item.query(Item.outdated == False, Item.deleted == False, Item.orphan == False).order(-Item.updated).fetch()}

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
    to_purge = set([item_key])
    # Get all children
    # Get all parents
    for item in to_purge:
        item.key.delete()

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
        template = JINJA_ENVIRONMENT.get_template('templates/index.html')
        self.response.write(template.render(FetchList()))

class AddItem(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
        try:
            new_item = Item(
                creator_id=auth.get_user_id(self.request),
                name=self.request.get('name'),
                description=self.request.get('description', default_value=''),
                qr_code=1234)
            new_item.put()
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
        new_item = Item(
            creator_id=auth.get_user_id(self.request),
            name=self.request.get('name'),
            description=self.request.get('description', default_value=''),
            qr_code=1234,
            parent=old_item_key)
        try:
            CommitEdit(old_item_key, new_item)
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
        except OutdatedEditException as e:
            CommitDelete(ndb.Key(urlsafe=id_string))
            # TODO: Expose this message to the user.
            logging.info('you are trying to delete an old version of this item, please reload the page and try again if you really wish to delete this item.')
        except TransactionFailedError as e:
             # TODO: Expose this message to the user.
            logging.info('could not purge the item, pelase try again')
        # Redirect back to items view.
        sleep(0.05)
        self.redirect("/")

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
        except TransactionFailedError as e:
            CommitPurge(item_key)
             # TODO: Expose this message to the user.
            logging.info('could not purge the item, pelase try again')
        sleep(0.1)
        self.redirect('/load_edit_page')

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
        sleep(0.1)
        self.redirect('/')

#Currently marks an item as "edited" and updates the database.
#TODO: Change method to actually send user to an edit page.
#THIS IS A TEMPORARY METHOD!
class EditItem(webapp2.RequestHandler):
    #@auth.login_required
    def post(self):
        item = ndb.Key(urlsafe=self.request.get('item_id')).get()
        newItem = cloneItem(item)
        newItem.description += "(A CLONE)"
        newItem = newItem.put().get()
        item.outdated = True
        item.newer_version = newItem.key
        newItem.older_version = item.key
        logging.info(item.to_dict())
        item.put()
        newItem.put()
        sleep(0.1)
        self.redirect('/')


class AuthHandler(webapp2.RequestHandler):
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('templates/auth.html')
        self.response.write(template.render({}))

class ReviewEdits(webapp2.RequestHandler):
# Loads the edit page.
    def post(self):
        self.get()
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('templates/review_edits.html')
        items = Item.query().order(-Item.updated).fetch()
        deleted = []
        hasOldVersion = []
        newAndOld = []
        for item in items:
            if item.deleted and item.newer_version == None: 
                deleted.append(item)
            elif item.older_version:
                hasOldVersion.append(item)
        for newest in hasOldVersion:
            #Hides all but latest version. 
            #TODO: Debate revision.
            if newest.outdated is False and newest.deleted is False: 
                newAndOld.append([newest,newest.older_version.get()])
        self.response.write(template.render({'deleted':deleted,'revised':newAndOld}))

#Keeps a revision.
#TODO: Actually implement.
class KeepRevision(webapp2.RequestHandler):
    def post(self):
        self.redirect('/load_edit_page')

#Discards a revision.
#TODO: Actually implement.
class DiscardRevision(webapp2.RequestHandler):
    def post(self):
        self.redirect('/load_edit_page')

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

app = webapp2.WSGIApplication([
    ('/delete_item', DeleteItem),
    ('/delete_item_forever', DeleteItemForever),
    ('/undelete_item', UndeleteItem),
    ('/add_item', AddItem),
    ('/edit_item', EditItem),
    ('/enforce_auth', AuthHandler),
    ('/review_edits', ReviewEdits),
    ('/resolve_edits', ResolveEdits),
    ('/edit_item', EditItem),
    ('/load_edit_page',LoadEditPage),
    ('/discard_revision',DiscardRevision),
    ('/keep_revision',KeepRevision),
    ('/.*', MainPage),
], debug=True)
