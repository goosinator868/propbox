// Copyright (c) 2017 Future Gadget Laboratories.

// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:

// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.

// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

cookie_timeout_ms =  15 * 60 * 1000; // 15 minutes

function SetUpFirebase() {

    // Initialize Firebase (only do this once per page)
    var config = {
        apiKey: "AIzaSyA2DvNhn0BkG85Lxot7ox07pt13qIfAo3M",
        authDomain: "uah-management-prototype.firebaseapp.com",
        databaseURL: "https://uah-management-prototype.firebaseio.com",
        projectId: "uah-management-prototype",
        storageBucket: "uah-management-prototype.appspot.com",
        messagingSenderId: "1078008160144"
    };
    firebase.initializeApp(config);

    // This is passed into the backend to authenticate the user.
    var userIdToken = null;

    function setAuthCookie() {
        setCookie("token", userIdToken, cookie_timeout_ms, "/");
    }

    function deleteAuthCookie() {
        deleteCookie("token", "/");
    }

    function sheduleAuthCookieRefresh() {
        setInterval(setAuthCookie, cookie_timeout_ms / 2);
    }

    // Checks for auth refresh and runs once when the page is loaded.
    function configureFirebaseLogin() {

        firebase.auth().onAuthStateChanged(function(user) {
          if (user) {
            /* If the provider gives a display name, use the name for the
            personal welcome message. Otherwise, use the user's email. */
            var name = user.displayName;
            var welcomeName = name ? name : user.email;

            user.getToken().then(function(idToken) {
                userIdToken = idToken;
                setAuthCookie();
                $('#user').text(welcomeName);
            });
          }
        });

        // Sign out a user
        var signOutBtn = $('#sign-out');
        signOutBtn.click(function(event) {
            event.preventDefault();
            console.log('got click');
            deleteAuthCookie();
            firebase.auth().signOut().then(function() {
                console.log("Sign out successful");
                window.location.replace("/enforce_auth");
            }, function(error) {
                console.log(error);
            });
        });
    }

    configureFirebaseLogin();
    sheduleAuthCookieRefresh();

};
