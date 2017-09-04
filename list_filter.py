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
condition_good_filter = True
condition_fair_filter = True
condition_poor_filter = True
condition_repair_filter = True

## Handlers
# Return true if filtering by costume
def CostumeFilterEnabled():
    global costume_filter
    return costume_filter

# Return true if filtering by prop
def PropFilterEnabled():
    global prop_filter
    return prop_filter

# Return true if filtering by good condition
def ConditionGoodFilterEnabled():
    global condition_good_filter
    return condition_good_filter

# Return true if filtering by fair condition
def ConditionFairFilterEnabled():
    global condition_fair_filter
    return condition_fair_filter

# Return true if filtering by poor condition
def ConditionPoorFilterEnabled():
    global condition_poor_filter
    return condition_poor_filter

# Return true if filtering by repair condition
def ConditionRepairFilterEnabled():
    global condition_repair_filter
    return condition_repair_filter

# Update search filter by name, type, and condition
def UpdateVisibleList(name, type, good_condition, fair_condition,
    poor_condition, repair_condition):
    global costume_filter, prop_filter, name_filter, condition_good_filter
    global condition_fair_filter, condition_poor_filter, condition_repair_filter

    name_filter = name
    condition_good_filter = good_condition
    condition_fair_filter = fair_condition
    condition_poor_filter = poor_condition
    condition_repair_filter = repair_condition

    if type == "costume":
        costume_filter = True
        prop_filter = False
    elif type == "prop":
        prop_filter = True
        costume_filter = False
    else:
        prop_filter = True
        costume_filter = True
