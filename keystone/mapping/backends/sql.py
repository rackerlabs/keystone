from keystone.mapping import Driver
from keystone.common import sql
from keystone.identity.backends import sql as identity
from keystone import exception


class Mapping(sql.Base, Driver):

    def __init__(self):
        super(Mapping)

    # Organisational
    #Sets
    def create_org_attribute_set(self, org_attribute_set_id,
                                 org_attribute_set_ref):
        session = self.get_session()
        with session.begin():
            orgset = OrgAttributeSet.from_dict(org_attribute_set_ref)
            session.add(orgset)
            session.flush()
        return orgset.to_dict()

    def get_org_attribute_set(self, set_id):
        session = self.get_session()
        ref = self._get_org_attribute_set(session, set_id).to_dict()
        links = session.query(OrgAttributeAssociation).filter_by(
            org_attribute_set_id=set_id).all()
        ref['attributes'] = [(self.get_org_attribute(
            s.org_attribute_id)) for s in list(links)]
        return ref

    def _get_org_attribute_set(self, session, set_id):
        try:
            return session.query(OrgAttributeSet).filter_by(
                id=set_id).one()
        except sql.NotFound:
            raise exception.OrgAttributeSetNotFound(
                org_attribute_set_id=set_id)

    def list_org_attribute_sets(self):
        session = self.get_session()
        sets = session.query(OrgAttributeSet).all()
        return [s.to_dict() for s in list(sets)]

    def delete_org_attribute_set(self, set_id):
        session = self.get_session()
        with session.begin():
            ref = self._get_org_attribute_set(session, set_id)
            session.query(OrgAttributeAssociation).filter_by(
                org_attribute_set_id=set_id).delete()
            session.delete(ref)
            session.flush()

    # Attributes
    def create_org_attribute(self, context, org_att_ref):
        session = self.get_session()
        with session.begin():
            attribute = OrgAttribute.from_dict(org_att_ref)
            session.add(attribute)
            session.flush()
        return attribute.to_dict()

    def get_org_attribute(self, attribute_id):
        session = self.get_session()
        return self._get_org_attribute(session, attribute_id).to_dict()

    def _get_org_attribute(self, session, attribute_id):
        try:
            return session.query(OrgAttribute).filter_by(
                id=attribute_id).one()
        except sql.NotFound:
            raise exception.OrgAttributeNotFound(id=attribute_id)

    def list_org_attributes(self):
        session = self.get_session()
        attributes = session.query(OrgAttribute).all()
        return [s.to_dict() for s in list(attributes)]

    def delete_org_attribute(self, attribute_id):
        session = self.get_session()
        with session.begin():
            ref = self._get_org_attribute(session, attribute_id)
            session.query(OrgAttributeAssociation).filter_by(
                org_attribute_id=attribute_id).delete()
            session.delete(ref)
            session.flush()

    # Associations
    def create_org_attribute_association(self, context, org_assoc_ref):
        session = self.get_session()
        with session.begin():
            assoc = OrgAttributeAssociation.from_dict(org_assoc_ref)
            session.add(assoc)
            session.flush()
        return assoc.to_dict()

    def get_org_attribute_association(self, assoc_id):
        session = self.get_session()
        return self._get_org_attribute_association(session, assoc_id).to_dict()

    def _get_org_attribute_association(self, session, assoc_id):
        try:
            return session.query(OrgAttributeAssociation).filter_by(
                id=assoc_id).one()
        except sql.NotFound:
            raise exception.OrgAttributeAssociationNotFound(id=assoc_id)

    def list_org_attribute_associations(self):
        session = self.get_session()
        assocs = session.query(OrgAttributeAssociation).all()
        return [s.to_dict() for s in list(assocs)]

    def delete_org_attribute_association(self, assoc_id):
        session = self.get_session()
        with session.begin():
            ref = self._get_org_attribute_association(session, assoc_id)
            session.delete(ref)
            session.flush()

    # Openstack
    #Sets
    def create_os_attribute_set(self, context, os_set_ref):
        session = self.get_session()
        with session.begin():
            osset = OsAttributeSet.from_dict(os_set_ref)
            session.add(osset)
            session.flush()
        return osset.to_dict()

    def get_os_attribute_set(self, set_id):
        session = self.get_session()
        ref = self._get_os_attribute_set(session, set_id).to_dict()
        links = session.query(OsAttributeAssociation).filter_by(
            os_attribute_set_id=set_id).all()
        ref['attributes'] = [(self._get_os_attribute(
            session, s.attribute_id, s.type)) for s in list(links)]
        return ref

    def _get_os_attribute_set(self, session, set_id):
        try:
            return session.query(OsAttributeSet).filter_by(
                id=set_id).one()
        except sql.NotFound:
            raise exception.OsAttributeSetNotFound(set_id=set_id)

    def list_os_attribute_sets(self):
        session = self.get_session()
        sets = session.query(OsAttributeSet).all()
        for s in list(sets):
            s["attributes"] = self._get_os_attribute_set_details(session, s.id)
        return [s.to_dict() for s in list(sets)]

    def delete_os_attribute_set(self, set_id):
        session = self.get_session()
        with session.begin():
            ref = self._get_os_attribute_set(session, set_id)
            session.query(OsAttributeAssociation).filter_by(
                os_attribute_set_id=set_id).delete()
            session.delete(ref)
            session.flush()

    def _get_os_attribute_set_details(self, session, set_id):
        links = session.query(OsAttributeAssociation).filter_by(
            os_attribute_set_id=set_id).all()
        return [(self._get_os_attribute(
            session, s.attribute_id, s.type)) for s in list(links)]

    # Associations
    def create_os_attribute_association(self, context, os_assoc_ref):
        session = self.get_session()
        with session.begin():
            assoc = OsAttributeAssociation.from_dict(os_assoc_ref)
            session.add(assoc)
            session.flush()
        return assoc.to_dict()

    def get_os_attribute_association(self, assoc_id):
        session = self.get_session()
        return self._get_os_attribute_association(session, assoc_id).to_dict()

    def _get_os_attribute_association(self, session, assoc_id):
        try:
            return session.query(OsAttributeAssociation).filter_by(
                id=assoc_id).one()
        except sql.NotFound:
            raise exception.OsAttributeAssociationNotFound(id=assoc_id)

    def list_os_attribute_associations(self):
        session = self.get_session()
        assocs = session.query(OsAttributeAssociation).all()
        return [s.to_dict() for s in list(assocs)]

    def delete_os_attribute_association(self, assoc_id):
        session = self.get_session()
        with session.begin():
            ref = self._get_os_attribute_association(session, assoc_id)
            session.delete(ref)
            session.flush()

    # Possibly the wrong way to do this, and likely not the prettiest -
    # suggestions welcome. Kristy
    # Get an internal (OS attribute)
    def _get_os_attribute(self, session, att_id, type):
        if type == "tenant":
            try:
                ref = session.query(identity.Tenant).filter_by(
                    id=att_id).one().to_dict()
                ref['type'] = type
                return ref
            except sql.NotFound:
                raise exception.ServiceNotFound(id=att_id)
        if type == "role":
            try:
                ref = session.query(identity.Role).filter_by(
                    id=att_id).one().to_dict()
                ref['type'] = type
                return ref
            except sql.NotFound:
                raise exception.ServiceNotFound(id=att_id)
        if type == "domain":
            raise exception.NotImplemented()

    # Attribute Mapping
    def create_mapping(self, context, mapping_ref):
        session = self.get_session()
        with session.begin():
            mapping = AttributeMapping.from_dict(mapping_ref)
            session.add(mapping)
            session.flush()
        return mapping.to_dict()

    def get_mapping(self, mapping_id):
        session = self.get_session()
        ref = self._get_mapping(session, mapping_id)
        ref = ref.to_dict()
        org_id = ref['org_attribute_set_id']
        os_id = ref['os_attribute_set_id']
        ref['org_attribute_set'] = self.get_org_attribute_set(org_id)
        ref['os_attribute_set'] = self.get_os_attribute_set(os_id)
        return ref

    def _get_mapping(self, session, mapping_id):
        try:
            return session.query(AttributeMapping).filter_by(
                id=mapping_id).one()
        except sql.NotFound:
            raise exception.MappingNotFound(id=mapping_id)

    def delete_mapping(self, mapping_id):
        session = self.get_session()
        with session.begin():
            ref = self._get_mapping(session, mapping_id)
            session.delete(ref)
            session.flush()

    def list_mappings(self):
        session = self.get_session()
        mappings = session.query(AttributeMapping).all()
        return [self.get_mapping(m.id) for m in list(mappings)]


class OrgAttributeSet(sql.ModelBase, sql.DictBase):
    __tablename__ = 'org_attribute_set'
    id = sql.Column(sql.String(64), primary_key=True)
    extra = sql.Column(sql.JsonBlob())

    @classmethod
    def from_dict(cls, org_attribute_set_dict):
        extra = {}
        for k, v in org_attribute_set_dict.copy().iteritems():
            if k not in ['id', 'extra']:
                extra[k] = org_attribute_set_dict.pop(k)

        org_attribute_set_dict['extra'] = extra
        return cls(**org_attribute_set_dict)

    def to_dict(self):
        extra_copy = self.extra.copy()
        extra_copy['id'] = self.id
        return extra_copy


class OrgAttribute(sql.ModelBase, sql.DictBase):
    __tablename__ = 'org_attribute'
    id = sql.Column(sql.String(64), primary_key=True)
    type = sql.Column(sql.String(255))
    value = sql.Column(sql.String(255))
    extra = sql.Column(sql.JsonBlob())

    @classmethod
    def from_dict(cls, service_dict):
        extra = {}
        for k, v in service_dict.copy().iteritems():
            if k not in ['id', 'type', 'value', 'extra']:
                extra[k] = service_dict.pop(k)

        service_dict['extra'] = extra
        return cls(**service_dict)

    def to_dict(self):
        extra_copy = self.extra.copy()
        extra_copy['id'] = self.id
        extra_copy['type'] = self.type
        extra_copy['value'] = self.value
        return extra_copy


class OrgAttributeAssociation(sql.ModelBase, sql.DictBase):
    __tablename__ = 'org_attribute_association'
    id = sql.Column(sql.String(64), primary_key=True)
    org_attribute_id = sql.Column(
        sql.String(64), sql.ForeignKey('org_attribute.id'))
    org_attribute_set_id = sql.Column(
        sql.String(64),  sql.ForeignKey('org_attribute_set.id'))
    extra = sql.Column(sql.JsonBlob())

    @classmethod
    def from_dict(cls, org_assoc_dict):
        extra = {}
        for k, v in org_assoc_dict.copy().iteritems():
            if k not in ['id', 'org_attribute_set_id',
                         'org_attribute_id', 'extra']:
                extra[k] = org_assoc_dict.pop(k)
        org_assoc_dict["extra"] = extra
        return cls(**org_assoc_dict)

    def to_dict(self):
        extra_copy = self.extra.copy()
        extra_copy['id'] = self.id
        extra_copy['org_attribute_id'] = self.org_attribute_id
        extra_copy['org_attribute_set_id'] = self.org_attribute_set_id
        return extra_copy


class OsAttributeSet(sql.ModelBase, sql.DictBase):
    __tablename__ = 'os_attribute_set'
    id = sql.Column(sql.String(64), primary_key=True)
    extra = sql.Column(sql.JsonBlob())

    @classmethod
    def from_dict(cls, os_set_dict):
        extra = {}
        for k, v in os_set_dict.copy().iteritems():
            if k not in ['id', 'extra']:
                extra[k] = os_set_dict.pop(k)

        os_set_dict['extra'] = extra
        return cls(**os_set_dict)

    def to_dict(self):
        extra_copy = self.extra.copy()
        extra_copy['id'] = self.id
        return extra_copy


class OsAttributeAssociation(sql.ModelBase, sql.DictBase):
    __tablename__ = 'os_attribute_association'
    id = sql.Column(sql.String(64), primary_key=True)
    attribute_id = sql.Column(sql.String(64))
    os_attribute_set_id = sql.Column(
        sql.String(64),  sql.ForeignKey('os_attribute_set.id'))
    type = sql.Column(sql.String(255))
    extra = sql.Column(sql.JsonBlob())

    @classmethod
    def from_dict(cls, org_assoc_dict):
        extra = {}
        for k, v in org_assoc_dict.copy().iteritems():
            if k not in ['id', 'os_attribute_set_id',
                         'attribute_id', 'type', 'extra']:
                extra[k] = org_assoc_dict.pop(k)
        org_assoc_dict["extra"] = extra

        return cls(**org_assoc_dict)

    def to_dict(self):
        extra_copy = self.extra.copy()
        extra_copy['id'] = self.id
        extra_copy['attribute_id'] = self.attribute_id
        extra_copy['os_attribute_set_id'] = self.os_attribute_set_id
        extra_copy['type'] = self.type
        return extra_copy


class AttributeMapping(sql.ModelBase, sql.DictBase):
    __tablename__ = 'attribute_mapping'
    id = sql.Column(sql.String(64), primary_key=True)
    org_attribute_set_id = sql.Column(
        sql.String(64),  sql.ForeignKey('org_attribute_set.id'))
    os_attribute_set_id = sql.Column(
        sql.String(64),  sql.ForeignKey('os_attribute_set.id'))
    extra = sql.Column(sql.JsonBlob())

    @classmethod
    def from_dict(cls, mapping_dict):
        extra = {}
        for k, v in mapping_dict.copy().iteritems():
            if k not in ['id', 'os_attribute_set_id',
                         'org_attribute_set_id', 'extra']:
                extra[k] = mapping_dict.pop(k)
        mapping_dict["extra"] = extra
        return cls(**mapping_dict)

    def to_dict(self):
        extra_copy = self.extra.copy()
        extra_copy['id'] = self.id
        extra_copy['org_attribute_set_id'] = self.org_attribute_set_id
        extra_copy['os_attribute_set_id'] = self.os_attribute_set_id
        return extra_copy
