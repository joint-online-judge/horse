from sanic import Sanic

from spf import SanicPluginsFramework
from sanic_restplus import Api, Resource, fields
from sanic_restplus.restplus import restplus

app = Sanic("joj-horse")
spf = SanicPluginsFramework(app)

# register rest api plugin in /api/v1 (note: no trailing /)
rest_assoc = spf.register_plugin(restplus)
api = Api(version='1.0', title='JOJ API', description='JOJ Simple API',
          prefix='/api/v1', doc='/api/v1')

import joj.horse.apis

rest_assoc.api(api)
