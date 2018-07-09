"""Utilities functions for API tests."""


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
        return self.value in driver.page_source


def get_element_depth(element):
    """Determine the depth of the element in the page, counting from body.

    Used to find the most specific element out of a set of matching
    elements for a condition where an element and its ancestors might match.
    """
    depth = 1
    next_element = element.find_element_by_xpath('..')
    while next_element.tag_name.lower() != 'body':
        depth += 1
        assert depth < 100

        next_element = next_element.find_element_by_xpath('..')
    return depth


def find_element_by_text(driver, text, fail_hard=False):
    """Find an element which contains the given text."""
    def t(e):
        try:
            return e.__innerHTML
        except AttributeError:
            e.__innerHTML = e.get_attribute('innerHTML')
            return e.__innerHTML
    elements = [
        e for e in
        driver.find_elements_by_xpath('//*[text()[contains(.,\'%s\')]]' % text)
        if text in t(e)
    ]
    if elements:
        elements.sort(key=lambda e: len(t(e)))
        return elements[0]
    elif fail_hard:
        raise ValueError('Did not find in page: %r\n%s' %
                         (text, driver.page_source)
                         )