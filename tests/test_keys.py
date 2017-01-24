# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from datetime import datetime

import pytest
from django.core.urlresolvers import reverse

from atmo.keys.models import SSHKey
from atmo.keys.utils import calculate_fingerprint

key_data = """\
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC4e3cWi5MQKd4yOsvKwzdFCVmaRIwVswVYKEvkDcbi3e7vLx+z1NdibBLWGfBkid8Hgi9pyA5x4XT9aI8jU0J83OjNtwPYr3tZWDmVAPi9gZIVMCDZsshw80zozXRyGJAkvsPnptFqPx1xoRIMt0YSqKn1Mga0YCJXkbZ15Fcn2UQAMm/pJZMIRXpkU2WKDjn4V8H7m2ZdzihlNDOSMhgojzY+32vT1HVIafLfeA71oSx/BLoTtFf812bOwLmqAYd7/FLittmDITPFGcBhZU1YWC+E6Dur+oiMmiJ4ty8PATmAjoqdgzkCT39pYYDThHbCK+NZefiRfJ5w2ZEvbwYr jezdez@Pal
"""
fingerprint = '50:a2:40:cb:2d:a2:38:64:66:ec:40:c7:a2:86:97:18'


def assert_message_contains(response, text, level=None):
    """
    Asserts that there is exactly one message containing the given text.
    """
    messages = response.context['messages']

    matches = [m for m in messages if text in m.message]

    if len(matches) == 1:
        msg = matches[0]
        if level is not None and msg.level != level:
            pytest.fail(
                'There was one matching message but with different'
                'level: %s != %s' % (msg.level, level)
            )

        return

    elif len(matches) == 0:
        messages_str = ", ".join('"%s"' % m for m in messages)
        pytest.fail(
            'No message contained text "%s", messages were: %s' %
            (text, messages_str)
        )
    else:
        pytest.fail(
            'Multiple messages contained text "%s": %s' %
            (text, ", ".join(('"%s"' % m) for m in matches))
        )


def test_create_ssh_key(ssh_key, test_user):
    assert str(ssh_key) == ssh_key.title
    assert ssh_key.prefix == 'ssh-rsa'
    assert ssh_key.created_by == test_user
    assert isinstance(ssh_key.created_at, datetime)
    assert isinstance(ssh_key.modified_at, datetime)
    fingerprint = calculate_fingerprint(ssh_key.key)
    assert ssh_key.fingerprint == fingerprint
    assert repr(ssh_key) == '<SSHKey %s (%s)>' % (ssh_key.title, fingerprint)
    assert ssh_key.get_absolute_url() == reverse('keys-detail',
                                                 kwargs={'id': ssh_key.id})


def test_calculate_fingerprint():
    assert calculate_fingerprint(key_data) == fingerprint


def test_new_ssh_key_get(client, test_user):
    response = client.get(reverse('keys-new'))
    assert response.status_code == 200
    assert 'form' in response.context


@pytest.mark.parametrize("key,exception", [
    # too large key data
    ('1' * 100001, 'The submitted key was larger than 100kB'),
    # invalid key data
    ('ssh-rsa abcdef', 'The submitted key is invalid or misformatted'),
    # unsupported key algorithm
    ('ssh-lol ' + key_data.split()[1], 'The submitted key is not supported'),
])
def test_new_ssh_key_post_errors(client, test_user, key, exception):
    new_data = {
        'sshkey-title': 'A title',
        'sshkey-key': key,
    }
    response = client.post(reverse('keys-new'), new_data, follow=True)
    assert not SSHKey.objects.filter(title='A title').exists()
    assert response.status_code == 200
    assert response.context['form'].errors
    assert exception in response.context['form'].errors['key'][0]


def test_new_ssh_key_post_success(client, test_user):
    new_data = {
        'sshkey-title': 'A title',
        'sshkey-key': key_data,
    }
    response = client.post(reverse('keys-new'), new_data, follow=True)
    ssh_key = SSHKey.objects.get(title='A title')
    assert response.status_code == 200
    assert response.redirect_chain[-1] == (reverse('keys-list'), 302)
    assert ssh_key in response.context['ssh_keys']
    assert_message_contains(response, 'successfully added')


def test_delete_key(client, ssh_key, ssh_key_maker, test_user, test_user2):
    delete_url = reverse('keys-delete', kwargs={'id': ssh_key.id})
    response = client.get(delete_url)
    assert response.status_code == 200

    # login the second user so we can check the delete_sshkey permission
    client.force_login(test_user2)
    response = client.get(delete_url)
    assert response.status_code == 403
    client.force_login(test_user)

    response = client.post(delete_url, follow=True)
    assert response.status_code == 200
    assert response.redirect_chain[-1], (reverse('keys-list') == 302)
    assert_message_contains(response, 'successfully deleted')
    assert not SSHKey.objects.filter(id=ssh_key.id).exists()


def test_view_key(client, ssh_key):
    detail_url = ssh_key.get_absolute_url()
    response = client.get(detail_url, follow=True)
    assert response.status_code == 200


def test_view_raw_key(client, ssh_key):
    raw_url = reverse('keys-raw', kwargs={'id': ssh_key.id})
    response = client.get(raw_url, follow=True)
    assert response.status_code == 200
    assert not response.context
    assert 'text/plain' in response['content-type']


def test_list_keys(client, ssh_key, test_user2):
    list_url = reverse('keys-list')
    response = client.get(list_url, follow=True)
    assert response.status_code == 200
    assert 'ssh_keys' in response.context
    assert ssh_key in response.context['ssh_keys']

    # login the second user so we can check the view_sshkey permission
    client.force_login(test_user2)
    response = client.get(list_url, follow=True)
    assert response.status_code == 200
    assert 'ssh_keys' in response.context
    assert ssh_key not in response.context['ssh_keys']
