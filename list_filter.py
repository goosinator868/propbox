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
costume_filter = False
prop_filter = True

## Handlers
def UpdateVisibleList(list):
    new_list = [];
    if costume_filter == True && prop_filter == False:
        for item in list:
            if item.type == "prop":
                newlist.append(item)
    elif costume_filter == False && prop_filter == True:
        for item in list:
            if item.type == "costume":
                newlist.append(item)

    return newlist



def FilterVisibleList(name, costume, prop):
    global name_filter, costume_filter, prop_filter
    name_filter = name
    if costume == "yes":
        costume_filter = True
    else:
        costume_filter = False

    if prop == "yes":
        prop_filter = True
    else:
        prop_filter = False
