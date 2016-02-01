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

from keystone.common import controller
from keystone import exception


class _Common403RaisingController(object):
    """A base controller that simply raises HTTP 403 for any call.

    This controller is used when a compat controller is not importable and will
    cause all of the registered routes to raise an HTTP 403. This is done by
    using the __getattr__ method to raise forbidden as the "real" method
    will not be defined.
    """

    def __getattr__(self, item):
        return self.RaiseHTTP403

    def RaiseHTTP403(self, *args, **kwargs):
        """Always Raise HTTP 403 Forbidden."""
        raise exception.Forbidden()


class _AllMethodsForbiddenControllerV2(_Common403RaisingController,
                                       controller.V2Controller):
    """A controller than will simply raise HTTP 403 for any call."""


class _AllMethodsForbiddenControllerV3(_Common403RaisingController,
                                       controller.V3Controller):
    """A controller than will simply raise HTTP 403 for any call."""
