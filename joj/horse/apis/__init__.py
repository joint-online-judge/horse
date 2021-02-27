from joj.horse import app
from joj.horse.apis import domains, misc, problem_sets, problems, records, user, users


def include_router(module):
    app.include_router(
        module.router,
        prefix=module.router_prefix
        + ("/" + module.router_name if module.router_name else ""),
        tags=[module.router_tag],
    )


include_router(misc)
include_router(domains)
include_router(problems)
include_router(problem_sets)
include_router(records)
include_router(user)
include_router(users)
