# vim: tabstop=4 shiftwidth=4 softtabstop=4

import datetime

from keystone import token
from keystone.common import sql


class TokenModel(sql.ModelBase, sql.DictBase):
    __tablename__ = 'token'
    id = sql.Column(sql.String(64), primary_key=True)
    expire_at = sql.Column(sql.DateTime())
    extra = sql.Column(sql.JsonBlob())

    @classmethod
    def from_dict(cls, token_dict):
        # shove any non-indexed properties into extra
        data = {}
        token_dict_copy = token_dict.copy()
        for k in ('id', 'expire_at'):
            data[k] = token_dict_copy.pop(k)
        data['extra'] = token_dict_copy
        return cls(**data)

    def to_dict(self):
        extra_copy = self.extra.copy()
        extra_copy['id'] = self.id
        extra_copy['expire_at'] = self.expire_at
        return extra_copy


class Token(sql.Base, token.Driver):
    # Public interface
    def get_token(self, token_id):
        session = self.get_session()
        now = datetime.datetime.now()
        token_ref = session.query(TokenModel)\
                                .filter_by(id=token_id)\
                                .filter(now < TokenModel.expire_at)\
                                .first()
        if not token_ref:
            return
        return token_ref.to_dict()

    def create_token(self, token_id, data):
        data['id'] = token_id

        if 'expire_at' not in data:
            data['expire_at'] = self.get_default_expire_time()

        session = self.get_session()
        with session.begin():
            token_ref = TokenModel.from_dict(data)
            session.add(token_ref)
            session.flush()

        return token_ref.to_dict()

    def delete_token(self, token_id):
        session = self.get_session()
        token_ref = session.query(TokenModel)\
                                .filter_by(id=token_id)\
                                .first()
        with session.begin():
            session.delete(token_ref)
            session.flush()
