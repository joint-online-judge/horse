from typing import Any, List

from joj.horse.apis import (
    admin as admin,
    auth as auth,
    domains as domains,
    judge as judge,
    misc as misc,
    problem_configs as problem_configs,
    problem_groups as problem_groups,
    problem_sets as problem_sets,
    problems as problems,
    records as records,
    users as users,
)
from joj.horse.apis.auth import login
from joj.horse.apis.problem_configs import update_problem_config_by_archive
from joj.horse.apis.problem_sets import submit_solution_to_problem_set
from joj.horse.apis.problems import submit_solution_to_problem
from joj.horse.app import app
from joj.horse.utils.fastapi.router import copy_schema, update_schema_name

modules: List[Any] = [
    domains,
    problem_sets,
    problems,
    problem_configs,
    problem_groups,
    records,
    users,
    auth,
    misc,
    admin,
    judge,
]
for module in modules:
    app.include_router(
        module.router,
        prefix="/" + module.router_name if module.router_name else "",
        tags=[module.router_tag],
    )


update_schema_name(app, submit_solution_to_problem, "ProblemSolutionSubmit")
copy_schema(app, submit_solution_to_problem, submit_solution_to_problem_set)
update_schema_name(app, update_problem_config_by_archive, "FileUpload")
update_schema_name(app, login, "OAuth2PasswordRequestForm")
