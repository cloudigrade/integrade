"""Utilities functions for API tests."""
import time

from selenium.common.exceptions import StaleElementReferenceException


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


def find_element_by_text(driver, text,
                         fail_hard=False,
                         n=0,
                         exact=True,
                         timeout=0.1):
    """Find an element which contains the given text."""
    start = time.time()
    end = start + timeout
    while time.time() < end:
        def t(e):
            try:
                try:
                    return e.__innerText
                except AttributeError:
                    e.__innerText = e.get_attribute('innerText')
                    return e.__innerText
            except StaleElementReferenceException:
                return ''
        elements = [
            e for e in
            driver.find_elements_by_xpath('//*[contains(.,\'%s\')]' % text)
            if (text == t(e) if exact else text in t(e))
        ]
        if elements:
            elements.sort(key=lambda e: (len(t(e)), -get_element_depth(e)))
            return elements[n]
    if fail_hard:
        raise ValueError(
            'Did not find in page: %r\n%s' %
            (text, driver.page_source)
        )


def fill_input_by_label(driver, element, label, value):
    """Click on a field label and enter text to the associated input."""
    find_element_by_text(element or driver, label).click()
    input = driver.execute_script('return document.activeElement')
    input.clear()
    input.send_keys(value)


def read_input_by_label(driver, element, label):
    """Click on a field label and read text from the associated input."""
    find_element_by_text(element or driver, label).click()
    input = driver.execute_script('return document.activeElement')
    return input.get_attribute('value')
