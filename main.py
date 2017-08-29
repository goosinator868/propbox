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

#Little helper function for rendering the main page.
def fetchList():
    return {'items':Item.query().order(-Item.updated).fetch()}

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
            newItem = Item(
                creator_id=auth.get_user_id(self.request),
                name=self.request.get('name'),
                description=self.request.get('description', default_value=''),
                qr_code=1234)
            newItem.put()
            template = JINJA_ENVIRONMENT.get_template('templates/index.html')
            self.response.write(template.render(fetchList()))
            self.redirect("/")
        except:
            # Should never be here unless the token has expired,
            # meaning that we forgot to refresh their token.
            self.redirect("/enforce_auth")

#Marks an item for deletion. DOES NOT ACTUALLY DELETE.
class DeleteItem(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
        #template = JINJA_ENVIRONMENT.get_template('templates/index.html')
        item = ndb.Key(urlsafe=self.request.get('item_id')).get()
        item.deleted = True
        toPut = [item]
        while item.older_version:
            item = item.older_version.get()
            toPut.append(item)
            item.deleted = True
        for i in toPut:
            i.put()
        # TODO: redirect back to items view.
        sleep(0.05)
        self.redirect("/")

#Deletes an item from the database for good. THIS CANNOT BE UNDONE.
class DeleteItemForever(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
        #template = JINJA_ENVIRONMENT.get_template('templates/review_edits.html')
        item = ndb.Key(urlsafe=self.request.get('item_id')).get()
        if item.deleted:
            toDelete = [item]
            while item.older_version:
                item = item.older_version.get()
                toDelete.append(item)
            logging.info("\n\n\n")
            logging.info(toDelete)
            while toDelete:
                delete = toDelete.pop()
                #logging.info(delete)
                delete.key.delete()
        sleep(0.1)
        self.redirect('/load_edit_page')

#Undeletes an item, returning it to the main list. Reverses the changes made by DeleteItem.
class UndeleteItem(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
        #template = JINJA_ENVIRONMENT.get_template('templates/review_edits.html')
        item = ndb.Key(urlsafe=self.request.get('item_id')).get()
        item.deleted = False
        item.put()
        while item.older_version:
            item = item.older_version.get()
            item.deleted = False
            item.put()
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

#Loads the edit page.
class LoadEditPage(webapp2.RequestHandler):
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
    ('/load_edit_page',LoadEditPage),
    ('/keep_revision',KeepRevision),
    ('/discard_revision',DiscardRevision),
    ('/.*', MainPage),
], debug=True)
