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
import sqlalchemy.engine.url
from sqlalchemy.exc import DisconnectionError
from sqlalchemy.ext import declarative
import sqlalchemy.orm
from sqlalchemy.orm.attributes import InstrumentedAttribute
import sqlalchemy.pool
from sqlalchemy import types as sql_types

from keystone.common import utils
from keystone import config
from keystone import exception
from keystone.openstack.common import jsonutils
from keystone.openstack.common import log as logging


LOG = logging.getLogger(__name__)
CONF = config.CONF

# maintain a single engine reference for sqlalchemy engine
GLOBAL_ENGINE = None
GLOBAL_ENGINE_CALLBACKS = set()


ModelBase = declarative.declarative_base()


# For exporting to other modules
Column = sql.Column
Index = sql.Index
String = sql.String
ForeignKey = sql.ForeignKey
DateTime = sql.DateTime
IntegrityError = sql.exc.IntegrityError
OperationalError = sql.exc.OperationalError
NotFound = sql.orm.exc.NoResultFound
Boolean = sql.Boolean
Text = sql.Text
UniqueConstraint = sql.UniqueConstraint
relationship = sql.orm.relationship
joinedload = sql.orm.joinedload


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


class DictBase(object):
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

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getitem__(self, key):
        if key in self.extra:
            return self.extra[key]
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def __iter__(self):
        self._i = iter(sqlalchemy.orm.object_mapper(self).columns)
        return self

    def next(self):
        n = self._i.next().name
        return n

    def update(self, values):
        """Make the model object behave like a dict."""
        for k, v in values.iteritems():
            setattr(self, k, v)

    def iteritems(self):
        """Make the model object behave like a dict.

        Includes attributes from joins.

        """
        return dict([(k, getattr(self, k)) for k in self])
        #local = dict(self)
        #joined = dict([(k, v) for k, v in self.__dict__.iteritems()
        #               if not k[0] == '_'])
        #local.update(joined)
        #return local.iteritems()


def mysql_on_checkout(dbapi_conn, connection_rec, connection_proxy):
    """Ensures that MySQL connections checked out of the pool are alive.

    Borrowed from:
    http://groups.google.com/group/sqlalchemy/msg/a4ce563d802c929f

    Error codes caught:
    * 2006 MySQL server has gone away
    * 2013 Lost connection to MySQL server during query
    * 2014 Commands out of sync; you can't run this command now
    * 2045 Can't open shared memory; no answer from server (%lu)
    * 2055 Lost connection to MySQL server at '%s', system error: %d

    from http://dev.mysql.com/doc/refman/5.6/en/error-messages-client.html
    """
    try:
        dbapi_conn.cursor().execute('select 1')
    except dbapi_conn.OperationalError as e:
        if e.args[0] in (2006, 2013, 2014, 2045, 2055):
            logging.warn(_('Got mysql server has gone away: %s'), e)
            raise DisconnectionError("Database server went away")
        else:
            raise


# Backends
class Base(object):
    _engine = None
    _sessionmaker = None

    def get_session(self, autocommit=True, expire_on_commit=False):
        """Return a SQLAlchemy session."""
        if not self._engine:
            self._engine = self.get_engine()
            self._sessionmaker = self.get_sessionmaker(self._engine)
            register_global_engine_callback(self.clear_engine)
        return self._sessionmaker(autocommit=autocommit,
                                  expire_on_commit=expire_on_commit)

    def get_engine(self, allow_global_engine=True):
        """Return a SQLAlchemy engine.

        If allow_global_engine is True and an in-memory sqlite connection
        string is provided by CONF, all backends will share a global sqlalchemy
        engine.

        """
        def new_engine():
            connection_dict = sql.engine.url.make_url(CONF.sql.connection)

            engine_config = {
                'convert_unicode': True,
                'echo': CONF.debug and CONF.verbose,
                'pool_recycle': CONF.sql.idle_timeout,
            }

            if 'sqlite' in connection_dict.drivername:
                engine_config['poolclass'] = sqlalchemy.pool.StaticPool

            engine = sql.create_engine(CONF.sql.connection, **engine_config)

            if engine.name == 'mysql':
                sql.event.listen(engine, 'checkout', mysql_on_checkout)

            return engine

        if not allow_global_engine:
            return new_engine()

        if GLOBAL_ENGINE:
            return GLOBAL_ENGINE

        engine = new_engine()

        # auto-build the db to support wsgi server w/ in-memory backend
        if CONF.sql.connection == 'sqlite://':
            ModelBase.metadata.create_all(bind=engine)

        set_global_engine(engine)

        return engine

    def get_sessionmaker(self, engine, autocommit=True,
                         expire_on_commit=False):
        """Return a SQLAlchemy sessionmaker using the given engine."""
        return sqlalchemy.orm.sessionmaker(
            bind=engine,
            autocommit=autocommit,
            expire_on_commit=expire_on_commit)

    def clear_engine(self):
        self._engine = None
        self._sessionmaker = None

    def filter(self, model, query, request_dict, valid_filters):
        """Applies filtering to a query.

        :param model: the table model in question
        :param query: query to apply filters to
        :param request_dict: dictionary of filters.  This will be modified
                             to remove any filters that have been satisfied.
        :param valid_filters: list of keys to apply filtering to

        :returns satisfied, query: satisfied is True if all valid filters could
                                   be added to the query

        """
        def inexact_filter(model, query, item, request_dict):
            """Applies an inexact filter to a query.

            :param model: the table model in question
            :param query: query to apply filters to
            :param item: item the filter in question
            :param request_dict: dictionary of filters

            :returns satisfied, query: satisfied is True if all valid filters
                                       could be added to the query

            """
            key, value = item.split('__', 1)
            column_attr = getattr(model, key)

            if value not in utils.INEXACT_FILTERS_SUPPORTED:
                # Better to error out now, rather than fail to match the filter
                # here, do a (potentially big) unfiltered query, pass it back
                # to the contoller and then just fail there.
                msg = _('Unsupported inexact string filter: %s') % item
                raise exception.ValidationError(msg)

            if value == 'contains':
                query_term = column_attr.like('%%%s%%' % request_dict[item])
            elif value == 'icontains':
                query_term = column_attr.ilike('%%%s%%' % request_dict[item])
            elif value == 'startswith':
                query_term = column_attr.like('%s%%' % request_dict[item])
            elif value == 'istartswith':
                query_term = column_attr.ilike('%s%%' % request_dict[item])
            elif value == 'endswith':
                query_term = column_attr.like('%%%s' % request_dict[item])
            elif value == 'iendswith':
                query_term = column_attr.ilike('%%%s' % request_dict[item])
            else:
                msg = (_('Missing code for inexact filter: %s') % item)
                LOG.debug(msg)
                return (False, query)

            return (True, query.filter(query_term))

        filter_dict = {}
        all_filters_satisifed = True
        for key in valid_filters:
            if key in request_dict:
                if isinstance(model.__table__.c[key].type,
                              sqlalchemy.types.Boolean):
                    filter_dict[key] = utils.attr_as_boolean(
                        request_dict.pop(key))
                else:
                    filter_dict[key] = request_dict.pop(key)
            else:
                # Check for inexact filter requests
                for item in request_dict:
                    if item.startswith(key + '__'):
                        satisfied, query = inexact_filter(
                            model, query, item, request_dict)
                        # If we could satisfy it then remove from the
                        # request_dict, else ensure we tell the caller
                        # function that we need some help at a higher level.
                        if satisfied:
                            request_dict.pop(item)
                        else:
                            all_filters_satisifed = False
                        break

        # Apply any exact filers we built up
        if filter_dict:
            query = query.filter_by(**filter_dict)

        return (all_filters_satisifed, query)

    def paginate_or_limit(self, query, request_dict, limit):
        """Applies pagination or limit to a query.

        If no pagination requested, then apply any supplied upper limit.

        :param query: query to apply filters to
        :param request_dict: dictionary of filters
        :param limit: hard limit to apply if no pagination

        :returns updated query

        """
        # TODO(henry-nash): Add pagination support here

        # If no pagination requested, set an upper limit if supplied
        if limit is not None:
            query = query.limit(limit)
        return query

    def filter_and_paginate(self, model, query, request_dict,
                            valid_filters, limit=None):
        """Applies filtering and pagination/limit to a query.

        :param model: table model
        :param query: query to apply filters to
        :param request_dict: dictionary of filters.  This will be modified
                             to remove any filters that have been satisfied.
        :param valid_filters: list of keys to apply filtering to
        :param limit: hard limit to apply if no pagination

        :returns updated query

        """
        ok_to_paginate = True
        if request_dict is not None and valid_filters is not None:
            ok_to_paginate, query = self.filter(model, query,
                                                request_dict, valid_filters)

        # We can only try and paginate or limit here if we supported all the
        # specified filters, sine otherwise this will mess up the results. Any
        # unsatisfied filters will have been left in the request_dict for the
        # controller to handle.
        #
        # At the moment, we guarantee to satisfy all supported filters, but
        # this principle may be useful in the future.

        if ok_to_paginate:
            return self.paginate_or_limit(query, request_dict, limit)
        else:
            return query


def handle_conflicts(type='object'):
    """Converts IntegrityError into HTTP 409 Conflict."""
    def decorator(method):
        @functools.wraps(method)
        def wrapper(*args, **kwargs):
            try:
                return method(*args, **kwargs)
            except (IntegrityError, OperationalError) as e:
                raise exception.Conflict(type=type, details=str(e.orig))
        return wrapper
    return decorator
