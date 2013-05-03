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
# under the License.

from keystone.common import kvs
from keystone.common import logging


LOG = logging.getLogger(__name__)


class DelegatedAuth(kvs.Base):
    def get_consumer(self, consumer_id):
        consumer_ref = self.db.get('consumer-%s' % consumer_id)
        return consumer_ref

    def create_consumer(self, consumer_id, consumer):
        self.db.set('consumer-%s' % consumer_id, consumer)
        consumer_list = set(self.db.get('consumer_list', []))
        consumer_list.add(consumer_id)
        self.db.set('consumer_list', list(consumer_list))
        return consumer

    def delete_consumer(self, consumer_id):
        self.db.get('consumer-%s' % consumer_id)
        self.db.delete('consumer-%s' % consumer_id)
        consumer_list = set(self.db.get('consumer_list', []))
        consumer_list.remove(consumer_id)
        self.db.set('consumer_list', list(consumer_list))
        return None

    def list_consumers(self):
        consumer_ids = self.db.get('consumer_list', [])
        return [self.get_consumer(x) for x in consumer_ids]

    def update_consumer(self, consumer_id, consumer):
        self.db.get('consumer-%s' % consumer_id)
        self.db.set('consumer-%s' % consumer_id, consumer)
        return consumer
