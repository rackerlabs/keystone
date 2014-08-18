from keystone.common import validation
from keystone.common.validation import parameter_types


_user_properties = {
    'name': parameter_types.name,
    'enabled': parameter_types.boolean,
    'email': parameter_types.email,
    'password': parameter_types.password,
    'description': parameter_types.description,
    'default_project_id': parameter_types.id_string,
    'domain_id': parameter_types.id_string
}

user_create = {
    'type': 'object',
    'properties': _user_properties,
    'required': ['name'],
    'additionalProperties': True,
}

user_update = {
    'type': 'object',
    'properties': _user_properties,
    'additionalProperties': True,
}
