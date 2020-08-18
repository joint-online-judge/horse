from joj.horse import app

import joj.horse.apis.user
import joj.horse.apis.misc


def include_router(module):
    app.include_router(module.router, prefix=module.router_prefix + '/' + module.router_name, tags=[module.router_name])


include_router(user)
include_router(misc)
