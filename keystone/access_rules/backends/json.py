# Copyright 2019 SUSE Linux GmbH
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

import re

from oslo_log import log
from oslo_serialization import jsonutils

from keystone.access_rules.backends import base
import keystone.conf
from keystone import exception

CONF = keystone.conf.CONF
LOG = log.getLogger(__name__)


class AccessRules(base.AccessRulesDriverBase):
    """This backend reads the access rules from a JSON file on disk.

    The format of the file is a mapping from service type to rules for that
    service type. For example:

    {
        "identity": [
            {
                "request_path": "/v3/users",
                "request_method": "GET",
                "allow_chained": false
            },
            {
                "request_path": "/v3/users",
                "request_method": "POST",
                "allow_chained": false
            },
            {
                "request_path": "/v3/users/*",
                "request_method": "GET",
                "allow_chained": false
            },
            {
                "request_path": "/v3/users/*",
                "request_method": "PATCH",
                "allow_chained": false
            },
            {
                "request_path": "/v3/users/*",
                "request_method": "DELETE",
                "allow_chained": false
            }
            ...
        ],
        "image": [
            {
                "request_path": "/v2/images",
                "request_method": "GET",
                "allow_chained": true
            },
            ...
        ],
        ...
    }

    This will be transmuted in memory to a hash map that looks like this:
    {
        "identity": {
            "GET": [
                {
                    "request_path": "/v3/users",
                    "allow_chained": false,
                },
                {
                    "request_path": "/v3/users/*",
                    "allow_chained": false,
                }
                ...
            ],
            "POST": [ ... ]
        },
        ...
    }

    The request_path may include a wildcard like '*' or '**'. A capability
    validation request for a path like "/v3/users/uuid" will match with an
    access rule like "/v3/users/*", and a request for a path like
    "/v3/users/uuid/application_credentials/uuid" will match with an access
    rule like "/v3/users/**".

    """

    def __init__(self):
        super(AccessRules, self).__init__()
        if CONF.access_rules.permissive:
            return
        access_rules_file = CONF.access_rules.rules_file
        self.access_rules = dict()
        self.access_rules_json = dict()
        try:
            with open(access_rules_file, "rb") as f:
                self.access_rules_json = jsonutils.load(f)
        except IOError:
            LOG.warning('No file found for access rules, application'
                        ' credential capabilities will be unavailable.')
            return
        except ValueError as e:
            raise exception.AccessRulesFileError(error=e)

        for service, rules in self.access_rules_json.items():
            self.access_rules[service] = dict()
            for rule in rules:
                try:
                    request_path_regex = self._convert_path(
                        rule['request_path'])
                    self.access_rules[service].setdefault(
                        rule['request_method'], []).append({
                            'request_path': request_path_regex,
                            'allow_chained': rule['allow_chained']
                        })
                except KeyError as e:
                    raise exception.AccessRulesFileError(error=e)

    def _convert_path(self, path):
        # The fnmatch module doesn't provide the ability to match * versus **,
        # so convert to regex.
        # replace * with [^\/]* (all except /)
        pattern = r'([^\*])\*($|[^\*])'
        replace = r'\1[^\/]**\2'
        request_path_regex = re.sub(pattern, replace, path)
        # replace ** with .*
        pattern = r'\*\*'
        replace = '.*'
        request_path_regex = re.sub(pattern, replace, request_path_regex)
        return request_path_regex

    def list_access_rules(self, service=None):
        """List access rules in human readable form."""
        if service:
            if service not in self.access_rules_json:
                raise exception.AccessRulesNotFound(service=service)
            return {service: self.access_rules_json[service]}
        return self.access_rules_json

    def check_access_rule(self, service, request_path, request_method,
                          allow_chained):
        """Check if an access rule exists."""
        if (service in self.access_rules
                and request_method in self.access_rules[service]):
            rules = self.access_rules[service][request_method]
            for rule in rules:
                pattern = r'^%s$' % rule['request_path']
                if (re.match(pattern, request_path)
                        and rule['allow_chained'] == allow_chained):
                    return True
        return False
