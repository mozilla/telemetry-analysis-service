# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from datetime import datetime

import pytest
from django.core.urlresolvers import reverse

from atmo.keys.factories import rsa_key
from atmo.keys.models import SSHKey
from atmo.keys.utils import calculate_fingerprint

key_data = """\
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC4e3cWi5MQKd4yOsvKwzdFCVmaRIwVswVYKEvkDcbi3e7vLx\
+z1NdibBLWGfBkid8Hgi9pyA5x4XT9aI8jU0J83OjNtwPYr3tZWDmVAPi9gZIVMCDZsshw80zozXRyGJAkvsPn\
ptFqPx1xoRIMt0YSqKn1Mga0YCJXkbZ15Fcn2UQAMm/pJZMIRXpkU2WKDjn4V8H7m2ZdzihlNDOSMhgojzY+32\
vT1HVIafLfeA71oSx/BLoTtFf812bOwLmqAYd7/FLittmDITPFGcBhZU1YWC+E6Dur+oiMmiJ4ty8PATmAjoqd\
gzkCT39pYYDThHbCK+NZefiRfJ5w2ZEvbwYr jezdez@Pal
"""
fingerprint = '50:a2:40:cb:2d:a2:38:64:66:ec:40:c7:a2:86:97:18'


def test_new_ssh_key(ssh_key, user):
    assert str(ssh_key) == ssh_key.title
    assert ssh_key.prefix == 'ssh-rsa'
    assert ssh_key.created_by == user
    assert isinstance(ssh_key.created_at, datetime)
    assert isinstance(ssh_key.modified_at, datetime)
    fingerprint = calculate_fingerprint(ssh_key.key)
    assert ssh_key.fingerprint == fingerprint
    assert (
        "<atmo.keys.models.SSHKey title='id_rsa' fingerprint='%s'" % ssh_key.fingerprint
        in
        repr(ssh_key)
    )

    assert (
        ssh_key.urls.detail ==
        ssh_key.get_absolute_url() ==
        reverse('keys-detail', kwargs={'id': ssh_key.id})
    )
    previous_fingerprint = ssh_key.fingerprint
    ssh_key.key = rsa_key()
    ssh_key.save()
    ssh_key.refresh_from_db()
    assert ssh_key.fingerprint != previous_fingerprint


def test_calculate_fingerprint():
    assert calculate_fingerprint(key_data) == fingerprint


def test_new_ssh_key_get(client, user):
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
    # special form in which we reuse the key of an existing key to
    # force a duplicate key warning
    ('duplicate', 'There is already a SSH key with the fingerprint'),
])
def test_new_ssh_key_post_errors(client, user, ssh_key, key, exception):
    # special case in which we force a duplicate key validation error
    if key == 'duplicate':
        key = ssh_key.key
    new_data = {
        'sshkey-title': 'A title',
        'sshkey-key': key,
    }
    response = client.post(reverse('keys-new'), new_data, follow=True)
    assert not SSHKey.objects.filter(title='A title').exists()
    assert response.status_code == 200
    assert response.context['form'].errors
    assert exception in response.context['form'].errors['key'][0]


def test_new_ssh_key_post_success(client, messages, user):
    new_data = {
        'sshkey-title': 'A title',
        'sshkey-key': key_data,
    }
    response = client.post(reverse('keys-new'), new_data, follow=True)
    ssh_key = SSHKey.objects.get(title='A title')
    assert response.status_code == 200
    assert response.redirect_chain[-1] == (reverse('keys-list'), 302)
    assert ssh_key in response.context['ssh_keys']
    messages.assert_message_contains(response, 'successfully added')


def test_delete_key(client, messages, ssh_key, user, user2):
    response = client.get(ssh_key.urls.delete)
    assert response.status_code == 200

    # login the second user so we can check the delete_sshkey permission
    client.force_login(user2)
    response = client.get(ssh_key.urls.delete)
    assert response.status_code == 403
    client.force_login(user)

    response = client.post(ssh_key.urls.delete, follow=True)
    assert response.status_code == 200
    assert response.redirect_chain[-1], (reverse('keys-list') == 302)
    messages.assert_message_contains(response, 'successfully deleted')
    assert not SSHKey.objects.filter(id=ssh_key.id).exists()


def test_view_key(client, ssh_key):
    response = client.get(ssh_key.urls.detail, follow=True)
    assert response.status_code == 200


def test_view_raw_key(client, ssh_key):
    response = client.get(ssh_key.urls.raw, follow=True)
    assert response.status_code == 200
    assert not response.context
    assert 'text/plain' in response['content-type']


def test_list_keys(client, ssh_key, user2):
    list_url = reverse('keys-list')
    response = client.get(list_url, follow=True)
    assert response.status_code == 200
    assert 'ssh_keys' in response.context
    assert ssh_key in response.context['ssh_keys']

    # login the second user so we can check the view_sshkey permission
    client.force_login(user2)
    response = client.get(list_url, follow=True)
    assert response.status_code == 200
    assert 'ssh_keys' in response.context
    assert ssh_key not in response.context['ssh_keys']
