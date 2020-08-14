from sanic_restplus import Api, Resource, fields

from joj.horse import api

ns = api.namespace('user', description='user operations')


@ns.route('/login')
class UserLogin(Resource):
    async def get(self, request):
        return 'login'
