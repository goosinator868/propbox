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
from warehouse_models import Item
import auth

class OutdatedEditException(Exception):
    def __init__(self,*args,**kwargs):
        Exception.__init__(self,*args,**kwargs)

# Little helper function for rendering the main page.
def fetchList():
    return {'items':Item.query().order(-Item.updated).fetch()}

# Finds the most recent version of an item, if deleted return None.
def FindUpdatedItem(item):
    while item.outdated:
        item = item.child.get()
    return None if item.deleted else item

@ndb.transactional(xg=True)
def AttemptEdit(old_key, new_item):
    old_item = old_key.get()
    if old_item.outdated:
        raise OutdatedEditException()
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
        self.response.write(template.render(fetchList()))

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
            template = JINJA_ENVIRONMENT.get_template('templates/index.html')
            self.response.write(template.render(fetchList()))
            self.redirect("/")
        except:
            # Should never be here unless the token has expired,
            # meaning that we forgot to refresh their token.
            self.redirect("/enforce_auth")

# TODO: Make transactional.
class EditItem(webapp2.RequestHandler):
    @auth.login_required
    def get(self):
        base_id = ndb.Key(urlsafe=self.request.get('base_id'))
        item = base_id.get()
        item = FindUpdatedItem(item)
        new_item = item
        new_key_str = self.request.get('new_key')
        if new_key_str:
            new_item = ndb.Key(urlsafe=new_key_str).get()
        template = JINJA_ENVIRONMENT.get_template('templates/edit_item.html')
        self.response.write(template.render({'old_item': item, 'new_item': new_item}))

    @auth.login_required
    def post(self):
        old_key = ndb.Key(urlsafe=self.request.get('parent_id'))
        new_item = Item(
            creator_id=auth.get_user_id(self.request),
            name=self.request.get('name'),
            description=self.request.get('description', default_value=''),
            qr_code=1234)
        try:
            AttemptEdit(old_key, new_item)
            self.redirect("/")
        except OutdatedEditException as e:
            new_item.parent = None
            conflict_key = FindUpdatedItem(old_key.get()).key
            # Mark this item as an attempted change that could not be commited.
            new_item.orphan = True
            new_key = new_item.put()
            self.redirect("/edit_item?" + urllib.urlencode({'base_id': conflict_key.urlsafe(), 'new_key': new_key.urlsafe()}))

# Marks an item for deletion. DOES NOT ACTUALLY DELETE.
# TODO: Make transactional.
class DeleteItem(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
        template = JINJA_ENVIRONMENT.get_template('templates/index.html')
        id_string = self.request.get('item_id')
        item = ndb.Key(urlsafe=id_string).get()
        item.deleted = True
        item.put()

        # Redirect back to items view.
        sleep(0.05)
        self.redirect("/")

# Deletes an item from the database for good. THIS CANNOT BE UNDONE.
# TODO: Make transactional.
class DeleteItemForever(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
        template = JINJA_ENVIRONMENT.get_template('templates/review_edits.html')
        item = ndb.Key(urlsafe=self.request.get('item_id')).get()
        # TODO: ensure this has no children.
        # TODO: delete all parents.
        if item.deleted:
            item.key.delete()
        sleep(0.1)
        self.redirect('/load_edit_page')

# Undeletes an item, returning it to the main list. Reverses the changes made by DeleteItem.
# TODO: Make transactional.
class UndeleteItem(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
        template = JINJA_ENVIRONMENT.get_template('templates/review_edits.html')
        item = ndb.Key(urlsafe=self.request.get('item_id')).get()
        if item.deleted:
            item.deleted = False
            item.put()
        sleep(0.1)
        self.redirect('/')


class AuthHandler(webapp2.RequestHandler):
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('templates/auth.html')
        self.response.write(template.render({}))

# Loads the edit page.
class ReviewEdits(webapp2.RequestHandler):
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('templates/review_edits.html')
        query = Item.query().order(-Item.updated)
        items = query.fetch()
        deleted = []
        outdated = []
        for item in items:
            if item.deleted: 
                deleted.append(item)
            elif item.outdated: #TODO: fix outdated listing.
                outdated.append(item)
        self.response.write(template.render({'deleted':deleted,'outdated':outdated}))

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

app = webapp2.WSGIApplication([
    ('/delete_item', DeleteItem),
    ('/delete_item_forever', DeleteItemForever),
    ('/undelete_item', UndeleteItem),
    ('/add_item', AddItem),
    ('/enforce_auth', AuthHandler),
    ('/review_edits', ReviewEdits),
    ('/edit_item', EditItem),
    ('/.*', MainPage),
], debug=True)
