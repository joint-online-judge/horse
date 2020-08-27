from joj.horse import app

import joj.horse.apis.domain
import joj.horse.apis.misc
import joj.horse.apis.user


def include_router(module):
    app.include_router(module.router, prefix=module.router_prefix + '/' + module.router_name, tags=[module.router_name])


include_router(domain)
include_router(misc)
include_router(misc)
