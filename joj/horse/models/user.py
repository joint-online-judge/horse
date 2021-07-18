from typing import List, Optional, Type

from pydantic import EmailStr
from tortoise import BaseDBAsyncClient, fields, signals, timezone
from uvicorn.config import logger

from joj.horse.models.base import BaseORMModel
from joj.horse.models.permission import DefaultRole


class User(BaseORMModel):
    class Meta:
        table = "users"
        unique_together = [
            ("scope", "uname_lower"),
            ("scope", "mail_lower"),
        ]

    id = fields.UUIDField(pk=True)

    scope = fields.CharField(max_length=255)
    uname = fields.CharField(max_length=255)
    mail = fields.CharField(max_length=255)

    uname_lower = fields.CharField(max_length=255)
    mail_lower = fields.CharField(max_length=255)
    gravatar = fields.CharField(max_length=255)

    student_id = fields.CharField(default="", max_length=255)
    real_name = fields.CharField(default="", max_length=255)

    salt = fields.CharField(default="", max_length=255)
    hash = fields.CharField(default="", max_length=255)
    role = fields.CharField(default=str(DefaultRole.USER), max_length=255)

    # register_at = fields.DatetimeField(auto_now_add=True)
    register_ip = fields.CharField(default="0.0.0.0", max_length=255)
    login_at = fields.DatetimeField(auto_now_add=True)
    login_ip = fields.CharField(default="0.0.0.0", max_length=255)

    @classmethod
    async def find_by_uname(cls, scope: str, uname: str) -> Optional["User"]:
        return await User.get_or_none(scope=scope, uname_lower=uname.strip().lower())

    @classmethod
    async def login_by_jaccount(
        cls, student_id: str, jaccount_name: str, real_name: str, ip: str
    ) -> Optional["User"]:
        scope = "sjtu"
        try:
            user = await cls.find_by_uname(scope=scope, uname=jaccount_name)
            if user:
                user.login_at = timezone.now()
                user.login_ip = ip
            else:
                user = User(
                    scope=scope,
                    uname=jaccount_name,
                    mail=EmailStr(jaccount_name + "@sjtu.edu.cn"),
                    student_id=student_id,
                    real_name=real_name,
                    register_ip=ip,
                    login_timestamp=timezone.now(),
                    login_ip=ip,
                )
            await user.save()
            return user
        except Exception as e:
            logger.exception(e)
            return None


@signals.pre_save(User)
async def user_pre_save(
    sender: "Type[User]",
    instance: User,
    using_db: "Optional[BaseDBAsyncClient]",
    update_fields: List[str],
) -> None:
    instance.uname_lower = instance.uname.strip().lower()
    instance.mail_lower = instance.mail.strip().lower()
    if not instance.gravatar:
        instance.gravatar = instance.mail_lower


# @instance.register
# class User(DocumentMixin, MotorAsyncIODocument):
#     class Meta:
#         collection_name = "users"
#         indexes = [
#             IndexModel([("scope", ASCENDING), ("uname_lower", ASCENDING)], unique=True),
#             IndexModel([("scope", ASCENDING), ("mail_lower", ASCENDING)], unique=True),
#         ]
#         strict = False
#
#     scope = fields.StringField(required=True)
#     uname = fields.StringField(required=True)
#     mail = fields.EmailField(required=True)
#
#     uname_lower = fields.StringField(required=True)
#     mail_lower = fields.StringField(required=True)
#     gravatar = fields.StringField(required=True)
#
#     student_id = fields.StringField(default="")
#     real_name = fields.StringField(default="")
#
#     salt = fields.StringField(default="")
#     hash = fields.StringField(default="")
#     role = fields.StringField(default="user")
#
#     register_timestamp = fields.DateTimeField(required=True)
#     register_ip = fields.StringField(default="0.0.0.0")
#     login_timestamp = fields.DateTimeField(required=True)
#     login_ip = fields.StringField(default="0.0.0.0")
#
