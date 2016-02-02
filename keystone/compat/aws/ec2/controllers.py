# Copyright 2013 OpenStack Foundation
#
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

"""EC2 Credential Service Controllers."""

import extras

from keystone import compat


_ec2_core = extras.try_import('keystone.compat.aws.ec2._ec2_core')


# NOTE(morganfainberg): This is to support the case where for legal reasons
# EC2 compat core cannot be installed on the disk. This pattern should
# never be replicated outside of the keystone.compat tree.
if _ec2_core:
    Ec2Controller = _ec2_core.Ec2Controller
    Ec2ControllerV3 = _ec2_core.Ec2ControllerV3
    # Make sure we've provided the proper CRED_TYPE so they can be referenced.
    CRED_TYPE_EC2 = _ec2_core.CRED_TYPE_EC2
else:
    Ec2Controller = compat._AllMethodsForbiddenControllerV2
    Ec2ControllerV3 = compat._AllMethodsForbiddenControllerV2
    # CRED_TYPE doesn't matter now because we're not using EC2.
    CRED_TYPE_EC2 = None
