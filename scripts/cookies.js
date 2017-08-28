function setCookie(name, value, timeout_ms, path) {
    var expiryDate = new Date();
    expiryDate.setTime(expiryDate.getTime() + timeout_ms);
    cookieString = name + "=" + value + ";";
    cookieString += "expires=" + expiryDate.toUTCString() + ";";
    cookieString += "path=" + path;
    document.cookie = cookieString;
}

function deleteCookie(name, path) {
    var expiryDate = new Date();
    expiryDate.setTime(expiryDate.getTime() - 10 * 24 * 60 * 1000); // 10 days ago
    cookieString = name + "=;";
    cookieString += "expires=" + expiryDate.toUTCString() + ";";
    cookieString += "path=" + path;
    document.cookie = cookieString;
}