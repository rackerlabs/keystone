# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
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
# under the License.from keystone import catalog


"""
    To avoid circular dependencies, the imports for the domain modules
    are not processed when this file is initially imported.
"""


def get_apis():
    #TODO make this static
    module_dict = None

    if not module_dict:
        from keystone import catalog
        from keystone import identity
        from keystone import policy
        from keystone import token

        module_dict = dict(catalog_api=catalog.Manager(),
                           identity_api=identity.Manager(),
                           policy_api=policy.Manager(),
                           token_api=token.Manager())
    return module_dict
