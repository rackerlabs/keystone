

class SwaggerDoc(dict):
    def __init__(self):
        super(SwaggerDoc, self).__init__()
        self.update({
            'swagger': '2.0',
            'info': {
                'title': 'OpenStack Identity API V3',
                'version': '3.6',
            },
            'paths': {}
        })

    def register_path(self, path, pathitem):
        self['paths'][path] = pathitem


SWAGGER_DOC = SwaggerDoc()
