# Python built-in imports.
from functools import wraps

# Third party imports.
from google.appengine.ext import ndb
import google.oauth2.id_token
import requests_toolbelt.adapters.appengine
import google.auth.transport.requests

# First party imports.
from warehouse_models import User

# Use the App Engine Requests adapter. This makes sure that Requests uses
# URLFetch.
requests_toolbelt.adapters.appengine.monkeypatch()
HTTP_REQUEST = google.auth.transport.requests.Request()

def GetCurrentUser(request):
    return ndb.Key(User, get_user_id(request)).get()

def get_cookies(request):
    cookies = {}
    raw_cookies = request.headers.get("Cookie")
    if raw_cookies:
        for cookie in raw_cookies.split(";"):
            cookie = cookie.strip()
            k_v = cookie.split("=")
            if len(k_v) >= 2:
                cookies[k_v[0]] = k_v[1]
    return cookies

def firebase_login_required(handler):
    def _decorator(_self, *args, **kwargs):
        cookies = get_cookies(_self.request)
        id_token = cookies.get('token')
        claims = None
        try:
            if id_token is not None:
                claims = google.oauth2.id_token.verify_firebase_token(id_token, HTTP_REQUEST)
        except:
            claims = None
        if claims is None:
            _self.redirect("/enforce_auth")
            return
        else:
            handler(_self, *args, **kwargs)
    return wraps(handler)(_decorator)

def login_required(handler):
    def _decorator(_self, *args, **kwargs):
        cookies = get_cookies(_self.request)
        id_token = cookies.get('token')
        claims = None
        try:
            if id_token is not None:
                claims = google.oauth2.id_token.verify_firebase_token(id_token, HTTP_REQUEST)
        except:
            claims = None
        if claims is None:
            _self.redirect("/enforce_auth")
            return
        user = GetCurrentUser(_self.request)
        if user is None:
            user = User(name=get_user_name(_self.request), id=get_user_id(_self.request), permissions="PENDING_USER")
            if len(User.query(User.permissions == "ADMIN").fetch()) == 0:
                user.permissions = "ADMIN"
            user.put()
        if user.permissions == "PENDING_USER":
            _self.redirect("/pending_approval")
            return
        if user.permissions == "DEACTIVATED_USER":
            _self.redirect("/account_deactivated")
        else:
            handler(_self, *args, **kwargs)
    return wraps(handler)(_decorator)


def _get_claims(request):
    cookies = get_cookies(request)
    id_token = cookies.get('token')
    claims = google.oauth2.id_token.verify_firebase_token(id_token, HTTP_REQUEST)
    print(claims)
    return claims

def get_user_name(request):
    claims = _get_claims(request)
    return claims.get('name', 'UNKNOWN')

def get_user_id(request):
    claims = _get_claims(request)
    return claims.get('user_id')
