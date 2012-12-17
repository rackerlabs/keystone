import uuid

import test_v3


class MappingTestCase(test_v3.RestfulTestCase):
    """Test mapping CRUD"""

    def setUp(self):
        super(MappingTestCase, self).setUp()
        self.org_attribute_set_id = uuid.uuid4().hex
        self.org_attribute_set = self.new_org_attribute_set_ref()
        self.org_attribute_set['id'] = self.org_attribute_set_id
        self.mapping_api.create_org_attribute_set(
            self.org_attribute_set_id,
            self.org_attribute_set.copy())

        self.os_attribute_set_id = uuid.uuid4().hex
        self.os_attribute_set = self.new_os_attribute_set_ref()
        self.os_attribute_set['id'] = self.os_attribute_set_id
        self.mapping_api.create_os_attribute_set(
            self.os_attribute_set_id,
            self.os_attribute_set.copy())

        self.org_attribute_id = uuid.uuid4().hex
        self.org_attribute = self.new_org_attribute_ref()
        self.org_attribute['id'] = self.org_attribute_id
        self.mapping_api.create_org_attribute(
            self.org_attribute_id,
            self.org_attribute.copy())

        self.role_id = uuid.uuid4().hex
        self.role = self.new_role_ref()
        self.role['id'] = self.role_id
        self.identity_api.create_role(
            self.role_id,
            self.role.copy())

        self.org_attribute_assoc_id = uuid.uuid4().hex
        ref = self.new_org_attribute_association_ref()
        self.org_attribute_association = ref
        self.org_attribute_association['id'] = self.org_attribute_assoc_id
        att_id = self.org_attribute_id
        self.org_attribute_association['org_attribute_id'] = att_id
        set_id = self.org_attribute_set_id
        self.org_attribute_association['org_attribute_set_id'] = set_id
        self.mapping_api.create_org_attribute_association(
            self.org_attribute_assoc_id,
            self.org_attribute_association.copy())

        self.os_attribute_association_id = uuid.uuid4().hex
        self.os_attribute_association = self.new_os_attribute_association_ref()
        self.os_attribute_association['id'] = self.os_attribute_association_id
        self.os_attribute_association['attribute_id'] = self.role_id
        set_id = self.os_attribute_set_id
        self.os_attribute_association['os_attribute_set_id'] = set_id
        self.os_attribute_association['type'] = 'role'
        self.mapping_api.create_os_attribute_association(
            self.os_attribute_association_id,
            self.os_attribute_association.copy())

        self.attribute_mapping_id = uuid.uuid4().hex
        self.attribute_mapping = self.new_attribute_mapping_ref()
        self.attribute_mapping['id'] = self.attribute_mapping_id
        os_set = self.os_attribute_set_id
        org_set = self.org_attribute_set_id
        self.attribute_mapping['org_attribute_set_id'] = org_set
        self.attribute_mapping['os_attribute_set_id'] = os_set
        self.mapping_api.create_mapping(
            self.attribute_mapping_id,
            self.attribute_mapping.copy())

    # Org Attribute set validation

    def assertValidOrgAttributeSetListResponse(self, resp, ref):
        return self.assertValidListResponse(
            resp,
            'org_attribute_sets',
            self.assertValidOrgAttributeSet,
            ref)

    def assertValidOrgAttributeSetResponse(self, resp, ref):
        return self.assertValidResponse(
            resp,
            'org_attribute_set',
            self.assertValidOrgAttributeSet,
            ref)

    def assertValidOrgAttributeSet(self, entity, ref=None):
        self.assertIsNotNone(entity.get('name'))
        if ref:
            self.assertEqual(ref['name'], entity['name'])
        return entity

    def test_create_org_attribute_set(self):
        """POST /org_attribute_sets"""
        ref = self.new_org_attribute_set_ref()
        r = self.post(
            '/org_attribute_sets',
            body={'org_attribute_set': ref})
        return self.assertValidOrgAttributeSetResponse(r, ref)

    def test_list_org_attribute_sets(self):
        """GET /org_attribute_sets"""
        r = self.get('/org_attribute_sets')
        self.assertValidOrgAttributeSetListResponse(r, self.org_attribute_set)

    def test_get_org_attribute_set(self):
        """GET /org_attribute_sets/{org_attribute_set_id}"""
        r = self.get('/org_attribute_sets/%(set_id)s' % {
            'set_id': self.org_attribute_set_id})
        self.assertValidOrgAttributeSetResponse(r, self.org_attribute_set)

    def test_delete_org_attribute_set(self):
        """DELETE /org_attribute_sets/{org_attribute_set_id}"""
        self.delete('/org_attribute_sets/%(set_id)s' % {
            'set_id': self.org_attribute_set_id})

    # Os Attribute Set validation

    def assertValidOsAttributeSetListResponse(self, resp, ref):
        return self.assertValidListResponse(
            resp,
            'os_attribute_sets',
            self.assertValidOsAttributeSet,
            ref)

    def assertValidOsAttributeSetResponse(self, resp, ref):
        return self.assertValidResponse(
            resp,
            'os_attribute_set',
            self.assertValidOsAttributeSet,
            ref)

    def assertValidOsAttributeSet(self, entity, ref=None):
        self.assertIsNotNone(entity.get('name'))
        if ref:
            self.assertEqual(ref['name'], entity['name'])
        return entity

    def test_create_os_attribute_set(self):
        """POST /os_attribute_sets"""
        ref = self.new_os_attribute_set_ref()
        r = self.post(
            '/os_attribute_sets',
            body={'os_attribute_set': ref})
        return self.assertValidOsAttributeSetResponse(r, ref)

    def test_list_os_attribute_sets(self):
        """GET /os_attribute_sets"""
        r = self.get('/os_attribute_sets')
        self.assertValidOsAttributeSetListResponse(r, self.os_attribute_set)

    def test_get_os_attribute_set(self):
        """GET /os_attribute_sets/{os_attribute_set_id}"""
        r = self.get('/os_attribute_sets/%(set_id)s' % {
            'set_id': self.os_attribute_set_id})
        self.assertValidOsAttributeSetResponse(r, self.os_attribute_set)

    def test_delete_os_attribute_set(self):
        """DELETE /os_attribute_sets/{os_attribute_set_id}"""
        self.delete('/os_attribute_sets/%(set_id)s' % {
            'set_id': self.os_attribute_set_id})

    # Org Attribute validation

    def assertValidOrgAttributeListResponse(self, resp, ref):
        return self.assertValidListResponse(
            resp,
            'org_attributes',
            self.assertValidOrgAttribute,
            ref)

    def assertValidOrgAttributeResponse(self, resp, ref):
        return self.assertValidResponse(
            resp,
            'org_attribute',
            self.assertValidOrgAttribute,
            ref)

    def assertValidOrgAttribute(self, entity, ref=None):
        self.assertIsNotNone(entity.get('name'))
        if ref:
            self.assertEqual(ref['name'], entity['name'])
        return entity

    def test_create_org_attribute(self):
        """POST /org_attributes"""
        ref = self.new_org_attribute_ref()
        r = self.post(
            '/org_attributes',
            body={'org_attribute': ref})
        return self.assertValidOrgAttributeResponse(r, ref)

    def test_list_org_attributes(self):
        """GET /org_attributes"""
        r = self.get('/org_attributes')
        self.assertValidOrgAttributeListResponse(r, self.org_attribute)

    def test_get_org_attribute(self):
        """GET /org_attributes/{org_attribute_id}"""
        r = self.get('/org_attributes/%(set_id)s' % {
            'set_id': self.org_attribute_id})
        self.assertValidOrgAttributeResponse(r, self.org_attribute)

    def test_delete_org_attribute(self):
        """DELETE /org_attributes/{org_attribute_id}"""
        self.delete('/org_attributes/%(set_id)s' % {
            'set_id': self.org_attribute_id})

    # org attribute association validation

    def assertValidOrgAttributeAssociationListResponse(self, resp, ref):
        return self.assertValidListResponse(
            resp,
            'org_attribute_associations',
            self.assertValidOrgAttributeAssociation,
            ref)

    def assertValidOrgAttributeAssociationResponse(self, resp, ref):
        return self.assertValidResponse(
            resp,
            'org_attribute_association',
            self.assertValidOrgAttributeAssociation,
            ref)

    def assertValidOrgAttributeAssociation(self, entity, ref=None):
        self.assertIsNotNone(entity.get('name'))
        if ref:
            self.assertEqual(ref['name'], entity['name'])
        return entity

    def test_create_org_attribute_association(self):
        """POST /org_attribute_associations"""
        ref = self.new_org_attribute_association_ref()
        r = self.post(
            '/org_attribute_associations',
            body={'org_attribute_association': ref})
        return self.assertValidOrgAttributeAssociationResponse(r, ref)

    def test_list_org_attribute_associations(self):
        """GET /org_attribute_associations"""
        r = self.get('/org_attribute_associations')
        oaa = self.org_attribute_association
        self.assertValidOrgAttributeAssociationListResponse(r, oaa)

    def test_get_org_attribute_association(self):
        """GET /org_attribute_associations/{org_attribute_association_id}"""
        r = self.get('/org_attribute_associations/%(set_id)s' % {
            'set_id': self.org_attribute_assoc_id})
        oaa = self.org_attribute_association
        self.assertValidOrgAttributeAssociationResponse(r, oaa)

    def test_delete_org_attribute_association(self):
        """DELETE /org_attribute_associations/{org_attribute_association_id}"""
        self.delete('/org_attribute_associations/%(set_id)s' % {
            'set_id': self.org_attribute_assoc_id})

    # os attribute association validation

    def assertValidOsAttributeAssociationListResponse(self, resp, ref):
        return self.assertValidListResponse(
            resp,
            'os_attribute_associations',
            self.assertValidOsAttributeAssociation,
            ref)

    def assertValidOsAttributeAssociationResponse(self, resp, ref):
        return self.assertValidResponse(
            resp,
            'os_attribute_association',
            self.assertValidOsAttributeAssociation,
            ref)

    def assertValidOsAttributeAssociation(self, entity, ref=None):
        self.assertIsNotNone(entity.get('name'))
        if ref:
            self.assertEqual(ref['name'], entity['name'])
        return entity

    def test_create_os_attribute_association(self):
        """POST /os_attribute_associations"""
        ref = self.new_os_attribute_association_ref()
        r = self.post(
            '/os_attribute_associations',
            body={'os_attribute_association': ref})
        return self.assertValidOsAttributeAssociationResponse(r, ref)

    def test_list_os_attribute_associations(self):
        """GET /os_attribute_associations"""
        r = self.get('/os_attribute_associations')
        oaa = self.os_attribute_association
        self.assertValidOsAttributeAssociationListResponse(r, oaa)

    def test_get_os_attribute_association(self):
        """GET /os_attribute_associations/{os_attribute_association_id}"""
        r = self.get('/os_attribute_associations/%(set_id)s' % {
            'set_id': self.os_attribute_association_id})
        oaa = self.os_attribute_association
        self.assertValidOsAttributeAssociationResponse(r, oaa)

    def test_delete_os_attribute_association(self):
        """DELETE /os_attribute_associations/{os_attribute_association_id}"""
        self.delete('/os_attribute_associations/%(set_id)s' % {
            'set_id': self.os_attribute_association_id})

    # attribute mapping validation

    def assertValidAttributeMappingListResponse(self, resp, ref):
        return self.assertValidListResponse(
            resp,
            'attribute_mappings',
            self.assertValidAttributeMapping,
            ref)

    def assertValidAttributeMappingResponse(self, resp, ref):
        return self.assertValidResponse(
            resp,
            'attribute_mapping',
            self.assertValidAttributeMapping,
            ref)

    def assertValidAttributeMapping(self, entity, ref=None):
        self.assertIsNotNone(entity.get('name'))
        if ref:
            self.assertEqual(ref['name'], entity['name'])
        return entity

    def test_create_attribute_mapping(self):
        """POST /mappings"""
        ref = self.new_attribute_mapping_ref()
        r = self.post(
            '/mappings',
            body={'attribute_mapping': ref})
        return self.assertValidAttributeMappingResponse(r, ref)

    def test_list_attribute_mappings(self):
        """GET /mappings"""
        r = self.get('/mappings')
        self.assertValidAttributeMappingListResponse(r, self.attribute_mapping)

    def test_get_attribute_mapping(self):
        """GET /mappings/{attribute_mapping_id}"""
        r = self.get('/mappings/%(mapping_id)s' % {
            'mapping_id': self.attribute_mapping_id})
        self.assertValidAttributeMappingResponse(r, self.attribute_mapping)

    def test_delete_attribute_mapping(self):
        """DELETE /mappings/{attribute_mapping_id}"""
        self.delete('/mappings/%(mapping_id)s' % {
            'mapping_id': self.attribute_mapping_id})
