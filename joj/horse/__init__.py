from sanic import Sanic
from sanic.response import json

from spf import SanicPluginsFramework
from sanic_restplus import Api
from sanic_restplus.restplus import restplus

app = Sanic("joj-horse")
spf = SanicPluginsFramework(app)

# register rest api plugin in /api/v1 (note: no trailing /)
rest_assoc = spf.register_plugin(restplus)
api = Api(version='1.0', title='JOJ API', description='JOJ Simple API',
          prefix='/api/v1', doc='/api/v1')

import joj.horse.apis

from webargs_sanic.sanicparser import use_kwargs, use_args
from webargs import fields


@app.route("/test", methods=["POST"])
@use_args({'uid': fields.Int()}, location="headers")
async def test(request, args):
    print(args)
    return json({"hello": "world"})


rest_assoc.api(api)
