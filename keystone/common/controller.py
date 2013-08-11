import collections
import functools
import uuid

from keystone.common import dependency
from keystone.common import utils
from keystone.common import wsgi
from keystone import config
from keystone import exception
from keystone.openstack.common import log as logging

LOG = logging.getLogger(__name__)
CONF = config.CONF
DEFAULT_DOMAIN_ID = CONF.identity.default_domain_id


def _build_policy_check_credentials(self, action, context, kwargs):
    LOG.debug(_('RBAC: Authorizing %(action)s(%(kwargs)s)') % {
        'action': action,
        'kwargs': ', '.join(['%s=%s' % (k, kwargs[k]) for k in kwargs])})

    try:
        token_ref = self.token_api.get_token(context['token_id'])
    except exception.TokenNotFound:
        LOG.warning(_('RBAC: Invalid token'))
        raise exception.Unauthorized()

    # NOTE(jamielennox): whilst this maybe shouldn't be within this function
    # it would otherwise need to reload the token_ref from backing store.
    wsgi.validate_token_bind(context, token_ref)

    creds = {}
    if 'token_data' in token_ref and 'token' in token_ref['token_data']:
        #V3 Tokens
        token_data = token_ref['token_data']['token']
        try:
            creds['user_id'] = token_data['user']['id']
        except AttributeError:
            LOG.warning(_('RBAC: Invalid user'))
            raise exception.Unauthorized()

        if 'project' in token_data:
            creds['project_id'] = token_data['project']['id']
        else:
            LOG.debug(_('RBAC: Proceeding without project'))

        if 'domain' in token_data:
            creds['domain_id'] = token_data['domain']['id']

        if 'roles' in token_data:
            creds['roles'] = []
            for role in token_data['roles']:
                creds['roles'].append(role['name'])
    else:
        #v2 Tokens
        creds = token_ref.get('metadata', {}).copy()
        try:
            creds['user_id'] = token_ref['user'].get('id')
        except AttributeError:
            LOG.warning(_('RBAC: Invalid user'))
            raise exception.Unauthorized()
        try:
            creds['project_id'] = token_ref['tenant'].get('id')
        except AttributeError:
            LOG.debug(_('RBAC: Proceeding without tenant'))
        # NOTE(vish): this is pretty inefficient
        creds['roles'] = [self.identity_api.get_role(role)['name']
                          for role in creds.get('roles', [])]

    return creds


def flatten(d, parent_key=''):
    """Flatten a nested dictionary

    Converts a dictionary with nested values to a single level flat
    dictionary, with dotted notation for each key.

    """
    items = []
    for k, v in d.items():
        new_key = parent_key + '.' + k if parent_key else k
        if isinstance(v, collections.MutableMapping):
            items.extend(flatten(v, new_key).items())
        else:
            items.append((new_key, v))
    return dict(items)


def protected(f):
    """Wraps API calls with role based access controls (RBAC)."""
    @functools.wraps(f)
    def wrapper(self, context, *args, **kwargs):
        if 'is_admin' in context and context['is_admin']:
            LOG.warning(_('RBAC: Bypassing authorization'))
        else:
            action = 'identity:%s' % f.__name__
            creds = _build_policy_check_credentials(self, action,
                                                    context, kwargs)
            # Simply use the passed kwargs as the target dict, which
            # would typically include the prime key of a get/update/delete
            # call.
            self.policy_api.enforce(creds, action, flatten(kwargs))
            LOG.debug(_('RBAC: Authorization granted'))

        return f(self, context, *args, **kwargs)
    return wrapper


def filterprotected(*filters):
    """Wraps filtered API calls with role based access controls (RBAC)."""

    def _filterprotected(f):
        @functools.wraps(f)
        def wrapper(self, context, **kwargs):
            if not context['is_admin']:
                action = 'identity:%s' % f.__name__
                creds = _build_policy_check_credentials(self, action,
                                                        context, kwargs)
                # Now, build the target dict for policy check.  We include:
                #
                # - Any query filter parameters
                # - Data from the main url (which will be in the kwargs
                #   parameter) and would typically include the prime key
                #   of a get/update/delete call
                #
                # First  any query filter parameters
                target = dict()
                if len(filters) > 0:
                    for item in filters:
                        if item in context['query_string']:
                            target[item] = context['query_string'][item]

                    LOG.debug(_('RBAC: Adding query filter params (%s)') % (
                        ', '.join(['%s=%s' % (item, target[item])
                                  for item in target])))

                # Now any formal url parameters
                for key in kwargs:
                    target[key] = kwargs[key]

                self.policy_api.enforce(creds, action, flatten(target))

                LOG.debug(_('RBAC: Authorization granted'))
            else:
                LOG.warning(_('RBAC: Bypassing authorization'))
            return f(self, context, filters, **kwargs)
        return wrapper
    return _filterprotected


@dependency.requires('identity_api', 'policy_api', 'token_api',
                     'trust_api', 'catalog_api', 'credential_api',
                     'assignment_api')
class V2Controller(wsgi.Application):
    """Base controller class for Identity API v2."""

    def _delete_tokens_for_trust(self, user_id, trust_id):
        self.token_api.delete_tokens(user_id, trust_id=trust_id)

    def _delete_tokens_for_user(self, user_id, project_id=None):
        #First delete tokens that could get other tokens.
        self.token_api.delete_tokens(user_id, tenant_id=project_id)

        #delete tokens generated from trusts
        for trust in self.trust_api.list_trusts_for_trustee(user_id):
            self._delete_tokens_for_trust(user_id, trust['id'])
        for trust in self.trust_api.list_trusts_for_trustor(user_id):
            self._delete_tokens_for_trust(trust['trustee_user_id'],
                                          trust['id'])

    def _delete_tokens_for_project(self, project_id):
        for user_ref in self.identity_api.get_project_users(project_id):
            self._delete_tokens_for_user(user_ref['id'], project_id=project_id)

    def _require_attribute(self, ref, attr):
        """Ensures the reference contains the specified attribute."""
        if ref.get(attr) is None or ref.get(attr) == '':
            msg = '%s field is required and cannot be empty' % attr
            raise exception.ValidationError(message=msg)

    def _normalize_domain_id(self, context, ref):
        """Fill in domain_id since v2 calls are not domain-aware.

        This will overwrite any domain_id that was inadvertently
        specified in the v2 call.

        """
        ref['domain_id'] = DEFAULT_DOMAIN_ID
        return ref

    def _filter_domain_id(self, ref):
        """Remove domain_id since v2 calls are not domain-aware."""
        ref.pop('domain_id', None)
        return ref


class V3Controller(V2Controller):
    """Base controller class for Identity API v3.

    Child classes should set the ``collection_name`` and ``member_name`` class
    attributes, representing the collection of entities they are exposing to
    the API. This is required for supporting self-referential links,
    pagination, etc.

    """

    collection_name = 'entities'
    member_name = 'entity'

    def _delete_tokens_for_group(self, group_id):
        user_refs = self.identity_api.list_users_in_group(group_id)
        for user in user_refs:
            self._delete_tokens_for_user(user['id'])

    @classmethod
    def base_url(cls, path=None):
        endpoint = CONF.public_endpoint % CONF

        # allow a missing trailing slash in the config
        if endpoint[-1] != '/':
            endpoint += '/'

        url = endpoint + 'v3'

        if path:
            return url + path
        else:
            return url + '/' + cls.collection_name

    @classmethod
    def _add_self_referential_link(cls, ref):
        ref.setdefault('links', {})
        ref['links']['self'] = cls.base_url() + '/' + ref['id']

    @classmethod
    def wrap_member(cls, context, ref):
        cls._add_self_referential_link(ref)
        return {cls.member_name: ref}

    @classmethod
    def wrap_collection(cls, context, refs, filters=[], query_string=None):
        """Wrap a collection, checking for filtering and pagination.

        Returns the wrapped collection, which includes:
        - Executing any filtering not already carried out
        - Paginating if necessary
        - Adds 'self' links in every member
        - Adds 'next', 'self' and 'prev' links for the whole collection.

        :param context: the current context, containing the original url path
                        and query string
        :param refs: the list of members of the collection
        :param filters: list of valid keys to apply filtering to
        :param query_string: modified query string that has any filters already
                             handled removed. If this is not present, this
                             implies no filtering has yet been done.

        """
        def build_url(path, query_dict, increment, ref_count):
            """Build a collection link.

            Build and return one of the prev, self, next links, based on:

            - the path provided
            - the current page specified in query_dict
            - the page increment we want (-1 is previous, 0 is self and
              +1 is next)
            - ref-count, the number of entries in this page, which compared to
              per_page to determine if we have a full page.

            If page is not specified in query-dict, then we are not paginating
            and previous and next should return None

            """
            if query_dict is not None and 'page' in query_dict:
                new_dict = update_page_in_query(query_dict, increment,
                                                ref_count)
                if new_dict is not None:
                    query_list = []
                    for x in new_dict:
                        query_list.append('%s=%s' % (x, new_dict[x]))
                    query_string = '&'.join(query_list)
                    new_path = '%(path)s?%(query_string)s' % {
                        'path': path,
                        'query_string': query_string}
                    return cls.base_url(new_path)
                else:
                    # We are paginating but have run off the start or end
                    return None
            else:
                # We are not paginating, so only the self link is required
                if increment == 0:
                    return cls.base_url(path)
                else:
                    return None

        def update_page_in_query(query_dict, increment, ref_count):
            """Return a new dict with the page number updated.

            Given current page number in query_dict, return an new, updated
            dict based on the page increment required.

            Return None if we have run off the start or end.

            """
            # We have already validates that any specified page or page size
            # are integers, so not need to check for TypeError
            page = query_dict.get('page')
            per_page = int(query_dict.get('per_page', 30))
            if page is None:
                # A query string of 'page=' is interpreted as page 1
                page = 1
            else:
                page = int(page)

            new_dict = query_dict.copy()
            page += increment
            new_dict['page'] = page

            # If the prev page is less than 1 or there is no next page
            # since we did not have a full page this time, then indicate
            # we should return a None url to the caller.
            #
            # This algorithm obviously does mean that in the case of the
            # last page being exactly full, we will incorrectly include
            # a next pointer.  However, that small issue avoids the need
            # for a look ahead read being percolated up from the driver
            # layer and is considered a reasonable trade-off.
            if page < 1 or (ref_count != per_page and increment == 1):
                return None
            else:
                return new_dict

        # If query_string was not specified, then this implies the driver has
        # not done any filtering at all, and we should just use the original
        # context query string.
        #
        # If driver layer did do some filtering, then it will have removed
        # any filters that it supported from 'query_string', so we now check
        # if there are any that it did not handle.  The driver will not have
        # paginated or limited the output if it found there were filters it
        # was unable to handle.

        if query_string is None:
            query_string = context['query_string']
        for f in filters:
            refs = cls._filter_by_attribute(query_string, refs, f)

        # This is safe whether the driver paginated or not, since
        # it will only take action if more than a page size has been
        # returned
        refs = cls.paginate(context, refs)

        for ref in refs:
            cls.wrap_member(context, ref)

        container = {cls.collection_name: refs}
        container['links'] = {
            'next': build_url(context['path'], context['query_string'],
                              1, len(refs)),
            'self': build_url(context['path'], context['query_string'],
                              0, len(refs)),
            'previous': build_url(context['path'], context['query_string'],
                                  -1, len(refs))}
        return container

    @classmethod
    def paginate(cls, context, refs):
        """Paginates a list of references, if not already done by the diver."""

        # Load and validate the page and page_size
        try:
            per_page = int(context['query_string'].get('per_page', 30))
            if 'page' in context['query_string']:
                page = context['query_string'].get('page')
                if page is None:
                    # A query string of 'page=' is interpreted as page 1
                    page = 1
                else:
                    page = int(page)
        except TypeError:
            raise exception.ValidationError(
                _('Page and page size must be an integer'))

        if len(refs) > per_page:
            # The driver returned more than a page size, so must be incapable
            # of pagination, so we must do it on its behalf, provided the
            # client has indicated they want this.
            if 'page' in context['query_string']:
                return refs[per_page * (page - 1):per_page * page]
        return refs

    @classmethod
    def filter_by_attribute(cls, context, refs, attr):
        """Filters a list of references by context query string value."""
        return cls._filter_by_attribute(cls, context['query_string'],
                                        refs, attr)

    @classmethod
    def _filter_by_attribute(cls, query_string, refs, attr):
        """Filters a list of references by query string value."""

        def _attr_match(ref_attr, val_attr):
            """Matches attributes allowing for booleans as strings.

            We test explicitly for a value that defines it as 'False',
            which also means that the existence of the attribute with
            no value implies 'True'

            """
            if type(ref_attr) is bool:
                return (ref_attr == utils.attr_as_boolean(val_attr))
            else:
                return (ref_attr == val_attr)

        if attr in query_string:
            value = query_string[attr]
            return [r for r in refs if _attr_match(
                flatten(r).get(attr), value)]
        return refs

    def _require_matching_id(self, value, ref):
        """Ensures the value matches the reference's ID, if any."""
        if 'id' in ref and ref['id'] != value:
            raise exception.ValidationError('Cannot change ID')

    def _assign_unique_id(self, ref):
        """Generates and assigns a unique identifer to a reference."""
        ref = ref.copy()
        ref['id'] = uuid.uuid4().hex
        return ref

    def _get_domain_id_for_request(self, context):
        """Get the domain_id for a v3 call."""

        if context['is_admin']:
            return DEFAULT_DOMAIN_ID

        # Fish the domain_id out of the token
        #
        # We could make this more efficient by loading the domain_id
        # into the context in the wrapper function above (since
        # this version of normalize_domain will only be called inside
        # a v3 protected call).  However, this optimization is probably not
        # worth the duplication of state
        try:
            token_ref = self.token_api.get_token(context['token_id'])
        except exception.TokenNotFound:
            LOG.warning(_('Invalid token in _get_domain_id_for_request'))
            raise exception.Unauthorized()

        if 'domain' in token_ref:
            return token_ref['domain']['id']
        else:
            return DEFAULT_DOMAIN_ID

    def _normalize_domain_id(self, context, ref):
        """Fill in domain_id if not specified in a v3 call."""
        if 'domain_id' not in ref:
            ref['domain_id'] = self._get_domain_id_for_request(context)
        return ref

    def _filter_domain_id(self, ref):
        """Override v2 filter to let domain_id out for v3 calls."""
        return ref
