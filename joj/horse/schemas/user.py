import re

# from joj.horse.models.permission import DefaultRole

# from joj.horse.schemas import BaseModel

# from joj.horse.schemas.base import BaseODMSchema


UID_RE = re.compile(r"-?\d+")
UNAME_RE = re.compile(r"[^\s\u3000](.{,254}[^\s\u3000])?")

# UserList = pydantic_queryset_creator(UserModel, name="UserList")

# class UserBase(BaseODMSchema):
#     scope: str
#     uname: str
#     mail: EmailStr
#
#     uname_lower: str = ""
#     mail_lower: str = ""
#     gravatar: str = ""
#
#     student_id: str = ""
#     real_name: str = ""
#
#     @validator("uname", pre=True)
#     def validate_uname(cls, v: str) -> str:
#         if not UNAME_RE.fullmatch(v):
#             raise ValueError("uname")
#         return v
#
#     @validator("uname_lower", pre=True, always=True)
#     def default_uname_lower(
#         cls, v: str, *, values: Dict[str, str], **kwargs: Any
#     ) -> str:
#         return v or values["uname"].strip().lower()
#
#     @validator("mail_lower", pre=True, always=True)
#     def default_mail_lower(
#         cls, v: str, *, values: Dict[str, str], **kwargs: Any
#     ) -> str:
#         return v or values["mail"].strip().lower()
#
#     @validator("gravatar", pre=True, always=True)
#     def default_gravatar(cls, v: str, *, values: Dict[str, str], **kwargs: Any) -> str:
#         return v or values["mail"].strip().lower()


# class User(UserBase):
#     salt: str = ""
#     hash: str = ""
#     role: str = DefaultRole.USER
#
#     register_ip: str = "0.0.0.0"
#     login_ip: str = "0.0.0.0"
#
#     register_timestamp: datetime
#     login_timestamp: datetime
#
#     @validator("register_timestamp", pre=True, always=True)
#     def default_register_timestamp(cls, v: datetime) -> datetime:
#         return v or datetime.utcnow()
#
#     @validator("login_timestamp", pre=True, always=True)
#     def default_login_timestamp(cls, v: datetime) -> datetime:
#         return v or datetime.utcnow()
