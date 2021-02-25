from joj.horse import app
from joj.horse.apis import domain, misc, problem, user, users


def include_router(module):
    app.include_router(
        module.router,
        prefix=module.router_prefix
        + ("/" + module.router_name if module.router_name else ""),
        tags=[module.router_tag],
    )


include_router(misc)
include_router(domain)
include_router(problem)
include_router(user)
include_router(users)
