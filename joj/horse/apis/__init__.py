from joj.horse import app
from joj.horse.apis import domain, misc, user, problem


def include_router(module):
    app.include_router(
        module.router,
        prefix=module.router_prefix + "/" + module.router_name,
        tags=[module.router_name],
    )


include_router(domain)
include_router(misc)
include_router(user)
include_router(problem)
