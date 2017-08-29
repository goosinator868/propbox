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
import list_filter

## Global Variables
name_filter = ""
costume_filter = True
prop_filter = True

## Handlers
def CostumeFilterEnabled():
    global costume_filter
    return costume_filter

def PropFilterEnabled():
    global prop_filter
    return prop_filter

def UpdateVisibleList(name, type):
    global costume_filter, prop_filter, name_filter
    name_filter = name
    if type == "costume":
        costume_filter = True
        prop_filter = False
    elif type == "prop":
        prop_filter = True
        costume_filter = False
    else:
        prop_filter = True
        costume_filter = True
