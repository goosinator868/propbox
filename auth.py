"""
Copyright (c) 2017 Future Gadget Laboratories.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

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
            user = User(name=get_user_name(_self.request), id=get_user_id(_self.request), permissions="Pending user")
            if len(User.query(User.permissions == "Admin").fetch()) == 0:
                user.permissions = "Admin"
            user.put()
        if user.permissions == "Pending user":
            _self.redirect("/pending_approval")
            return
        if user.permissions == "Deactivated user":
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
