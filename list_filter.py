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

def UpdateVisibleList(name, costume, prop):
    global costume_filter, prop_filter, name_filter
    name_filter = name
    if costume == "yes":
        costume_filter = True
    else:
        costume_filter = False

    if prop == "yes":
        prop_filter = True
    else:
        prop_filter = False
