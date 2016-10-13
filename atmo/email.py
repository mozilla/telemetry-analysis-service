from django.conf import settings
import boto3

ses = boto3.client("ses", region_name=settings.AWS_CONFIG['AWS_REGION'])


def send_email(email_address, subject, body):
    return ses.send_email(
        Source=settings.AWS_CONFIG['EMAIL_SOURCE'],
        Destination={'ToAddresses': [email_address]},
        Message={
            'Subject': {'Data': subject, 'Charset': 'UTF-8'},
            'Body': {'Text': {'Data': body, 'Charset': 'UTF-8'}}
        }
    )['MessageId']
