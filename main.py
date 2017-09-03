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

## Handlers
class MainPage(webapp2.RequestHandler):
    @auth.login_required
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('templates/index.html')
        query = Item.query().order(-Item.updated)
        items = query.fetch()
        self.response.write(template.render({'items': items}))

class AddItem(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
        try:
            newItem = Item(
                creator_id=auth.get_user_id(self.request),
                name=self.request.get('name'),
                image=self.request.get('image', default_value=''),
                description=self.request.get('description', default_value=''),
                qr_code=1234)
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

class ViewImage(webapp2.RequestHandler):
    def get(self):
        item_key = ndb.Key(urlsafe=self.request.get('entity_id'))
        item = item_key.get()
        self.response.headers['Content-Type'] = 'image/png'
        self.response.out.write(item.image)

class AuthHandler(webapp2.RequestHandler):
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('templates/auth.html')
        self.response.write(template.render({}))

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

app = webapp2.WSGIApplication([
    ('/delete_item', DeleteItem),
    ('/add_item', AddItem),
    ('/view_image', ViewImage),
    ('/enforce_auth', AuthHandler),
    ('/.*', MainPage),
], debug=True)
