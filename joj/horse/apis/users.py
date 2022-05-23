from typing import cast

from fastapi import Depends
from loguru import logger

from joj.horse import models, schemas
from joj.horse.schemas import StandardResponse
from joj.horse.schemas.auth import Authentication
from joj.horse.utils.fastapi.router import MyRouter
from joj.horse.utils.parser import parse_uid

router = MyRouter()
router_name = "users"
router_tag = "user"


@router.get("/me")
async def get_current_user(
    auth: Authentication = Depends(),
) -> StandardResponse[schemas.UserDetail]:
    user = await parse_uid(cast(schemas.UserID, auth.jwt.id), auth)
    return StandardResponse(user)


@router.patch("/me")
async def update_current_user(
    user_edit: schemas.UserEdit = Depends(schemas.UserEdit.edit_dependency),
    auth: Authentication = Depends(),
) -> StandardResponse[schemas.UserDetail]:
    user = await parse_uid(cast(schemas.UserID, auth.jwt.id), auth)
    user.update_from_dict(user_edit.dict())
    logger.info(f"update user: {user}")
    await user.save_model()
    return StandardResponse(user)


@router.patch("/me/password")
async def change_password(
    user_reset_password: schemas.UserResetPassword,
    auth: Authentication = Depends(),
) -> StandardResponse[schemas.UserDetail]:
    user = await parse_uid(cast(schemas.UserID, auth.jwt.id), auth)
    await user.reset_password(
        user_reset_password.current_password,
        user_reset_password.new_password,
    )
    return StandardResponse(user)


@router.get("/{uid}")
async def get_user(
    user: models.User = Depends(parse_uid),
) -> StandardResponse[schemas.UserPreview]:
    return StandardResponse(user)
