import uuid

from keystone.common import wsgi
from keystone.common import manager
from keystone.common import logging
from keystone import config
from keystone import exception

CONF = config.CONF
LOG = logging.getLogger(__name__)


class Manager(manager.Manager):

    def __init__(self):
        super(Manager, self).__init__(CONF.mapping.driver)
    # Sets

    def create_os_attribute_set(self, context, set_ref):
        return self.driver.create_os_attribute_set(context, set_ref)

    def get_os_attribute_set(self, context, set_id):
        return self.driver.get_os_attribute_set(set_id)

    def list_os_attribute_sets(self):
        return self.driver.list_os_attribute_sets()

    def delete_os_attribute_set(self, set_id):
        LOG.debug("Start of delete os set in Manager")
        self.driver.delete_os_attribute_set(set_id)

    # Associations

    def create_os_attribute_association(self, context, assoc_ref):
        return self.driver.create_os_attribute_association(context, assoc_ref)

    def get_os_attribute_association(self, context, assoc_id):
        return self.driver.get_os_attribute_association(assoc_id)

    def list_os_attribute_associations(self):
        return self.driver.list_os_attribute_associations()

    def delete_os_attribute_association(self, assoc_id):
        LOG.debug("Start of del os assoc")
        self.driver.delete_os_attribute_association(assoc_id)

    def __init__(self):
        super(Manager, self).__init__(CONF.mapping.driver)

    # Sets

    def create_org_attribute_set(self, context, set_ref):
        return self.driver.create_org_attribute_set(
            context, set_ref)

    def get_org_attribute_set(self, context, set_id):
        return self.driver.get_org_attribute_set(set_id)

    def list_org_attribute_sets(self):
        return self.driver.list_org_attribute_sets()

    def delete_org_attribute_set(self, set_id):
        self.driver.delete_org_attribute_set(set_id)

    # Attributes

    def create_org_attribute(self, context, attribute_ref):
        return self.driver.create_org_attribute(
            context, attribute_ref)

    def get_org_attribute(self, context, attribute_id):
        return self.driver.get_org_attribute(attribute_id)

    def list_org_attributes(self):
        return self.driver.list_org_attributes()

    def delete_org_attribute(self, attribute_id):
        self.driver.delete_org_attribute(attribute_id)

    # Associations

    def create_org_attribute_association(self, context, assoc_ref):
        return self.driver.create_org_attribute_association(
            context, assoc_ref)

    def get_org_attribute_association(self, context, assoc_id):
        return self.driver.get_org_attribute_association(assoc_id)

    def list_org_attribute_associations(self):
        return self.driver.list_org_attribute_associations()

    def delete_org_attribute_association(self, assoc_id):
        self.driver.delete_org_attribute_association(assoc_id)

    # Mappings

    def create_mapping(self, context, mapping_ref):
        return self.driver.create_mapping(context, mapping_ref)

    def get_mapping(self, context, mapping_id):
        return self.driver.get_mapping(mapping_id)

    def list_mappings(self):
        return self.driver.list_mappings()

    def delete_mapping(self, mapping_id):
        self.driver.delete_mapping(mapping_id)

    def get_mappings_from_attributes(self, context, attributes):
        return self.driver.get_mappings_from_attributes(attributes)


class Driver(object):

    def __init__(self):
        super(Mapping)

    # Organisational
    #Sets

    def create_org_attribute_set(self, org_attribute_set_id,
                                 org_attribute_set_ref):
        raise exception.NotImplemented()

    def get_org_attribute_set(self, set_id):
        raise exception.NotImplemented()

    def _get_org_attribute_set(self, session, set_id):
        raise exception.NotImplemented()

    def list_org_attribute_sets(self):
        raise exception.NotImplemented()

    def delete_org_attribute_set(self, set_id):
        raise exception.NotImplemented()

    # Attributes

    def create_org_attribute(self, context, org_att_id, org_att_ref):
        raise exception.NotImplemented()

    def get_org_attribute(self, attribute_id):
        raise exception.NotImplemented()

    def _get_org_attribute(self, session, attribute_id):
        raise exception.NotImplemented()

    def list_org_attributes(self):
        raise exception.NotImplemented()

    def delete_org_attribute(self, attribute_id):
        raise exception.NotImplemented()

    # Associations

    def create_org_attribute_association(self, context,
                                         org_attribute_association_id,
                                         org_attribute_association_ref):
        raise exception.NotImplemented()

    def get_org_attribute_association(self, org_attribute_association_id):
        raise exception.NotImplemented()

    def _get_org_attribute_association(self, session,
                                       org_attribute_association_id):
        raise exception.NotImplemented()

    def list_org_attribute_associations(self):
        raise exception.NotImplemented()

    def delete_org_attribute_association(self, org_attribute_association_id):
        raise exception.NotImplemented()

    # Openstack
    #Sets

    def create_os_attribute_set(self, context, os_attribute_set_ref):
        raise exception.NotImplemented()

    def get_os_attribute_set(self, os_attribute_set_id):
        raise exception.NotImplemented()

    def _get_os_attribute_set(self, session, os_attribute_set_id):
        raise exception.NotImplemented()

    def list_os_attribute_sets(self):
        raise exception.NotImplemented()

    def delete_os_attribute_set(self, os_attribute_set_id):
        raise exception.NotImplemented()

    # Associations

    def create_os_attribute_association(self, context,
                                        os_attribute_association_ref):
        raise exception.NotImplemented()

    def get_os_attribute_association(self, os_attribute_association_id):
        raise exception.NotImplemented()

    def _get_os_attribute_association(self, session,
                                      os_attribute_association_id):
        raise exception.NotImplemented()

    def list_os_attribute_associations(self):
        raise exception.NotImplemented()

    def delete_os_attribute_association(self, os_attribute_association_id):
        raise exception.NotImplemented()

    # Attribute Mapping

    def create_mapping(self, context, mapping_ref):
        raise exception.NotImplemented()

    def get_mapping(self, mapping_id):
        raise exception.NotImplemented()

    def _get_mapping(self, session, mapping_id):
        raise exception.NotImplemented()

    def delete_mapping(self, mapping_id):
        raise exception.NotImplemented()

    def list_mappings(self):
        raise exception.NotImplemented()
