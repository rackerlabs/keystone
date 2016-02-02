# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""S3 Credential Controllers.

If the backend code cannot be loaded, all APIs fronted by this service will
simply raise an HTTP 403. This is to solve legal concerns for some deployments
when using OpenStack and the AWS compatibility APIs.
"""

import extras

from keystone import compat


_s3_core = extras.try_import('keystone.compat.aws.s3._s3_core')
_ec2_core = extras.try_import('keystone.compat.aws.ec2._ec2_core')


# NOTE(morganfainberg): This is to support the case where for legal reasons
# S3 compat core cannot be installed on the disk. This pattern should
# never be replicated outside of the keystone.compat tree. Both EC2 and S3
# need to be available for S3 to work.
if _ec2_core and _s3_core:
    S3Controller = _s3_core.S3Controller
else:
    S3Controller = compat._AllMethodsForbiddenControllerV2
