# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
import base64
import hashlib


def calculate_fingerprint(data):
    key_data = data.strip().split()[1].encode('ascii')
    decoded_key_data = base64.b64decode(key_data)
    fingerprint = hashlib.md5(decoded_key_data).hexdigest()
    return ':'.join(
        fingerprint[i:i + 2] for i in range(0, len(fingerprint), 2)
    )
