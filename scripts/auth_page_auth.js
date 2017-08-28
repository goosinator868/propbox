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
                window.location.replace("/");

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
          'signInSuccessUrl': '/',
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
