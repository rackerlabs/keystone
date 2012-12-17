import uuid

from keystone.common import wsgi
from keystone.common import manager
from keystone.common import logging
from keystone import config
from keystone.mapping.core import Manager

CONF = config.CONF
LOG = logging.getLogger(__name__)


class AttributeMappingController(wsgi.Application):
    def __init__(self):
        self.mapping_api = Manager()
        super(AttributeMappingController)
    # Sets

    def get_mapping(self, context, mapping_id):
        mapping = self.mapping_api.get_mapping(context, mapping_id)
        return {'attribute_mapping': mapping}

    def list_mappings(self, context):
        return {'attribute_mappings': self.mapping_api.list_mappings()}

    def delete_mapping(self, context, mapping_id):
        self.mapping_api.delete_mapping(mapping_id)

    def create_mapping(self, context, attribute_mapping):
        self.assert_admin(context)
        mapping_id = uuid.uuid4().hex
        mapping_ref = attribute_mapping.copy()
        mapping_ref['id'] = mapping_id
        new_mapping_ref = self.mapping_api.create_mapping(
            context, mapping_ref)
        return {'attribute_mapping': new_mapping_ref}

    def get_mappings_from_attributes(self, context, attributes):
        mappings = self.mapping_api.list_mappings()
        matches = []
        for m in mappings:
            LOG.debug(m)
            cur_set = {}
            for org in m['org_attribute_set']['attributes']:
                cur_set[org['type']] = org['value']
            for k, v in cur_set.iteritems():
                set_matched = True
                LOG.debug(k)
                matched = False
                for k2, v2 in attributes.iteritems():
                    if k2 == k and v in v2:
                        matched = True
                        break    # break out if we matched an attribute
                if not matched:
                    set_matched = False

            if set_matched:
                tenants = []
                roles = []
                # How do we do domains??
                for os in m['os_attribute_set']['attributes']:
                    if os['type'] in "tenant":
                        tenants.append(os)
                    if os['type'] in "role":
                        roles.append(os)
                matched_sets = {"roles": roles, "tenants": tenants}
                matches.append({"matched_set": matched_sets})

        return {'mapped_attributes': matches}


class OrgMappingController(wsgi.Application):

    def __init__(self):
        self.mapping_api = Manager()
        super(OrgMappingController)

    # Sets

    def list_org_attribute_sets(self, context):
        return {'org_attribute_sets':
                self.mapping_api.list_org_attribute_sets()}

    def get_org_attribute_set(self, context, org_attribute_set_id):
        org_set = self.mapping_api.get_org_attribute_set(context,
                                                         org_attribute_set_id)
        return {'org_attribute_set': org_set}

    def delete_org_attribute_set(self, context, org_attribute_set_id):
        self.mapping_api.delete_org_attribute_set(org_attribute_set_id)

    def create_org_attribute_set(self, context, org_attribute_set):
        LOG.debug("Creating set: " + str(org_attribute_set))
        self.assert_admin(context)
        set_id = uuid.uuid4().hex
        set_ref = org_attribute_set.copy()
        set_ref['id'] = set_id
        new_set_ref = self.mapping_api.create_org_attribute_set(
            context, set_ref)
        return {'org_attribute_set': new_set_ref}

    # Attributes

    def get_org_attribute(self, context, org_attribute_id=None):
        att = self.mapping_api.get_org_attribute(context, org_attribute_id)
        return {'org_attribute': att}

    def list_org_attributes(self, context):
        atts = self.mapping_api.list_org_attributes()
        return {'org_attributes': atts}

    def delete_org_attribute(self, context, org_attribute_id):
        self.mapping_api.delete_org_attribute(org_attribute_id)

    def create_org_attribute(self, context, org_attribute):
        self.assert_admin(context)
        attribute_id = uuid.uuid4().hex
        attribute_ref = org_attribute.copy()
        attribute_ref['id'] = attribute_id
        new_attribute_ref = self.mapping_api.create_org_attribute(
            context, attribute_ref)
        return {'org_attribute': new_attribute_ref}

    # Associations

    def get_org_attribute_association(self, context,
                                      org_attribute_association_id=None):
        assoc_id = org_attribute_association_id
        assoc = self.mapping_api.get_org_attribute_association(context,
                                                               assoc_id)
        return {'org_attribute_association': assoc}

    def list_org_attribute_associations(self, context):
        assocs = self.mapping_api.list_org_attribute_associations()
        return {'org_attribute_associations': assocs}

    def delete_org_attribute_association(self, context,
                                         org_attribute_association_id):
        assoc_id = org_attribute_association_id
        self.mapping_api.delete_org_attribute_association(assoc_id)

    def create_org_attribute_association(self, context,
                                         org_attribute_association):
        self.assert_admin(context)
        assoc_id = uuid.uuid4().hex
        assoc_ref = org_attribute_association.copy()
        assoc_ref['id'] = assoc_id
        new_assoc_ref = self.mapping_api.create_org_attribute_association(
            context, assoc_ref)
        return {'org_attribute_association': new_assoc_ref}


class OsMappingController(wsgi.Application):

    def __init__(self):
        self.mapping_api = Manager()
        super(OsMappingController)

    # Sets

    def get_os_attribute_set(self, context, os_attribute_set_id=None):
        if os_attribute_set_id:
            os_set = self.mapping_api.get_os_attribute_set(context,
                                                           os_attribute_set_id)
            return {'os_attribute_set': os_set}

    def list_os_attribute_sets(self, context):
        return {'os_attribute_sets': self.mapping_api.list_os_attribute_sets()}

    def delete_os_attribute_set(self, context, os_attribute_set_id):
        LOG.debug("Start of controller os set delete")
        self.mapping_api.delete_os_attribute_set(os_attribute_set_id)

    def create_os_attribute_set(self, context, os_attribute_set):
        self.assert_admin(context)
        set_id = uuid.uuid4().hex
        set_ref = os_attribute_set.copy()
        set_ref['id'] = set_id
        new_set_ref = self.mapping_api.create_os_attribute_set(context,
                                                               set_ref)
        return {'os_attribute_set': new_set_ref}

    # Associations

    def get_os_attribute_association(self, context,
                                     os_attribute_association_id=None):
        assoc_id = os_attribute_association_id
        assoc = self.mapping_api.get_os_attribute_association(context,
                                                              assoc_id)
        return {'os_attribute_association': assoc}

    def list_os_attribute_associations(self, context):
        assocs = self.mapping_api.list_os_attribute_associations()
        return {'os_attribute_associations': assocs}

    def delete_os_attribute_association(self, context,
                                        os_attribute_association_id):
        self.mapping_api.delete_os_attribute_association(
            os_attribute_association_id)

    def create_os_attribute_association(self, context,
                                        os_attribute_association):
        self.assert_admin(context)
        assoc_id = uuid.uuid4().hex
        assoc_ref = os_attribute_association.copy()
        assoc_ref['id'] = assoc_id
        new_assoc_ref = self.mapping_api.create_os_attribute_association(
            context, assoc_ref)
        return {'os_attribute_association': new_assoc_ref}
