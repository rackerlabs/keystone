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

import sys

from oslo_config import cfg
from oslo_log import versionutils

from keystone.conf import utils


bind = cfg.ListOpt(
    'bind',
    default=[],
    help=utils.fmt("""
This is a list of external authentication mechanisms which should add token
binding metadata to tokens, such as `kerberos` or `x509`. Binding metadata is
enforced according to the `[token] enforce_token_bind` option.
"""))

enforce_token_bind = cfg.StrOpt(
    'enforce_token_bind',
    default='permissive',
    deprecated_since=versionutils.deprecated.PIKE,
    deprecated_for_removal=True,
    help=utils.fmt("""
This controls the token binding enforcement policy on tokens presented to
keystone with token binding metadata (as specified by the `[token] bind`
option). `disabled` completely bypasses token binding validation. `permissive`
and `strict` do not require tokens to have binding metadata (but will validate
it if present), whereas `required` will always demand tokens to having binding
metadata. `permissive` will allow unsupported binding metadata to pass through
without validation (usually to be validated at another time by another
component), whereas `strict` and `required` will demand that the included
binding metadata be supported by keystone.
"""))

expiration = cfg.IntOpt(
    'expiration',
    default=3600,
    min=0,
    max=sys.maxsize,
    help=utils.fmt("""
The amount of time that a token should remain valid (in seconds). Drastically
reducing this value may break "long-running" operations that involve multiple
services to coordinate together, and will force users to authenticate with
keystone more frequently. Drastically increasing this value will increase load
on the `[token] driver`, as more tokens will be simultaneously valid. Keystone
tokens are also bearer tokens, so a shorter duration will also reduce the
potential security impact of a compromised token.
"""))

provider = cfg.StrOpt(
    'provider',
    default='fernet',
    help=utils.fmt("""
Entry point for the token provider in the `keystone.token.provider` namespace.
The token provider controls the token construction, validation, and revocation
operations. Keystone includes `fernet` and `uuid` token
providers. `uuid` tokens must be persisted (using the backend specified in the
`[token] driver` option), but do not require any extra configuration or setup.
`fernet` tokens do not need to be persisted at all, but require that you run
`keystone-manage token_setup` (also see the `keystone-manage token_rotate`
command).
"""))

key_repository = cfg.StrOpt(
    'key_repository',
    default='/etc/keystone/token-keys/',
    deprecated_opts=[cfg.DeprecatedOpt('key_repository',
                                       group='fernet_tokens')],
    help=utils.fmt("""
Directory containing token keys. This directory must exist before using
`keystone-manage token_setup` for the first time, must be writable by the user
running `keystone-manage token_setup` or `keystone-manage token_rotate`, and
of course must be readable by keystone's server process. The repository may
contain keys in one of three states: a single staged key (always index 0) used
for token validation, a single primary key (always the highest index) used for
token creation and validation, and any number of secondary keys (all other
index values) used for token validation. With multiple keystone nodes, each
node must share the same key repository contents, with the exception of the
staged key (index 0). It is safe to run `keystone-manage token_rotate` once on
any one node to promote a staged key (index 0) to be the new primary
(incremented from the previous highest index), and produce a new staged key (a
new key with index 0); the resulting repository can then be atomically
replicated to other nodes without any risk of race conditions (for example, it
is safe to run `keystone-manage token_rotate` on host A, wait any amount of
time, create a tarball of the directory on host A, unpack it on host B to a
temporary location, and atomically move (`mv`) the directory into place on host
B). Running `keystone-manage token_rotate` *twice* on a key repository without
syncing other nodes will result in tokens that can not be validated by all
nodes.
"""))

max_active_keys = cfg.IntOpt(
    'max_active_keys',
    default=3,
    deprecated_opts=[cfg.DeprecatedOpt('max_active_keys',
                                       group='fernet_tokens')],
    min=1,
    help=utils.fmt("""
This controls how many keys are held in rotation by `keystone-manage
token_rotate` before they are discarded. The default value of 3 means that
keystone will maintain one staged key (always index 0), one primary key (the
highest numerical index), and one secondary key (every other index). Increasing
this value means that additional secondary keys will be kept in the rotation.
"""))

driver = cfg.StrOpt(
    'driver',
    default='sql',
    deprecated_since=versionutils.deprecated.PIKE,
    deprecated_for_removal=True,
    help=utils.fmt("""
Entry point for the token persistence backend driver in the
`keystone.token.persistence` namespace. Keystone provides the `sql`
driver.  The `sql` option (default) depends on the options in your
`[database]` section. If you're using the `fernet` `[token] provider`, this
backend will not be utilized to persist tokens at all.
"""))

caching = cfg.BoolOpt(
    'caching',
    default=True,
    help=utils.fmt("""
Toggle for caching token creation and validation data. This has no effect
unless global caching is enabled.
"""))

cache_time = cfg.IntOpt(
    'cache_time',
    min=0,
    max=sys.maxsize,
    help=utils.fmt("""
The number of seconds to cache token creation and validation data. This has no
effect unless both global and `[token] caching` are enabled.
"""))

revoke_by_id = cfg.BoolOpt(
    'revoke_by_id',
    default=True,
    help=utils.fmt("""
This toggles support for revoking individual tokens by the token identifier and
thus various token enumeration operations (such as listing all tokens issued to
a specific user). These operations are used to determine the list of tokens to
consider revoked. Do not disable this option if you're using the `kvs`
`[revoke] driver`.
"""))

allow_rescope_scoped_token = cfg.BoolOpt(
    'allow_rescope_scoped_token',
    default=True,
    help=utils.fmt("""
This toggles whether scoped tokens may be re-scoped to a new project or
domain, thereby preventing users from exchanging a scoped token (including
those with a default project scope) for any other token. This forces users to
either authenticate for unscoped tokens (and later exchange that unscoped token
for tokens with a more specific scope) or to provide their credentials in every
request for a scoped token to avoid re-scoping altogether.
"""))

infer_roles = cfg.BoolOpt(
    'infer_roles',
    default=True,
    help=utils.fmt("""
This controls whether roles should be included with tokens that are not
directly assigned to the token's scope, but are instead linked implicitly to
other role assignments.
"""))

cache_on_issue = cfg.BoolOpt(
    'cache_on_issue',
    default=True,
    help=utils.fmt("""
Enable storing issued token data to token validation cache so that first token
validation doesn't actually cause full validation cycle. This option has no
effect unless global caching and token caching are enabled.
"""))

allow_expired_window = cfg.IntOpt(
    'allow_expired_window',
    default=48 * 60 * 60,
    help=utils.fmt("""
This controls the number of seconds that a token can be retrieved for beyond
the built-in expiry time. This allows long running operations to succeed.
Defaults to two days.
"""))


GROUP_NAME = __name__.split('.')[-1]
ALL_OPTS = [
    bind,
    enforce_token_bind,
    expiration,
    provider,
    key_repository,
    max_active_keys,
    driver,
    caching,
    cache_time,
    revoke_by_id,
    allow_rescope_scoped_token,
    infer_roles,
    cache_on_issue,
    allow_expired_window,
]


def register_opts(conf):
    conf.register_opts(ALL_OPTS, group=GROUP_NAME)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}
