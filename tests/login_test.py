from selenium import webdriver

# Make sure you have webdriver installed selenium / webdriver
#       pip install selenium
# Make sure you download and install the chrome webdriver from
# https://sites.google.com/a/chromium.org/chromedriver/downloads
# Just place the executable somewhere on your computer and add
# that location to your path.
# Example:
#     1) I placed it in C:\ProgramFiles\chromedriver
#     2) I added C:\ProgramFiles\chromedriver to my path

def setupTestingEnv():
    # Setup
    driver = webdriver.Chrome()
    driver.get("localhost:8080")
    # Tell the browser to wait for up to 10s before reporting that it can't find an element.
    driver.implicitly_wait(10)
    return driver


def login(driver, email="test@fake.org", name="Automated Test", password="password"):
    # First screen
    email_elem = driver.find_element_by_name('email')
    email_elem.send_keys(email)
    next = driver.find_element_by_css_selector('.firebaseui-id-submit')
    next.click()
    # Second screen
    # This can be one of 2 screens:
    #    1) The automated tester has not made an account.
    #    2) The automated tester has made an account and just needs to log in.
    try:
        # The automated tester has been run before.
        password_elem = driver.find_element_by_name('password')
        password_elem.send_keys(password)
    except:
        # It is the first time the automated tester has been run.
        # This will take 10s at least since we implicitly wait 10s before throwing exceptions.
        new_password = driver.find_element_by_name('newPassword')
        new_password.send_keys(password)
        name_elem = driver.find_element_by_name('name')
        name_elem.send_keys(name)

    next = driver.find_element_by_css_selector('.firebaseui-id-submit')
    next.click()

def main():
    driver = setupTestingEnv()
    login(driver)
    print("done")
    driver.quit()

if __name__ == '__main__':
    main()
