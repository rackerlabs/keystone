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

"""Configuration options for Kubernetes token authentication."""

from oslo_config import cfg

from keystone.conf import utils

enabled = cfg.BoolOpt(
    'enabled',
    default=False,
    help=utils.fmt("""
Enable the Kubernetes token authentication middleware. When enabled,
Keystone can validate Kubernetes bearer tokens (both JWT service-account
tokens and opaque OpenShift OAuth tokens) for federation authentication.
"""))

k8s_api_url = cfg.StrOpt(
    'k8s_api_url',
    default='https://kubernetes.default.svc',
    help=utils.fmt("""
URL of the Kubernetes API server. Defaults to the in-cluster service
address. Used for JWKS fetching and TokenReview API calls.
"""))

ca_path = cfg.StrOpt(
    'ca_path',
    default='/var/run/secrets/kubernetes.io/serviceaccount/ca.crt',
    help=utils.fmt("""
Path to the CA certificate bundle for verifying TLS connections to the
Kubernetes API server. Defaults to the in-cluster CA bundle.
"""))

verify_ssl = cfg.BoolOpt(
    'verify_ssl',
    default=True,
    help=utils.fmt("""
Whether to verify TLS certificates when connecting to the Kubernetes
API server. Should be True in production; may be set to False for
development with self-signed certificates.
"""))

claim_prefix = cfg.StrOpt(
    'claim_prefix',
    default='OIDC-',
    help=utils.fmt("""
Prefix for WSGI environment variables populated by this middleware.
The default 'OIDC-' matches what mod_auth_openidc uses, so existing
federation mapping rules work without modification.
"""))

oauth_client_id = cfg.StrOpt(
    'oauth_client_id',
    help=utils.fmt("""
OAuth client ID registered with the OpenShift OAuth server. Required
for the websso browser login flow. Create an OAuthClient resource in
OpenShift and set its name here.
"""))

oauth_client_secret = cfg.StrOpt(
    'oauth_client_secret',
    secret=True,
    help=utils.fmt("""
OAuth client secret for the OpenShift OAuth server. Required for the
websso browser login flow.
"""))

oauth_authorize_url = cfg.StrOpt(
    'oauth_authorize_url',
    help=utils.fmt("""
OpenShift OAuth authorization endpoint URL. Typically
``https://oauth-openshift.apps.<cluster>/oauth/authorize``.
Required for the websso browser login flow.
"""))

oauth_token_url = cfg.StrOpt(
    'oauth_token_url',
    help=utils.fmt("""
OpenShift OAuth token endpoint URL. Typically
``https://oauth-openshift.apps.<cluster>/oauth/token``.
Required for the websso browser login flow.
"""))

GROUP_NAME = __name__.split('.')[-1]
ALL_OPTS = [
    enabled,
    k8s_api_url,
    ca_path,
    verify_ssl,
    claim_prefix,
    oauth_client_id,
    oauth_client_secret,
    oauth_authorize_url,
    oauth_token_url,
]


def register_opts(conf):
    conf.register_opts(ALL_OPTS, group=GROUP_NAME)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}
