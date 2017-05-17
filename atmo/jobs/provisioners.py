# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from collections import OrderedDict

from ..provisioners import Provisioner


class SparkJobProvisioner(Provisioner):
    log_dir = 'jobs'
    name_component = 'job'

    def __init__(self):
        super().__init__()
        # the S3 URI to the job shell script
        self.batch_uri = 's3://%s/steps/batch.sh' % self.config['SPARK_EMR_BUCKET']

    def add(self, identifier, notebook_file):
        """
        Upload the notebook file to S3
        """
        key = 'jobs/%s/%s' % (identifier, notebook_file.name)
        self.s3.put_object(
            Bucket=self.config['CODE_BUCKET'],
            Key=key,
            Body=notebook_file
        )
        return key

    def get(self, key):
        return self.s3.get_object(Bucket=self.config['CODE_BUCKET'], Key=key)

    def remove(self, key):
        self.s3.delete_object(Bucket=self.config['CODE_BUCKET'], Key=key)

    def run(self, user_username, user_email, identifier, emr_release, size,
            notebook_key, is_public, job_timeout):

        # first get the common job flow parameters
        job_flow_params = self.job_flow_params(
            user_username=user_username,
            user_email=user_email,
            identifier=identifier,
            emr_release=emr_release,
            size=size,
        )

        # the S3 URI to the Jupyter notebook file
        notebook_uri = 's3://%s/%s' % (self.config['CODE_BUCKET'], notebook_key)

        if is_public:
            data_bucket = self.config['PUBLIC_DATA_BUCKET']
        else:
            data_bucket = self.config['PRIVATE_DATA_BUCKET']

        job_flow_params.update({
            'BootstrapActions': [{
                'Name': 'setup-telemetry-spark-job',
                'ScriptBootstrapAction': {
                    'Path': self.script_uri,
                    'Args': [
                        '--timeout', str(job_timeout * 60),
                    ]
                }
            }],
            'Steps': [{
                'Name': 'RunNotebookStep',
                'ActionOnFailure': 'TERMINATE_JOB_FLOW',
                'HadoopJarStep': {
                    'Jar': self.jar_uri,
                    'Args': [
                        self.batch_uri,
                        '--job-name', identifier,
                        '--notebook', notebook_uri,
                        '--data-bucket', data_bucket
                    ]
                }
            }],
        })

        cluster = self.emr.run_job_flow(**job_flow_params)
        return cluster['JobFlowId']

    def results(self, identifier, is_public):
        if is_public:
            bucket = self.config['PUBLIC_DATA_BUCKET']
        else:
            bucket = self.config['PRIVATE_DATA_BUCKET']

        params = {
            'Prefix': '%s/' % identifier,
            'Bucket': bucket,
        }

        results = OrderedDict()
        list_objects_v2_paginator = self.s3.get_paginator('list_objects_v2')
        for page in list_objects_v2_paginator.paginate(**params):
            for item in page.get('Contents', []):
                try:
                    prefix = item['Key'].split('/')[1]
                except IndexError:
                    continue
                results.setdefault(prefix, []).append(item['Key'])
        return results
