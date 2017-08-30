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
        template = JINJA_ENVIRONMENT.get_template('templates/index.html')
        query = FilterItems()
        items = query.fetch()
        self.response.write(template.render({'items': items}))

class UpdateItemsFilter(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
        try:
            name_filter = self.request.get('filter_by_name')
            item_type_filter = self.request.get('filter_by_item_type')
            condition_filter_good = self.request.get('filter_by_condition_good', default_value=False)
            condition_filter_fair = self.request.get('filter_by_condition_fair', default_value=False)
            condition_filter_poor = self.request.get('filter_by_condition_poor', default_value=False)
            condition_filter_repair = self.request.get('filter_by_condition_repair', default_value=False)
            UpdateVisibleList(name_filter, item_type_filter, condition_filter_good,
                condition_filter_fair, condition_filter_poor,
                condition_filter_repair)
            self.redirect("/")
        except:
            # Should never be here unless the token has expired,
            # meaning that we forgot to refresh their token.
            self.redirect("/enforce_auth")

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

def FilterItems():
    if CostumeFilterEnabled() == True and PropFilterEnabled() == False:
        query = Item.query(Item.item_type == "Costume").order(-Item.updated, Item.condition)
    elif CostumeFilterEnabled() == False and PropFilterEnabled() == True:
        query = Item.query(Item.item_type == "Prop").order(-Item.updated, Item.condition)
    else:
        query = Item.query().order(-Item.updated, Item.condition)

    # Handles Condition selection options
    if ConditionGoodFilterEnabled():
        if ConditionFairFilterEnabled():
            if ConditionPoorFilterEnabled():
                if ConditionRepairFilterEnabled():
                    query = query.filter(ndb.OR(Item.condition == "Good", Item.condition == "Fair", Item.condition == "Poor", Item.condition == "Being Repaired"))
                else:
                    query = query.filter(ndb.OR(Item.condition == "Good", Item.condition == "Fair", Item.condition == "Poor"))
            else:
                if ConditionRepairFilterEnabled():
                    query = query.filter(ndb.OR(Item.condition == "Good", Item.condition == "Fair", Item.condition == "Being Repaired"))
                else:
                    query = query.filter(ndb.OR(Item.condition == "Good", Item.condition == "Fair"))
        else:
            if ConditionPoorFilterEnabled():
                if ConditionRepairFilterEnabled():
                    query = query.filter(ndb.OR(Item.condition == "Good", Item.condition == "Poor", Item.condition == "Being Repaired"))
                else:
                    query = query.filter(ndb.OR(Item.condition == "Good", Item.condition == "Poor"))
            else:
                if ConditionRepairFilterEnabled():
                    query = query.filter(ndb.OR(Item.condition == "Good", Item.condition == "Being Repaired"))
                else:
                    query = query.filter(Item.condition == "Good")
    else:
        if ConditionFairFilterEnabled():
            if ConditionPoorFilterEnabled():
                if ConditionRepairFilterEnabled():
                    query = query.filter(ndb.OR(Item.condition == "Fair", Item.condition == "Poor", Item.condition == "Being Repaired"))
                else:
                    query = query.filter(ndb.OR(Item.condition == "Fair", Item.condition == "Poor"))
            else:
                if ConditionRepairFilterEnabled():
                    query = query.filter(ndb.OR(Item.condition == "Fair", Item.condition == "Being Repaired"))
                else:
                    query = query.filter(Item.condition == "Being Repaired")
        else:
            if ConditionPoorFilterEnabled():
                if ConditionRepairFilterEnabled():
                    query = query.filter(ndb.OR(Item.condition == "Poor", Item.condition == "Being Repaired"))
                else:
                    query = query.filter(Item.condition == "Poor")
            else:
                if ConditionRepairFilterEnabled():
                    query = query.filter(Item.condition == "Being Repaired")
                else:
                    query = query.filter(Item.condition == "")

    return query

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

app = webapp2.WSGIApplication([
    ('/delete_item', DeleteItem),
    ('/add_item', AddItem),
    ('/enforce_auth', AuthHandler),
    ('/update_items_filter', UpdateItemsFilter),
    ('/.*', MainPage),
], debug=True)
