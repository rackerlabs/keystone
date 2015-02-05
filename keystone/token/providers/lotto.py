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

"""Keystone Lotto Token Provider"""

from __future__ import absolute_import

import random

from keystone import config

from keystone.token.providers import common

CONF = config.CONF


class Provider(common.BaseProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)

    def _powerball_token(self, token_data):
        white_balls = range(1,59)
        random.shuffle(white_balls)
        fragment1 = "-".join(str(x) for x in white_balls[:5])
        power_ball = random.randint(1,35)
        fragment2 = "-PB:%d" % power_ball
        return fragment1+fragment2

    def _get_token_id(self, token_data):
        return self._powerball_token(token_data)
