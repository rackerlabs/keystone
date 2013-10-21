# vim: tabstop=4 shiftwidth=4 softtabstop=4

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


from keystone.openstack.common import gettextutils

from six import moves


# NOTE(dstanek):
#  We must first setup the gettext framework by calling install.  This will
#  add our '_' function to the __builtins__ by way to the six library.  We
#  steam a reference to it so that we can make '_' importable from this
#  module.
gettextutils.install('keystone', lazy=True)
_ = moves.builtins.__dict__['_']
