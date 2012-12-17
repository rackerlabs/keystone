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

        self.attribute_mapping_id = uuid.uuid4().hex
        self.attribute_mapping = self.new_attribute_mapping_ref()
        self.attribute_mapping['id'] = self.attribute_mapping_id
        os_set = self.os_attribute_set_id
        org_set = self.org_attribute_set_id
        self.attribute_mapping['org_attribute_set_id'] = org_set
        self.attribute_mapping['os_attribute_set_id'] = os_set
        self.mapping_api.create_attribute_set_mapping(
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

    def test_list_attributes_in_org_set(self):
        """GET /org_attribute_sets/{set_id}/attributes"""
        self.get('/org_attribute_sets/%(set_id)s/attributes' % {
            'set_id': self.org_attribute_set_id})

    def test_add_attribute_to_org_set(self):
        """PUT /org_attribute_sets/{set_id}/attributes/{attribute_id}"""
        url = '/org_attribute_sets/%(set_id)s/' % {
              'set_id': self.org_attribute_set_id}
        url += 'attributes/%(attribute_id)s' % {
            'attribute_id': self.org_attribute_id}
        self.put(url)

    def test_check_attribute_in_org_set(self):
        """HEAD /org_attribute_sets/{set_id}/attributes/{attribute_id}"""
        url = '/org_attribute_sets/%(set_id)s/' % {
              'set_id': self.org_attribute_set_id}
        url += 'attributes/%(attribute_id)s' % {
            'attribute_id': self.org_attribute_id}
        self.put(url)
        self.head(url)

    def test_remove_attribute_from_org_set(self):
        """DELETE /org_attribute_sets/{set_id}/attributes/{attribute_id}"""
        url = '/org_attribute_sets/%(set_id)s/' % {
              'set_id': self.org_attribute_set_id}
        url += 'attributes/%(attribute_id)s' % {
            'attribute_id': self.org_attribute_id}
        self.put(url)
        self.delete(url)

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

    def test_list_attributes_in_os_set(self):
        """GET /os_attribute_sets/{os_attribute_set_id/attributes"""
        url = '/os_attribute_sets/%(os_attribute_set_id)s/attributes' % {
            'os_attribute_set_id': self.os_attribute_set_id}
        self.get(url)

    def test_add_attribute_to_os_set(self):
        """PUT /os_attribute_sets/{set_id}/attributes/{attribute_id}"""
        url = '/os_attribute_sets/%(set_id)s/' % {
              'set_id': self.os_attribute_set_id}
        url += 'attributes/%(attribute_id)s?type=role' % {
            'attribute_id': self.role_id}
        self.put(url)

    def test_remove_attribute_from_os_set(self):
        """DELETE /os_attribute_sets/{set_id}/attributes/{attribute_id}"""
        url = '/os_attribute_sets/%(set_id)s/' % {
              'set_id': self.os_attribute_set_id}
        url += 'attributes/%(attribute_id)s?type=role' % {
            'attribute_id': self.role_id}
        self.put(url)
        self.delete(url)

    def test_check_attribute_in_os_set(self):
        """HEAD /os_attribute_sets/{set_id}/attributes/{attribute_id}"""
        url = '/os_attribute_sets/%(set_id)s/' % {
              'set_id': self.os_attribute_set_id}
        url += 'attributes/%(attribute_id)s?type=role' % {
            'attribute_id': self.role_id}
        self.put(url)
        self.head(url)

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

    # attribute mapping validation

    def assertValidAttributeMappingListResponse(self, resp, ref):
        return self.assertValidListResponse(
            resp,
            'attribute_set_mappings',
            self.assertValidAttributeMapping,
            ref)

    def assertValidAttributeMappingResponse(self, resp, ref):
        return self.assertValidResponse(
            resp,
            'attribute_set_mapping',
            self.assertValidAttributeMapping,
            ref)

    def assertValidAttributeMapping(self, entity, ref=None):
        self.assertIsNotNone(entity.get('name'))
        if ref:
            self.assertEqual(ref['name'], entity['name'])
        return entity

    def test_create_attribute_set_mapping(self):
        """POST /mappings"""
        ref = self.new_attribute_mapping_ref()
        ref['org_attribute_set_id'] = self.org_attribute_set_id
        ref['os_attribute_set_id'] = self.os_attribute_set_id
        r = self.post(
            '/attribute_set_mappings',
            body={'attribute_set_mapping': ref})
        return self.assertValidAttributeMappingResponse(r, ref)

    def test_list_attribute_set_mappings(self):
        """GET /attribute_set_mappings"""
        r = self.get('/attribute_set_mappings')
        self.assertValidAttributeMappingListResponse(r, self.attribute_mapping)

    def test_get_attribute_set_mapping(self):
        """GET /attribute_set_mappings/{attribute_set_mapping_id}"""
        r = self.get('/attribute_set_mappings/%(mapping_id)s' % {
            'mapping_id': self.attribute_mapping_id})
        self.assertValidAttributeMappingResponse(r, self.attribute_mapping)

    def test_delete_attribute_set_mapping(self):
        """DELETE /attribute_set_mappings/{attribute_set_mapping_id}"""
        self.delete('/attribute_set_mappings/%(mapping_id)s' % {
            'mapping_id': self.attribute_mapping_id})
