"""Cloudigrade views."""
from widgetastic.widget import TextInput, View

from widgetastic_patternfly import Button


class LoginView(View):
    """Login Form UI. Helper to test login form behavior."""

    login = Button('Log In', classes=[Button.PRIMARY])
    username = TextInput(locator='#email')
    password = TextInput(locator='#password')
