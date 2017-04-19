"""
A pytest fixture that provides easy assertion tools for
django.contrib.messages based on a Django test client response.

This is partially based on ojii's unittest mixin
(https://gist.github.com/ojii/1269949), all credit to them.
"""
import pytest
from django.contrib.messages import get_messages
from pytest_django.lazy_django import skip_if_no_django


class Messages:

    def __init__(self):
        self._messages = None

    def get_messages(self, response):
        if self._messages is None:
            self._messages = get_messages(response.wsgi_request)
        return self._messages

    def filter_messages(self, messages, message, level=None):
        found = [msg for msg in messages if message in msg.message]
        if level:
            found = [msg for msg in found if msg.level == level]
        return found

    def assert_message_count(self, response, expected):
        messages = self.get_messages(response)
        actual_num = len(messages)
        if actual_num != expected:
            pytest.fail(
                'Message count was %d, expected %d' % (actual_num, expected)
            )

    def assert_message_contains(self, response, message, level=None):
        messages = self.get_messages(response)
        found = self.filter_messages(messages, message, level)
        if not found:
            messages = [
                '%s (%s)' % (msg.message, msg.level)
                for msg in messages
            ]
            if level:
                pytest.fail(
                    'Message %r with level %r not found in request. '
                    'Available messages: %r' %
                    (message, level, messages)
                )
            else:
                pytest.fail(
                    'Message %r not found in request. '
                    'Available messages: %r' %
                    (message, messages)
                )

    def assert_message_misses(self, response, message, level=None):
        messages = self.get_messages(response)
        found = self.filter_messages(messages, message, level)
        if found:
            if level:
                pytest.fail(
                    'Message %r with level %r found in request' %
                    (message, level)
                )
            else:
                pytest.fail('Message %r found in request' % message)


@pytest.fixture()
def messages():
    """A Django test client instance with support for messages"""
    skip_if_no_django()
    return Messages()
