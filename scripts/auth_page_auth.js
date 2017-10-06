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

$(function(){

    // Initialize Firebase
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

    // Firebase log-in
    // Checks for auth refresh and runs once when the page is loaded.
    function configureFirebaseLogin() {

        firebase.auth().onAuthStateChanged(function(user) {
          if (user) {
            $('#logged-out').hide();

            var name = user.displayName;
            // Never currently run, just for if we add other providers (facebook).
            var welcomeName = name ? name : user.email;

            user.getToken().then(function(idToken) {


                /* Now that the user is authenicated, fetch the notes. */
                userIdToken = idToken;
                setAuthCookie(userIdToken);

                $('#user').text(welcomeName);
                $('#logged-in').show();
                window.location.replace("/post_auth");

            });

            } else {
                $('#logged-out').show();
                $('#logged-in').hide();
            }
        });
    }

    // Firebase log-in widget
    function configureFirebaseLoginWidget() {
        var uiConfig = {
          'signInSuccessUrl': '/post_auth',
          'signInOptions': [
            // Leave the lines as is for the providers you want to offer your users.
            // firebase.auth.GoogleAuthProvider.PROVIDER_ID,
            // firebase.auth.FacebookAuthProvider.PROVIDER_ID,
            // firebase.auth.TwitterAuthProvider.PROVIDER_ID,
            // firebase.auth.GithubAuthProvider.PROVIDER_ID,
            firebase.auth.EmailAuthProvider.PROVIDER_ID
          ],
          // Terms of service url
          'tosUrl': '<your-tos-url>',
        };

        var ui = new firebaseui.auth.AuthUI(firebase.auth());
        ui.start('#firebaseui-auth-container', uiConfig);
    }

    configureFirebaseLogin();
    configureFirebaseLoginWidget();

});
