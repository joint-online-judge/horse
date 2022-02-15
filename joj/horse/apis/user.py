from fastapi import Depends
from loguru import logger

from joj.horse import schemas
from joj.horse.schemas import StandardResponse
from joj.horse.schemas.auth import Authentication
from joj.horse.utils.parser import parse_uid
from joj.horse.utils.router import MyRouter

router = MyRouter()
router_name = "user"
router_tag = "user"
router_prefix = "/api/v1"


@router.get("")
async def get_current_user(
    auth: Authentication = Depends(),
) -> StandardResponse[schemas.UserDetail]:
    user = await parse_uid(auth.jwt.id, auth)
    return StandardResponse(user)


@router.patch("")
async def update_current_user(
    user_edit: schemas.UserEdit = Depends(schemas.UserEdit.edit_dependency),
    auth: Authentication = Depends(),
) -> StandardResponse[schemas.User]:
    user = await parse_uid(auth.jwt.id, auth)
    user.update_from_dict(user_edit.dict())
    logger.info(f"update user: {user}")
    await user.save_model()
    return StandardResponse(user)


# @router.get("/problems")
# async def get_current_user_problems(
#     query: schemas.PaginationQuery = Depends(parse_pagination_query),
#     auth: Authentication = Depends(),
# ) -> StandardListResponse[schemas.Problem]:
#     condition = {"owner": auth.jwt.id}
#     cursor = models.Problem.cursor_find(condition, query)
#     res = await models.Problem.to_list(cursor)
#     return StandardListResponse(res)


@router.patch("/password")
async def change_password(
    user_reset_password: schemas.UserResetPassword,
    auth: Authentication = Depends(),
) -> StandardResponse[schemas.User]:
    user = await parse_uid(auth.jwt.id, auth)
    await user.reset_password(
        user_reset_password.current_password,
        user_reset_password.new_password,
    )
    return StandardResponse(user)
