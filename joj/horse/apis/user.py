from sanic_restplus import Resource
from webargs import fields

from joj.horse.utils.api import create_namespace, Locations

ns = create_namespace('user', description='user operations')


@ns.route('/login')
class UserLogin(Resource):

    @ns.argument('uid', fields.Int(required=True), Locations.QUERY, 'User ID')
    async def get(self, request, args):
        print(args)
        return request.json
