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
#from enums import *

## Handlers
class MainPage(webapp2.RequestHandler):
    @auth.login_required

    def get(self):
        try:
            # Load html template
            template = JINJA_ENVIRONMENT.get_template('templates/index.html')

            # Filter search items
            item_name_filter = self.request.get('filter_by_name')
            item_type_filter = self.request.get('filter_by_item_type')
            item_condition_filter = self.request.get('filter_by_condition', allow_multiple=True)
            item_article_filter = self.request.get('filter_by_article', allow_multiple=True)
            costume_size_string_filter = self.request.get('filter_by_costume_size_string', allow_multiple=True)
            costume_size_number_filter = self.request.get('filter_by_costume_size_number', allow_multiple=True)
            query = FilterItems(
                item_name_filter,
                item_type_filter,
                item_condition_filter,
                item_article_filter,
                costume_size_string_filter,
                costume_size_number_filter)

            items = query.fetch()
            # send to display
            self.response.write(template.render({'items': items}))
        except:
            # first time opening or item has been added
            query = Item.query()
            items = query.fetch()
            self.response.write(template.render({'items': items}))

class AddItem(webapp2.RequestHandler):
    @auth.login_required
    def post(self):
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
                description=self.request.get('description', default_value=''),
                qr_code=1234,
                item_type=costume_or_prop,
                condition=self.request.get('condition'),
                clothing_article_type=article_type,
                clothing_size_num=costume_size_number,
                clothing_size_string=costume_size_word,
                tags=tags_list)
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

# Filters viewable items based on selected boxes in MainPage
def FilterItems(item_name, item_type, item_condition, costume_article, costume_size_string, costume_size_number):
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
    return query

# Converts text list of tags to array of tags
def ParseTags(tags_string):
    tags_list = []

    # Find newline character
    tag_end_index = tags_string.find("\n")

    # Check newline character exists in string
    while tag_end_index != -1:
        # Add tag to list
        tags_list.append(tags_string[:tag_end_index])
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
