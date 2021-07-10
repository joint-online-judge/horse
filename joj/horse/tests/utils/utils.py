import random
import string
from typing import Any, Dict

from fastapi_jwt_auth import AuthJWT

from joj.horse.models.user import User
from joj.horse.utils.auth import auth_jwt_encode


def random_lower_string(length: int = 32) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=length))


def random_bool() -> bool:
    return bool(random.randint(0, 1))


def random_student_id() -> str:
    return f"5{random.randint(0,99):02}370910{random.randint(0,999):03}"


def random_ip() -> str:
    return ".".join(map(str, (random.randint(0, 255) for _ in range(4))))


async def create_test_user() -> User:
    user = await User.login_by_jaccount(
        random_student_id(), random_lower_string(), random_lower_string(), random_ip()
    )
    assert user is not None
    return user


def get_base_url(module: Any) -> str:
    return module.router_prefix + (
        "/" + module.router_name if module.router_name else ""
    )


def generate_auth_headers(user: User) -> Dict[str, str]:
    access_jwt = auth_jwt_encode(auth_jwt=AuthJWT(), user=user, channel="jaccount")
    return {"Authorization": f"Bearer {access_jwt}"}
