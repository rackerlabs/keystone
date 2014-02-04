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

from keystone.common import utils
from keystone.openstack.common import jsonutils


class KeystoneRenderer(object):
    """Fake rendering everything to json.

    Traditionally keystone renders everything to JSON and then leaves the
    conversion to XML or other type to middleware. To maintain compatability
    this renderer will encode everything that is pointed at it to json.
    """

    def __init__(self, path, extra_vars):
        pass

    def render(self, template_path, namespace):
        return jsonutils.dumps(namespace, cls=utils.SmarterEncoder)
