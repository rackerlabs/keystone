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

"""SQL backends for the various services."""
import functools

import sqlalchemy as sql
from sqlalchemy.ext import declarative
from sqlalchemy.orm.attributes import InstrumentedAttribute
import sqlalchemy.pool
from sqlalchemy import types as sql_types

from keystone.common import logging
from keystone import config
from keystone import exception
from keystone.openstack.common.db import exception as db_exc
from keystone.openstack.common.db.sqlalchemy import models
from keystone.openstack.common.db.sqlalchemy import session
from keystone.openstack.common import jsonutils


LOG = logging.getLogger(__name__)
CONF = config.CONF

# maintain a single engine reference for sqlalchemy engine
GLOBAL_ENGINE = None
GLOBAL_ENGINE_CALLBACKS = set()


ModelBase = declarative.declarative_base()


# For exporting to other modules
Column = sql.Column
String = sql.String
ForeignKey = sql.ForeignKey
DateTime = sql.DateTime
IntegrityError = sql.exc.IntegrityError
OperationalError = sql.exc.OperationalError
NotFound = sql.orm.exc.NoResultFound
Boolean = sql.Boolean
Text = sql.Text
UniqueConstraint = sql.UniqueConstraint


def initialize_decorator(init):
    """Ensure that the length of string field do not exceed the limit.

    This decorator check the initialize arguments, to make sure the
    length of string field do not exceed the length limit, or raise a
    'StringLengthExceeded' exception.

    Use decorator instead of inheritance, because the metaclass will
    check the __tablename__, primary key columns, etc. at the class
    definition.

    """
    def initialize(self, *args, **kwargs):
        cls = type(self)
        for k, v in kwargs.items():
            if hasattr(cls, k):
                attr = getattr(cls, k)
                if isinstance(attr, InstrumentedAttribute):
                    column = attr.property.columns[0]
                    if isinstance(column.type, String):
                        if not isinstance(v, unicode):
                            v = str(v)
                        if column.type.length and \
                                column.type.length < len(v):
                            raise exception.StringLengthExceeded(
                                string=v, type=k, length=column.type.length)

        init(self, *args, **kwargs)
    return initialize

ModelBase.__init__ = initialize_decorator(ModelBase.__init__)


def set_global_engine(engine):
    """Set the global engine.

    This sets the current global engine, which is returned by
    Base.get_engine(allow_global_engine=True).

    When the global engine is changed, all of the callbacks registered via
    register_global_engine_callback since the last time set_global_engine was
    changed are called. The callback functions are invoked with no arguments.

    """

    global GLOBAL_ENGINE
    global GLOBAL_ENGINE_CALLBACKS

    if engine is GLOBAL_ENGINE:
        # It's the same engine so nothing to do.
        return

    if engine is None:
        session.cleanup()

    GLOBAL_ENGINE = engine

    cbs = GLOBAL_ENGINE_CALLBACKS
    GLOBAL_ENGINE_CALLBACKS = set()
    for cb in cbs:
        try:
            cb()
        except Exception:
            LOG.exception(_("Global engine callback raised."))
            # Just logging the exception so can process other callbacks.


def register_global_engine_callback(cb_fn):
    """Register a function to be called when the global engine is set.

    Note that the callback will be called only once or not at all, so to get
    called each time the global engine is changed the function must be
    re-registered.

    """

    global GLOBAL_ENGINE_CALLBACKS

    GLOBAL_ENGINE_CALLBACKS.add(cb_fn)


# Special Fields
class JsonBlob(sql_types.TypeDecorator):

    impl = sql.Text

    def process_bind_param(self, value, dialect):
        return jsonutils.dumps(value)

    def process_result_value(self, value, dialect):
        return jsonutils.loads(value)


class DictBase(models.ModelBase):
    attributes = []

    @classmethod
    def from_dict(cls, d):
        new_d = d.copy()

        new_d['extra'] = dict((k, new_d.pop(k)) for k in d.iterkeys()
                              if k not in cls.attributes and k != 'extra')

        return cls(**new_d)

    def to_dict(self, include_extra_dict=False):
        """Returns the model's attributes as a dictionary.

        If include_extra_dict is True, 'extra' attributes are literally
        included in the resulting dictionary twice, for backwards-compatibility
        with a broken implementation.

        """
        d = self.extra.copy()
        for attr in self.__class__.attributes:
            d[attr] = getattr(self, attr)

        if include_extra_dict:
            d['extra'] = self.extra.copy()

        return d


# Backends
class Base(object):
    def get_session(self, autocommit=True, expire_on_commit=False):
        """Return a SQLAlchemy session."""
        return session.get_session(
            autocommit=autocommit, expire_on_commit=expire_on_commit)

    def get_engine(self, allow_global_engine=True):
        """Return a SQLAlchemy engine.

        If allow_global_engine is True and an in-memory sqlite connection
        string is provided by CONF, all backends will share a global sqlalchemy
        engine.

        """
        def new_engine():
            connection_dict = sql.engine.url.make_url(CONF.database.connection)

            engine_config = {
                'convert_unicode': True,
                'echo': CONF.debug and CONF.verbose,
                'pool_recycle': CONF.database.idle_timeout,
            }

            if 'sqlite' in connection_dict.drivername:
                engine_config['poolclass'] = sqlalchemy.pool.StaticPool

            engine = sql.create_engine(
                CONF.database.connection, **engine_config)

            if engine.name == 'mysql':
                sql.event.listen(engine, 'checkout', session.ping_listener)

            return engine

        if not allow_global_engine:
            return new_engine()

        if GLOBAL_ENGINE:
            return GLOBAL_ENGINE

        engine = session.get_engine(sqlite_fk=False, slave_engine=False)

        # auto-build the db to support wsgi server w/ in-memory backend
        if CONF.database.connection == 'sqlite://':
            ModelBase.metadata.create_all(bind=engine)

        set_global_engine(engine)

        return engine

    def get_sessionmaker(self, engine, autocommit=True,
                         expire_on_commit=False):
        """Return a SQLAlchemy sessionmaker using the given engine."""
        return session.get_maker(
            engine, autocommit=autocommit, expire_on_commit=expire_on_commit)


def handle_conflicts(type='object'):
    """Converts IntegrityError into HTTP 409 Conflict."""
    def decorator(method):
        @functools.wraps(method)
        def wrapper(*args, **kwargs):
            try:
                return method(*args, **kwargs)
            except (IntegrityError, OperationalError) as e:
                raise exception.Conflict(type=type, details=str(e.orig))
            except db_exc.DBDuplicateEntry as e:
                msg = "Duplicate values in column(s) {0}".format(
                    ", ".join(e.columns))
                raise exception.Conflict(type=type, details=msg)
            except db_exc.DBError as e:
                raise exception.Conflict(type=type,
                                         details=str(e.inner_exception.orig))
        return wrapper
    return decorator
