import pytest

from joj.horse import apis, models
from joj.horse.tests.utils.utils import get_base_url, parametrize_global_problems

base_user_url = get_base_url(apis.users)


@pytest.mark.asyncio
@pytest.mark.depends(name="TestProblemCreate", on=["TestProblemSetCreate"])
class TestProblemCreate:
    @parametrize_global_problems
    async def test_global_problems(self, problem: models.Problem) -> None:
        pass
