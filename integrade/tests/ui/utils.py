"""Utilities functions for API tests."""
import time

from selenium.common.exceptions import StaleElementReferenceException

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
    elements.sort(key=lambda e: (len(get_el_text(e)), -get_element_depth(e)))

    if fail_hard and not elements:
        raise ValueError(
            'Did not find in page: %r\n%s' %
            (text, driver.page_source)
        )
    elif elements:
        return elements[0]


def find_elements_by_text(driver, text,
                          exact=True,
                          timeout=None,
                          tag=None):
    """Find an element which contains the given text.

    parameters:
    - driver            Selenium or Element instance to locate under
    - text              Text to search for on the page
    - n=0               If multiple results are found, return the N'th one
                        counting from the most specific to least.
                        "Specific" is defined by the length and depth of the
                        matched element. The shorter the overall text of the
                        element and the greater depth in the DOM the more
                        specific it is considered. (length is only applicable
                        when exact=False, otherwise only depth defines the
                        specificity)
    - exact=True        Only locate elements that exactly match the text. If
                        False, locate elements which contain the text somewhere
                        in their content. (See n parameter description for the
                        affects on specificity)
    - timeout=0.1       Time to spend re-checking for text to appear on page.
                        Larger values behave as a "wait for..." search for the
                        text.

    """
    timeout = timeout or 0.1
    with timemetric('find_elements_by_text()'):
        start = time.time()
        end = start + timeout
        elements = []
        while time.time() < end:
            elements = [
                e for e in
                driver.find_elements_by_xpath(
                    '//*[contains(.,\'%s\')]'
                    % (text,)
                )
                if (
                    text == get_el_text(e)
                    if exact else text in get_el_text(e)
                 ) and e.is_displayed()
            ]
        return elements


def fill_input_by_label(driver, element, label, value, timeout=None):
    """Click on a field label and enter text to the associated input."""
    elements = find_elements_by_text(element or driver, label, timeout=timeout)
    elements[-1].click()
    input = driver.execute_script('return document.activeElement')
    input.clear()
    input.send_keys(value)
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
    find_element_by_text(element or driver, label).click()
    input = driver.execute_script('return document.activeElement')
    return input.get_attribute('value')


def retry_w_timeout(t, func, *args, **kwargs):
    """Retry a function until it returns truthy or a timeout occures."""
    start = time.time()
    end = start
    while end - start < t:
        retval = func(*args, **kwargs)
        if retval:
            return retval
        end = time.time()


def _page_has_text(driver, text):
    """Simply check if text exists in the page, irrespective of markup."""
    body = driver.find_element_by_tag_name('body')
    page_text = ' '.join(body.get_attribute('innerText').split())
    return text in page_text


def page_has_text(driver, text, timeout=5):
    """Wait for text to be seen in page, irrespective of markup, or timeout."""
    return retry_w_timeout(timeout, _page_has_text, driver, text)
