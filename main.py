# Python built-in imports.
import os
import urllib
import logging
import webapp2
import jinja2

# Third party imports.
from google.appengine.ext import ndb

# First party imports
from warehouse_models import Item
import auth
from list_filter import *

## Handlers
class MainPage(webapp2.RequestHandler):
    @auth.login_required

    def get(self):
        try:
            template = JINJA_ENVIRONMENT.get_template('templates/index.html')
            item_name_filter = self.request.get('filter_by_name')
            item_type_filter = self.request.get('filter_by_item_type')
            item_condition_filter = self.request.get('filter_by_condition', allow_multiple=True)
            query = FilterItems(item_name_filter, item_type_filter, item_condition_filter)
            #query = Item.query()
            items = query.fetch()
            self.response.write(template.render({'items': items}))
        except:
            query = Item.query()
            items = query.fetch()
            self.response.write(template.render({'items': items}))

class AddItem(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
        try:
            newItem = Item(
                creator_id=auth.get_user_id(self.request),
                name=self.request.get('name'),
                description=self.request.get('description', default_value=''),
                qr_code=1234,
                item_type=self.request.get('item_type'),
                condition=self.request.get('condition'))
            newItem.put()
            self.redirect("/")
        except:
            # Should never be here unless the token has expired,
            # meaning that we forgot to refresh their token.
            self.redirect("/enforce_auth")

class DeleteItem(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
        # Wastes 1 read operation per call.
        item = ndb.Key(urlsafe=self.request.get('item_id')).get()
        item.key.delete()
        # TODO: redirect back to items view.
        self.redirect("/")

class AuthHandler(webapp2.RequestHandler):
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('templates/auth.html')
        self.response.write(template.render({}))

def FilterItems(item_name, item_type, item_condition):
    if (item_type != "All" and item_type != ""):
        query = Item.query(Item.item_type == item_type).order(Item.name)
    else:
        query = Item.query().order(Item.name)

    query = query.filter(Item.condition.IN(item_condition))
    return query

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

app = webapp2.WSGIApplication([
    ('/delete_item', DeleteItem),
    ('/add_item', AddItem),
    ('/enforce_auth', AuthHandler),
    ('/.*', MainPage),
], debug=True)
