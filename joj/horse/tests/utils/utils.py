import random
import string
from typing import Any

from joj.horse.models.user import User


def random_lower_string() -> str:
    return "".join(random.choices(string.ascii_lowercase, k=32))


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
