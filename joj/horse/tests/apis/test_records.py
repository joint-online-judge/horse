import pytest
from httpx import AsyncClient
from pytest_lazyfixture import lazy_fixture

from joj.horse import models
from joj.horse.app import app
from joj.horse.tests.utils.utils import (
    create_test_problem,
    create_test_problem_set,
    do_api_request,
    validate_test_problem,
    validate_test_problem_set,
)


@pytest.fixture(scope="module")
async def problem_set_0(
    client: AsyncClient,
    global_domain_0: models.Domain,
    global_root_user: models.User,
) -> models.ProblemSet:
    """
    A new problem set for global_domain_0. Avoid earlier interference.
    """
    title = "record_test_problem_set_0"
    data = {"title": title, "url": title}
    response = await create_test_problem_set(
        client, global_domain_0, global_root_user, data
    )
    return await validate_test_problem_set(
        response, global_domain_0, global_root_user, data
    )


@pytest.fixture(scope="module")
async def problem_0(
    client: AsyncClient,
    global_domain_0: models.Domain,
    global_root_user: models.User,
) -> models.Problem:
    """
    A new problem set for global_domain_0. Avoid earlier interference.
    """
    title = "record_test_problem_0"
    data = {"title": title, "url": title}
    response = await create_test_problem(
        client, global_domain_0, global_root_user, data
    )
    return await validate_test_problem(
        response, global_domain_0, global_root_user, data
    )


@pytest.fixture(scope="module")
async def problem_1(
    client: AsyncClient,
    global_domain_0: models.Domain,
    global_root_user: models.User,
) -> models.Problem:
    """
    A new problem set for global_domain_0. Avoid earlier interference.
    """
    title = "record_test_problem_1"
    data = {"title": title, "url": title}
    response = await create_test_problem(
        client, global_domain_0, global_root_user, data
    )
    return await validate_test_problem(
        response, global_domain_0, global_root_user, data
    )


@pytest.fixture(scope="module", autouse=True)
async def record_0(
    client: AsyncClient,
    problem_0: models.Problem,
    global_root_user: models.User,
) -> models.Record:
    """
    Record in global_domain_0, bound to (None, problem_0)
    """
    problem_config = models.ProblemConfig(
        problem_id=problem_0.id,
        committer_id=global_root_user.id,
        commit_id="commit_0",
    )
    await problem_config.save_model()
    record = models.Record(
        domain_id=problem_0.domain_id,
        problem_set_id=None,
        problem_id=problem_0.id,
        problem_config_id=problem_config.id,
        committer_id=global_root_user.id,
    )
    await record.save_model()
    return record


@pytest.fixture(scope="module", autouse=True)
async def record_1(
    client: AsyncClient,
    problem_0: models.Problem,
    problem_set_0: models.ProblemSet,
    global_root_user: models.User,
) -> models.Record:
    """
    Record in global_domain_0, bound to (problem_set_0_new, problem_0)
    """
    problem_config = models.ProblemConfig(
        problem_id=problem_0.id,
        committer_id=global_root_user.id,
        commit_id="commit_1",
    )
    await problem_config.save_model()
    record = models.Record(
        domain_id=problem_0.domain_id,
        problem_set_id=problem_set_0.id,
        problem_id=problem_0.id,
        problem_config_id=problem_config.id,
        committer_id=global_root_user.id,
    )
    await record.save_model()
    return record


@pytest.fixture(scope="module", autouse=True)
async def record_2(
    client: AsyncClient,
    problem_1: models.Problem,
    global_root_user: models.User,
) -> models.Record:
    """
    Record in global_domain_0, bound to (None, problem_1)
    """
    problem_config = models.ProblemConfig(
        problem_id=problem_1.id,
        committer_id=global_root_user.id,
        commit_id="commit_0",
    )
    await problem_config.save_model()
    record = models.Record(
        domain_id=problem_1.domain_id,
        problem_set_id=None,
        problem_id=problem_1.id,
        problem_config_id=problem_config.id,
        committer_id=global_root_user.id,
    )
    await record.save_model()
    return record


@pytest.fixture(scope="module")
async def problem_2(
    client: AsyncClient,
    global_domain_1: models.Domain,
    global_root_user: models.User,
) -> models.Problem:
    """
    Create interference for global_domain_0
    """
    title = "record_test_problem_2"
    data = {"title": title, "url": title}
    response = await create_test_problem(
        client, global_domain_1, global_root_user, data
    )
    return await validate_test_problem(
        response, global_domain_1, global_root_user, data
    )


@pytest.fixture(scope="module", autouse=True)
async def record_3(
    client: AsyncClient,
    problem_2: models.Problem,
    global_root_user: models.User,
) -> models.Record:
    """
    Record in global_domain_1, bound to (None, problem_1_new)
    """
    problem_config = models.ProblemConfig(
        problem_id=problem_2.id,
        committer_id=global_root_user.id,
        commit_id="commit_2",
    )
    await problem_config.save_model()
    record = models.Record(
        domain_id=problem_2.domain_id,
        problem_set_id=None,
        problem_id=problem_2.id,
        problem_config_id=problem_config.id,
        committer_id=global_root_user.id,
    )
    await record.save_model()
    return record


@pytest.mark.asyncio
@pytest.mark.depends(on=["TestDomainCreate"])
class TestRecordList:
    url_base = "list_records_in_domain"

    @pytest.mark.parametrize("user", [lazy_fixture("global_root_user")])
    async def test_list_records_no_filter(
        self,
        client: AsyncClient,
        user: models.User,
        global_domain_0: models.Domain,
        record_0: models.Record,
        record_1: models.Record,
        record_2: models.Record,
    ) -> None:
        url = app.url_path_for(self.url_base, domain=global_domain_0.url)
        response = await do_api_request(client, "GET", url, user)
        assert response.status_code == 200
        res = response.json()
        res = res["data"]
        assert res["count"] == 3
        assert len(res["results"]) == 3
        assert (
            len(list(filter(lambda x: x["id"] == str(record_0.id), res["results"])))
            == 1
        )
        assert (
            len(list(filter(lambda x: x["id"] == str(record_1.id), res["results"])))
            == 1
        )
        assert (
            len(list(filter(lambda x: x["id"] == str(record_2.id), res["results"])))
            == 1
        )

    @pytest.mark.parametrize("user", [lazy_fixture("global_root_user")])
    async def test_list_records_filter_problem(
        self,
        client: AsyncClient,
        user: models.User,
        global_domain_0: models.Domain,
        problem_1: models.Problem,
        record_2: models.Record,
    ) -> None:
        url = app.url_path_for(self.url_base, domain=global_domain_0.url)
        response = await do_api_request(
            client, "GET", url, user, {"problem": str(problem_1.id)}
        )
        assert response.status_code == 200
        res = response.json()
        res = res["data"]
        assert res["count"] == 1
        assert len(res["results"]) == 1
        assert (
            len(list(filter(lambda x: x["id"] == str(record_2.id), res["results"])))
            == 1
        )

    @pytest.mark.parametrize("user", [lazy_fixture("global_root_user")])
    async def test_list_records_filter_problem_set(
        self,
        client: AsyncClient,
        user: models.User,
        global_domain_0: models.Domain,
        problem_set_0: models.ProblemSet,
        record_1: models.Record,
    ) -> None:
        url = app.url_path_for(self.url_base, domain=global_domain_0.url)
        response = await do_api_request(
            client, "GET", url, user, {"problemSet": str(problem_set_0.id)}
        )
        assert response.status_code == 200
        res = response.json()
        res = res["data"]
        assert res["count"] == 1
        assert len(res["results"]) == 1
        assert (
            len(list(filter(lambda x: x["id"] == str(record_1.id), res["results"])))
            == 1
        )


#     @pytest.mark.parametrize("user", [lazy_fixture("global_root_user")])
#     async def test_list_domain_desc(
#         self, client: AsyncClient, user: models.User
#     ) -> None:
#         await self.list_domain_helper(client, user, "-updated_at")
#
#     @pytest.mark.parametrize("user", [lazy_fixture("global_root_user")])
#     async def test_list_domain_illegal_field(
#         self, client: AsyncClient, user: models.User
#     ) -> None:
#         response = await do_api_request(
#             client, "GET", self.url, user, {"ordering": "error_field"}
#         )
#         assert response.status_code == 200
#         res = response.json()
#         assert res["errorCode"] == ErrorCode.IllegalFieldError
#
#
# @pytest.mark.asyncio
# @pytest.mark.depends(name="TestDomainGet", on=["TestDomainCreate::test_global_domains"])
# class TestDomainGet:
#     url_base = "get_domain"
#
#     @pytest.mark.parametrize("user", [lazy_fixture("global_root_user")])
#     @parametrize_global_domains
#     @pytest.mark.parametrize("url_type", ["url", "id"])
#     async def test_global_domains(
#         self,
#         client: AsyncClient,
#         user: models.User,
#         domain: models.Domain,
#         url_type: str,
#     ) -> None:
#         domain_path = get_path_by_url_type(domain, url_type)
#         url = app.url_path_for(self.url_base, domain=domain_path)
#         response = await do_api_request(client, "GET", url, user)
#         await validate_test_domain(response, user, domain)
#
#     @pytest.mark.parametrize("user", [lazy_fixture("global_root_user")])
#     @pytest.mark.parametrize("domain", [lazy_fixture("global_domain_0")])
#     async def test_domain_not_exist(
#         self,
#         client: AsyncClient,
#         user: models.User,
#         domain: models.Domain,
#     ) -> None:
#         url = app.url_path_for(self.url_base, domain=domain.url + "_not_exist")
#         response = await do_api_request(client, "GET", url, user)
#         assert response.status_code == 200
#         res = response.json()
#         assert res["errorCode"] == ErrorCode.DomainNotFoundError
