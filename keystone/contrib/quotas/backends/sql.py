import uuid

from keystone.common import sql
from keystone.common.sql import migration
from keystone import exception


class Resource(sql.ModelBase, sql.DictBase):
    __tablename__ = 'resource'
    attributes = ['id', 'name', 'default_limit', 'description']

    id = sql.Column(sql.String(64), primary_key=True, nullable=False)
    name = sql.Column(sql.String(64), unique=True, nullable=False)
    default_limit = sql.Column(sql.Integer, nullable=False)
    description = sql.Column(sql.String(255))

    @classmethod
    def from_dict(cls, user_dict):
        return cls(**user_dict)

    def to_dict(self):
        return dict(self.iteritems())


class ProjectQuota(sql.ModelBase, sql.DictBase):
    __tablename__ = 'project_quota'
    attributes = ['id', 'resource_id', 'project_id', 'limit']

    id = sql.Column(sql.String(64), primary_key=True, nullable=False)
    resource_id = sql.Column(sql.ForeignKey('resource.id'), nullable=False)
    project_id = sql.Column(sql.ForeignKey('project.id'), nullable=False)
    limit = sql.Column(sql.Integer, nullable=False)

    @classmethod
    def from_dict(cls, user_dict):
        return cls(**user_dict)

    def to_dict(self):
        return dict(self.iteritems())


class UserQuota(sql.ModelBase, sql.DictBase):
    __tablename__ = 'user_quota'
    attributes = ['id', 'resource_id', 'user_id', 'limit']

    id = sql.Column(sql.String(64), primary_key=True, nullable=False)
    resource_id = sql.Column(sql.ForeignKey('resource.id'), nullable=False)
    user_id = sql.Column(sql.ForeignKey('user.id'), nullable=False)
    limit = sql.Column(sql.Integer, nullable=False)

    @classmethod
    def from_dict(cls, user_dict):
        return cls(**user_dict)

    def to_dict(self):
        return dict(self.iteritems())


class SQLQuotaDriver(sql.Base):

    def db_sync(self):
        migration.db_sync()

    # resource ops

    @sql.handle_conflicts(type='resource')
    def create_resource(self, resource):
        resource_id = uuid.uuid4().hex
        resource['id'] = resource_id
        session = self.get_session()

        with session.begin():
            ref = Resource.from_dict(resource)
            session.add(ref)
            session.flush()

        return ref.to_dict()

    def list_resources(self):
        session = self.get_session()
        refs = session.query(Resource).all()
        return [ref.to_dict() for ref in refs]

    def _get_resource(self, session, resource_id):
        ref = session.query(Resource).get(resource_id)
        if not ref:
            raise exception.NotFound(_('Resource not found'))
        return ref

    def get_resource(self, resource_id):
        session = self.get_session()
        return self._get_resource(session, resource_id).to_dict()

    @sql.handle_conflicts(type='resource')
    def update_resource(self, resource_id, resource):
        session = self.get_session()
        if 'id' in resource and resource_id != resource['id']:
            raise exception.ValidationError('Cannot change resource ID')

        with session.begin():
            ref = self._get_resource(session, resource_id)
            old_dict = ref.to_dict()
            for key in resource:
                old_dict[key] = resource[key]
            new_resource = Resource.from_dict(old_dict)
            for attr in Resource.attributes:
                if attr != 'id':
                    setattr(ref, attr, getattr(new_resource, attr))
            session.flush()
        return ref.to_dict()

    def delete_resource(self, resource_id):
        session = self.get_session()

        with session.begin():
            ref = self._get_resource(session, resource_id)

            q = session.query(UserQuota)
            q = q.filter_by(resource_id=resource_id)
            q.delete(False)

            session.delete(ref)
            session.flush()

    # user quotas ops

    @sql.handle_conflicts(type='user_quota')
    def create_user_quota(self, user_id, quota):
        quota['id'] = uuid.uuid4().hex
        quota['user_id'] = user_id
        session = self.get_session()

        with session.begin():
            ref = UserQuota.from_dict(quota)
            session.add(ref)
            session.flush()

        return ref.to_dict()

    def _get_user_quota(self, session, quota_id):
        ref = session.query(UserQuota).get(quota_id)
        if not ref:
            raise exception.NotFound('User quota not found')
        return ref

    def get_user_quota(self, user_id, quota_id):
        session = self.get_session()
        return self._get_user_quota(session, quota_id).to_dict()

    def update_user_quota(self, user_id, quota_id, quota):
        for key in quota.keys():
            if key not in ['limit']:
                raise Exception('Bad request')

        session = self.get_session()

        with session.begin():
            ref = self._get_user_quota(session, quota_id)
            if ref.user_id != user_id:
                raise Exception('Not Found')
            for key, value in quota.items():
                setattr(ref, key, value)
            session.flush()
        return ref.to_dict()

    def delete_user_quota(self, user_id, quota_id):
        session = self.get_session()
        q = session.query(UserQuota).filter_by(id=quota_id, user_id=user_id).first()

        if not q.first():
            raise exception.UserQuotaNotFound(quota_id=quota_id)

        with session.begin():
            ref = self._get_quota(session, quota_id)

            q.delete(False)

            session.delete(ref)
            session.flush()

    def list_user_quotas(self, user_id):
        session = self.get_session()
        refs = session.query(UserQuota).filter_by(user_id=user_id).all()
        return [ref.to_dict() for ref in refs]

    # project quotas ops

    @sql.handle_conflicts(type='project_quota')
    def create_project_quota(self, project_id, quota):
        quota['id'] = uuid.uuid4().hex
        quota['project_id'] = project_id
        session = self.get_session()

        with session.begin():
            ref = ProjectQuota.from_dict(quota)
            session.add(ref)
            session.flush()

        return ref.to_dict()

    def _get_project_quota(self, session, quota_id):
        ref = session.query(ProjectQuota).get(quota_id)
        if not ref:
            raise exception.NotFound('Project quota not found')
        return ref

    def get_project_quota(self, project_id, quota_id):
        session = self.get_session()
        return self._get_project_quota(session, quota_id).to_dict()

    def update_project_quota(self, project_id, quota_id, quota):
        for key in quota.keys():
            if key not in ['limit']:
                raise Exception('Bad request')

        session = self.get_session()

        with session.begin():
            ref = self._get_project_quota(session, quota_id)
            if ref.project_id != project_id:
                raise Exception('Not Found')
            for key, value in quota.items():
                setattr(ref, key, value)
            session.flush()
        return ref.to_dict()

    def delete_project_quota(self, project_id, quota_id):
        session = self.get_session()
        q = session.query(ProjectQuota).filter_by(id=quota_id, project_id=project_id).first()

        if not q.first():
            raise exception.ProjectQuotaNotFound(quota_id=quota_id)

        with session.begin():
            ref = self._get_quota(session, quota_id)

            q.delete(False)

            session.delete(ref)
            session.flush()

    def list_project_quotas(self, project_id):
        session = self.get_session()
        refs = session.query(ProjectQuota).filter_by(project_id=project_id).all()
        return [ref.to_dict() for ref in refs]

