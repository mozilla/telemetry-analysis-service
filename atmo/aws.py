# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
import boto3
from django.conf import settings

emr = boto3.client('emr', region_name=settings.AWS_CONFIG['AWS_REGION'])
s3 = boto3.client('s3', region_name=settings.AWS_CONFIG['AWS_REGION'])
