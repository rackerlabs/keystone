import uuid

from keystone.common import dependency
from keystone.common import manager
from keystone.common import logging
from keystone import config
from keystone import exception

CONF = config.CONF
LOG = logging.getLogger(__name__)


@dependency.provider('mapping_api')
class Manager(manager.Manager):

    def __init__(self):
        super(Manager, self).__init__(CONF.mapping.driver)


class Driver(object):

    # Organisational
    #Sets

    def create_org_attribute_set(self, org_attribute_set_id,
                                 org_attribute_set_ref):
        raise exception.NotImplemented()

    def get_org_attribute_set(self, set_id):
        raise exception.NotImplemented()

    def list_org_attribute_sets(self):
        raise exception.NotImplemented()

    def delete_org_attribute_set(self, set_id):
        raise exception.NotImplemented()

    # Attributes

    def create_org_attribute(self, org_att_id, org_att_ref):
        raise exception.NotImplemented()

    def get_org_attribute(self, attribute_id):
        raise exception.NotImplemented()

    def list_org_attributes(self):
        raise exception.NotImplemented()

    def delete_org_attribute(self, attribute_id):
        raise exception.NotImplemented()

    def add_attribute_to_org_set(self, org_attribute_set_id, attribute_id):
        raise exception.NotImplemented()

    def remove_attribute_from_org_set(self, org_attribute_set_id,
                                      attribute_id):
        raise exception.NotImplemented()

    def check_attribute_in_org_set(self, org_attribute_set_id, attribute_id):
        raise exception.NotImplemented()

    def list_attributes_in_org_set(self, org_attribute_set_id):
        raise exception.NotImplemented()

    def list_org_sets_containing_attribute(self, org_attribute_id):
        raise exception.NotImplemented()

    # Openstack
    #Sets

    def create_os_attribute_set(self, os_attribute_set_ref):
        raise exception.NotImplemented()

    def get_os_attribute_set(self, os_attribute_set_id):
        raise exception.NotImplemented()

    def list_os_attribute_sets(self):
        raise exception.NotImplemented()

    def delete_os_attribute_set(self, os_attribute_set_id):
        raise exception.NotImplemented()

    def add_attribute_to_os_set(self, os_attribute_set_id, attribute_id, type):
        raise exception.NotImplemented()

    def remove_attribute_from_os_set(self, os_attribute_set_id,
                                     attribute_id, type):
        raise exception.NotImplemented()

    def check_attribute_in_os_set(self, os_attribute_set_id,
                                  attribute_id, type):
        raise exception.NotImplemented()

    def list_attributes_in_os_set(self, os_attribute_set_id):
        raise exception.NotImplemented()

    def list_os_sets_containing_attribute(self, os_attribute_id, type):
        raise exception.NotImplemented()

    # Attribute Mapping

    def create_attribute_set_mapping(self, mapping_ref):
        raise exception.NotImplemented()

    def get_attribute_set_mapping(self, mapping_id):
        raise exception.NotImplemented()

    def delete_attribute_set_mapping(self, mapping_id):
        raise exception.NotImplemented()

    def list_attribute_set_mappings(self, org_attribute_set_id=None,
                                    os_attribute_set_id=None):
        raise exception.NotImplemented()
