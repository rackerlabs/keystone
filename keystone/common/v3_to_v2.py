#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Helper functions for v3 -> v2 conversions."""

from keystone.i18n import _


def filter_domain_id(ref):
    """Remove domain_id since v2 calls are not domain-aware."""
    ref.pop('domain_id', None)
    return ref


def filter_domain(ref):
    """Remove domain since v2 calls are not domain-aware."""
    ref.pop('domain', None)
    return ref


def filter_project_parent_id(ref):
    """Remove parent_id since v2 calls are not hierarchy-aware."""
    ref.pop('parent_id', None)
    return ref


def filter_is_domain(ref):
    """Remove is_domain field since v2 calls are not domain-aware."""
    ref.pop('is_domain', None)
    return ref


def normalize_username_in_response(ref):
    """Adds username to outgoing user refs to match the v2 spec.

    Internally we use `name` to represent a user's name. The v2 spec
    requires the use of `username` instead.

    """
    if 'username' not in ref and 'name' in ref:
        ref['username'] = ref['name']
    return ref


def normalize_username_in_request(ref):
    """Adds name in incoming user refs to match the v2 spec.

    Internally we use `name` to represent a user's name. The v2 spec
    requires the use of `username` instead.

    """
    if 'name' not in ref and 'username' in ref:
        ref['name'] = ref.pop('username')
    return ref


def convert_user(ref):
    """Convert a user_ref from v3 to v2 compatible.

    * v2.0 users are not domain aware, and should have domain_id removed
    * v2.0 users expect the use of tenantId instead of default_project_id
    * v2.0 users have a username attribute

    If ref is a list type, we will iterate through each element and do the
    conversion.
    """
    def _format_default_project_id(ref):
        """Convert default_project_id to tenantId for v2 calls."""
        default_project_id = ref.pop('default_project_id', None)
        if default_project_id is not None:
            ref['tenantId'] = default_project_id
        elif 'tenantId' in ref:
            # NOTE(morganfainberg): To avoid v2.0 confusion if somehow a
            # tenantId property sneaks its way into the extra blob on the
            # user, we remove it here.  If default_project_id is set, we
            # would override it in either case.
            del ref['tenantId']

    def _normalize_and_filter_user_properties(ref):
        """Run through the various filter/normalization methods."""
        _format_default_project_id(ref)
        filter_domain(ref)
        filter_domain_id(ref)
        normalize_username_in_response(ref)
        return ref

    if isinstance(ref, dict):
        return _normalize_and_filter_user_properties(ref)
    elif isinstance(ref, list):
        return [_normalize_and_filter_user_properties(x) for x in ref]
    else:
        raise ValueError(_('Expected dict or list: %s') % type(ref))


def convert_project(ref):
    """Convert a project_ref from v3 to v2.

    * v2.0 projects are not domain aware, and should have domain_id removed
    * v2.0 projects are not hierarchy aware, and should have parent_id
      removed

    This method should only be applied to project_refs being returned from
    the v2.0 controller(s).

    If ref is a list type, we will iterate through each element and do the
    conversion.
    """
    def _filter_project_properties(ref):
        """Run through the various filter methods."""
        filter_domain_id(ref)
        filter_project_parent_id(ref)
        filter_is_domain(ref)
        return ref

    if isinstance(ref, dict):
        return _filter_project_properties(ref)
    elif isinstance(ref, list):
        return [_filter_project_properties(x) for x in ref]
    else:
        raise ValueError(_('Expected dict or list: %s') % type(ref))
