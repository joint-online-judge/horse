import pytest

from joj.horse import apis, models
from joj.horse.tests.utils.utils import get_base_url, parametrize_global_problem_sets

base_user_url = get_base_url(apis.users)


@pytest.mark.asyncio
@pytest.mark.depends(name="TestProblemSetCreate", on=["TestDomainCreate"])
class TestProblemSetCreate:
    @parametrize_global_problem_sets
    async def test_global_problem_sets(self, problem_set: models.ProblemSet) -> None:
        pass
