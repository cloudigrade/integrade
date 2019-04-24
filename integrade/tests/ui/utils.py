"""Utilities functions for API tests."""
import time

from selenium.common.exceptions import (
    InvalidElementStateException,
    StaleElementReferenceException,
    WebDriverException,
)

from ..conftest import timemetric


class wait_for_input_value(object):
    """Selenium Wait helper to wait until an input has a specific value."""

    def __init__(self, locator, value):
        """Save element locator and expected value for later."""
        self.locator = locator
        self.value = value

    def __call__(self, driver):
        """Check if the element exists with the expected value yet."""
        element = driver.find_element(*self.locator)
        return element.get_attribute('value') == self.value


class wait_for_page_text(object):
    """Selenium Wait helper to wait until specific text appears."""

    def __init__(self, value):
        """Initilaize and save expected text to check for later."""
        self.value = value

    def __call__(self, driver):
        """Check if the expected check appears in the page yet."""
        body = driver.find_element_by_tag_name('body')
        return self.value in body.get_attribute('innerText')


class wait_for_result(object):
    """Selenium Wait helper to wait until specific text appears."""

    def __init__(self, timeout, func, *args, **kwargs):
        """Initilaize and save expected text to check for later."""
        self.timeout = timeout
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def __call__(self, driver):
        """Check if the expected check appears in the page yet."""
        start = time.time()
        end = start + self.timeout
        while time.time() < end:
            retval = self.func(*self.args, **self.kwargs)
            if retval:
                return retval
        return None


def back_in_time(session, months):
    """Manipulate browser to go to previous months.

    :param months: A timespan of how far back you want to go measured in a
        number of months.
    :param session: Pass browser_session from current location in call.
    :returns: Nothing. The browser window should be updated to the new date
    filter.
    """
    dropdown = find_element_by_text(session, 'Last 30 Days')
    dropdown.click()
    time.sleep(0.25)
    toolbar = session.find_elements_by_xpath(
        '//form[@class="toolbar-pf-actions"]')
    dropdowns = toolbar[0].find_elements_by_xpath('//div[@class="form-group"]')
    desired_month = dropdowns[0].find_elements_by_xpath('//ul/li/a')
    desired_month[months].click()
    time.sleep(0.25)


def get_element_depth(element):
    """Determine the depth of the element in the page, counting from body.

    Used to find the most specific element out of a set of matching
    elements for a condition where an element and its ancestors might match.
    """
    depth = 1
    if element.tag_name.lower() in ('html', 'body'):
        return depth
    next_element = element.find_element_by_xpath('..')
    while next_element.tag_name.lower() not in ('html', 'body'):
        depth += 1
        assert depth < 100

        next_element = next_element.find_element_by_xpath('..')
    return depth


def get_el_text(e):
    """Get the inner text of a WebElement and cache for quicker re-lookup."""
    try:
        try:
            return e.__innerText
        except AttributeError:
            text = ' '.join(e.get_attribute('innerText').split())
            e.__innerText = text
            return e.__innerText
    except StaleElementReferenceException:
        return ''


def find_element_by_text(driver, text, *args, **kwargs):
    """Find an element which contains the given text.

    If multiple results are found, return them ordered
    counting from the most specific to least.

    "Specific" is defined by the length and depth of the
    matched element. The shorter the overall text of the
    element and the greater depth in the DOM the more
    specific it is considered. (length is only applicable
    when exact=False, otherwise only depth defines the
    specificity)

    parameters:
    - driver            Selenium or Element instance to locate under
    - text              Text to search for on the page
    - fail_hard=False   If True, raise exception on failure to locate
    - exact=True        Only locate elements that exactly match the text. If
                        False, locate elements which contain the text somewhere
                        in their content. (See n parameter description for the
                        affects on specificity)
    - timeout=0.1       Time to spend re-checking for text to appear on page.
                        Larger values behave as a "wait for..." search for the
                        text.

    """
    fail_hard = kwargs.pop('fail_hard', False)
    elements = find_elements_by_text(driver, text, *args, **kwargs)
    # elements.sort(key=lambda e: (len(get_el_text(e)), -get_element_depth(e)))

    if fail_hard and not elements:
        raise ValueError(
            'Did not find in page: %r\n%s' %
            (text, driver.page_source)
        )
    elif elements:
        return elements[0]


def find_elements_by_text(driver, text,
                          n=0,
                          exact=True,
                          selector='*',
                          timeout=None):
    """Find an element which contains the given text."""
    if driver.__class__.__name__ == 'WebElement':
        element = driver
        while driver.__class__.__name__ == 'WebElement':
            driver = driver._parent
    else:
        element = None

    start = time.time()
    end = start + (timeout or 5)

    with timemetric('find_elements_by_text()'):
        while time.time() < end:
            elements = driver.execute_script("""
            var ctx = arguments[0]
            var text = arguments[1]
            var exact = arguments[2]
            var selector = arguments[3]

            function depth(top, el) {
                var n = el.parentNode
                var d = 0
                while (n && n != top) {
                    d++
                    n = n.parentNode
                }
                return d
            }

            var all = (ctx || document).querySelectorAll(selector)
            var check = (el) => el.textContent.indexOf(text) > -1
            if (exact) {
                check = (el) => el.textContent.trim() == text
            }

            var elements = Array.prototype.filter.call(all, check)
            elements = Array.prototype.filter.call(elements,
                (el) => el.offsetParent !== null
            )

            elements.sort((a, b) => {
                if (a.textContent.length < b.textContent.length) {
                    return true
                } else if (a.textContent.length > b.textContent.length) {
                    return false
                } else {
                    return depth(document.body, a) < depth(document.body, b)
                }
            })

            /* uncomment for debugging */
            /*window.last_results = {
                target: ctx,
                all: all,
                elements: elements,
            }*/ /* uncomment for debugging */

            return elements
            """, element, text, exact, selector)

            if elements:
                return elements


def fill_input_by_label(driver, element, label, value, timeout=None):
    """Click on a field label and enter text to the associated input."""
    input = None

    @retry_w_timeout(1)
    def _():
        nonlocal input
        el = find_element_by_text(element or driver, label,
                                  timeout=0.2, selector='label')

        el.click()
        input = driver.execute_script('return document.activeElement')
        try:
            input.clear()
        except InvalidElementStateException:
            return False
        else:
            input.send_keys(value)
            return True

    return input


def fill_input_by_placeholder(driver, element, label, value):
    """Click on a field label and enter text to the associated input."""
    css_sel = '[placeholder="%s"]' % label
    input = (element or driver).find_element_by_css_selector(css_sel)
    input.clear()
    input.send_keys(value)
    return input


def read_input_by_label(driver, element, label):
    """Click on a field label and read text from the associated input."""
    value = None

    @retry_w_timeout(1)
    def _():
        nonlocal value

        el = find_element_by_text(element or driver, label, selector='label')
        try:
            el.click()
        except WebDriverException as e:
            return e
        input = driver.execute_script('return document.activeElement')
        value = input.get_attribute('value')

        return value

    return value


def retry_w_timeout(t, func=None, *args, **kwargs):
    """Retry a function until it returns truthy or a timeout occures."""
    if func is None:
        def dec(func, *args, **kwargs):
            return retry_w_timeout(t, func, *args, **kwargs)
        return dec
    else:
        start = time.time()
        end = start
        while end - start < t:
            retval = func(*args, **kwargs)
            if retval and not isinstance(retval, BaseException):
                return retval
            end = time.time()
        if isinstance(retval, BaseException):
            raise retval


def _page_has_text(driver, text):
    """Simply check if text exists in the page, irrespective of markup."""
    body = driver.find_element_by_tag_name('body')
    page_text = ' '.join(body.get_attribute('innerText').split())
    return text in page_text


def page_has_text(driver, text, timeout=5):
    """Wait for text to be seen in page, irrespective of markup, or timeout."""
    return retry_w_timeout(timeout, _page_has_text, driver, text)


def _element_has_text(element, text):
    """Simply check if text exists in the element, irrespective of markup."""
    element_text = ' '.join(element.get_attribute('innerText').split('\n'))
    return text in element_text


def element_has_text(element, text, timeout=5):
    """Wait for text in element, irrespective of markup, or timeout."""
    return retry_w_timeout(timeout, _element_has_text, element, text)


def elem_parent(elem):
    """Return the parent of a given element."""
    return elem.find_element_by_xpath('..')


class return_url:
    """Conext manager to control return back to a URL after steps completed."""

    def __init__(self, browser):
        """Initialize with reference to the WebDriver."""
        self.browser = browser

    def __enter__(self):
        """Remember current URL before entering context."""
        self.url = self.browser.current_url

    def __exit__(self, *args):
        """Return to original URL outside context."""
        self.browser.get(self.url)


def unflag_everything(browser_session):
    """Check that all flaggable boxes are not flagged."""
    flag_path = '//span/span[contains(@class, "fa-flag")]'
    # check if on summary or detail page (url ends in '/accounts')
    current_url = browser_session.current_url
    last_word = current_url.rsplit('/', 1)[1]
    summary_page = bool(last_word == 'accounts')
    while browser_session.find_elements_by_xpath(flag_path):
        if summary_page:
            # Since on summary page, go to detail page to interact with flags.
            # Find flagged item
            flag_ctns = browser_session.find_elements_by_xpath(flag_path)
            # find it's parent div to get to detail page
            ctn = flag_ctns[0].find_element_by_xpath('../../..')
            ctn.click()
            time.sleep(0.25)

        # Expand details to expose flag interface
        ami_id = browser_session.find_element_by_class_name(
            'list-view-pf-description')
        ami_id.click()
        time.sleep(0.25)

        ctn = browser_session.find_elements_by_xpath(
            '//div[@class="cloudmeter-list-container"]')
        ctn = ctn[0]
        flags = find_elements_by_text(ctn, 'Flagged for review')

        # flags is a list of nested divs that all contain the text 'Flagged for
        # review by virtue of their child dev containing the text. I only want
        # to click on the inner-most one. So of the 8 returned, the third and
        # seventh are the ones.
        if bool(flags) and len(flags) == 4:
            flags[3].click()
        elif bool(flags) and len(flags) == 8:
            flags[3].click()
            flags[7].click()
        # Go back to the main page if that's where you started
        if summary_page:
            accounts = browser_session.find_elements_by_class_name(
                'cloudmeter-breadcrumb')[0]
            link = find_element_by_text(accounts, 'Accounts')
            link.click()
