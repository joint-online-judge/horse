from joj.horse.models.user import User


async def create_test_user() -> User:
    user = await User.login_by_jaccount(
        "500370910000", "test_jaccount_name", "real_name", "0.0.0.0"
    )
    assert user is not None
    return user
