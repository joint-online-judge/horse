from sanic import Sanic
from sanic.response import json

from spf import SanicPluginsFramework
from sanic_restplus import Api
from sanic_restplus.restplus import restplus

from typing import Optional

from joj.horse.utils.fastapi import FastAPI
from joj.horse.utils.session import SessionMiddleware


app = FastAPI()

app.add_middleware(SessionMiddleware)


import joj.horse.apis





# app = Sanic("joj-horse")
# spf = SanicPluginsFramework(app)
#
# # register rest api plugin in /api/v1 (note: no trailing /)
# rest_assoc = spf.register_plugin(restplus)
# api = Api(version='1.0', title='JOJ API', description='JOJ Simple API',
#           prefix='/api/v1', doc='/api/v1')
#
# import joj.horse.apis
#
# rest_assoc.api(api)
