import uuid

from keystone.common import dependency


@dependency.requires('credential_api')
class Credential(dict):

    @property
    def id(self):
        return self['id']

    @property
    def user_id(self):
        return self['user_id']

    @property
    def project_id(self):
        return self['project_id']

    @property
    def type(self):
        return self['type']

    @property
    def blob(self):
        return self['blob']

    def destroy(self):
        self.delete(self.id)

    def save(self):
        self.credential_api.update_credential(self.id, self)

    def _create(self):
        self.credential_api.create_credential(self.id, self)

    @classmethod
    def list(cls):
        return [Credential(c) for c in
                cls.get_credential_api().list_credentials()]

    @classmethod
    def get(cls, credential_id):
        credential = cls.get_credential_api().get_credential(credential_id)
        return Credential(credential)

    @classmethod
    def new(cls, id=None, name=None, description=None, enabled=True,
            user_id=None, project_id=None, blob=None, type=None):

        if not id:
            id = uuid.uuid4().hex

        credential = Credential(id=id,
                                name=name,
                                description=description,
                                enabled=enabled,
                                user_id=user_id,
                                project_id=project_id,
                                blob=blob,
                                type=type)
        return credential

    @classmethod
    def create(cls, *args, **kwargs):
        credential = cls.new(*args, **kwargs)
        credential._create()
        return credential

    @classmethod
    def update(cls, *args, **kwargs):
        credential = cls.new(*args, **kwargs)
        credential.save()
        return credential

    @classmethod
    def delete(cls, credential_id):
        return cls.get_credential_api().delete_credential(credential_id)
