from typing import TYPE_CHECKING, Optional

import boto3
from lakefs_client import Configuration, __version__ as lakefs_client_version, models
from lakefs_client.client import LakeFSClient
from lakefs_client.exceptions import ApiException as LakeFSApiException
from loguru import logger
from tenacity import retry
from tenacity.stop import stop_after_attempt
from tenacity.wait import wait_exponential

from joj.horse.config import settings

if TYPE_CHECKING:
    from joj.horse.models import Problem

__client: Optional[LakeFSClient] = None


def init_lakefs() -> None:
    global __client
    configuration = Configuration(
        host=f"{settings.lakefs_host}:{settings.lakefs_port}",
        username=settings.lakefs_username,
        password=settings.lakefs_password,
    )
    client = LakeFSClient(configuration)
    response: models.VersionConfig = client.config.get_lake_fs_version()
    server_version = response["version"]
    __client = client
    logger.info(
        f"LakeFS connected: client version {lakefs_client_version}, "
        f"server version {server_version}."
    )


@retry(stop=stop_after_attempt(5), wait=wait_exponential(2))
def try_init_lakefs() -> None:
    attempt_number = try_init_lakefs.retry.statistics["attempt_number"]
    try:
        init_lakefs()
    except Exception as e:
        max_attempt_number = try_init_lakefs.retry.stop.max_attempt_number
        msg = "LakeFS: initialization failed ({}/{})".format(
            attempt_number, max_attempt_number
        )
        if attempt_number < max_attempt_number:
            msg += ", trying again after {} second.".format(2 ** attempt_number)
        else:
            msg += "."
        logger.error(e)
        logger.warning(msg)
        raise e


def get_lakefs_client() -> LakeFSClient:
    if __client is None:
        raise NotImplementedError("LakeFS not connected!")
    return __client


def create_bucket(bucket: str) -> None:
    if not bucket.startswith("s3://"):
        raise ValueError("only s3 bucket can be automatically created")
    if not settings.s3_host or not settings.s3_port:
        raise ValueError("s3 host or port not defined")
    logger.info(f"LakeFS: create bucket {bucket} automatically.")
    try:
        s3 = boto3.resource(
            "s3",
            endpoint_url=f"http://{settings.s3_host}:{settings.s3_port}",
            aws_access_key_id=settings.s3_username,
            aws_secret_access_key=settings.s3_password,
            # config=Config(signature_version="s3v4"),
            # region_name="us-east-1",
        )
        s3.create_bucket(Bucket=bucket[5:])
    except Exception as e:
        logger.error(f"LakeFS: create bucket {bucket} failed.")
        logger.error("Please check the s3 settings or create the bucket yourselves.")
        raise e


def examine_bucket(bucket: str) -> None:
    client = get_lakefs_client()

    def delete_test_repo(_repo_name: str) -> None:
        try:
            client.repositories.delete_repository(repository=_repo_name)
        except LakeFSApiException:
            pass

    repo_name = "joj-generated-for-test-do-not-edit"
    namespace = f"{bucket}/{repo_name}"
    logger.info(f"LakeFS: examine bucket {bucket}.")
    # delete the test repo if exists
    delete_test_repo(repo_name)
    # create the test repo
    new_repo = models.RepositoryCreation(storage_namespace=namespace, name=repo_name)
    client.repositories.create_repository(new_repo)
    # delete the test repo again
    delete_test_repo(repo_name)
    logger.info(f"LakeFS: examine bucket {bucket} succeeded.")


def examine_lakefs_buckets() -> None:
    """
    Test whether the lakefs with storage backend is working.
    """
    for bucket in {settings.bucket_config, settings.bucket_submission}:
        try:
            examine_bucket(bucket)
        except LakeFSApiException:
            logger.warning(f"LakeFS: examine bucket {bucket} failed.")
            create_bucket(bucket)
            examine_bucket(bucket)


def get_problem_submission_repo_name(problem: "Problem") -> str:
    return f"joj-submission-{problem.id}"


class LakeFSProblemConfig:
    def __init__(self, problem: "Problem"):
        self.client = get_lakefs_client()
        # self.problem: "Problem" = problem
        self.repo_id: str = str(problem.problem_group_id)
        self.branch_id: str = str(problem.id)
        self.repo_name: str = f"joj-config-{self.repo_id}"
        self.branch_name: str = f"problem-{self.branch_id}"
        self.repo: Optional[models.Repository] = None
        self.branch: Optional[models.Ref] = None

    def ensure_repo(self) -> None:
        if self.repo is not None:
            return
        try:
            self.repo = self.client.repositories.get_repository(
                repository=self.repo_name
            )
            logger.info(f"LakeFS get repo: {self.repo}")
        except LakeFSApiException:
            namespace = f"{settings.bucket_config}/{self.repo_id}"
            new_repo = models.RepositoryCreation(
                storage_namespace=namespace,
                name=self.repo_name,
                default_branch=self.branch_name,
            )
            self.repo = self.client.repositories.create_repository(new_repo)
            logger.info(f"LakeFS create repo: {self.repo}")

    def ensure_branch(self, problem_base: Optional["Problem"] = None) -> None:
        self.ensure_repo()
        if self.branch is not None:
            return
        try:
            self.branch = self.client.branches.get_branch(
                repository=self.repo_name, branch=self.branch_name
            )
            logger.info(f"LakeFS get branch: {self.branch}")
        except LakeFSApiException:
            if problem_base is None:
                assert self.repo is not None
                source_branch_name = self.repo.default_branch
            else:
                source_branch_name = f"problem-{str(problem_base.id)}"
            new_branch = models.BranchCreation(
                name=self.branch_name, source=source_branch_name
            )
            self.branch = self.client.branches.create_branch(
                repository=self.repo_name, branch_creation=new_branch
            )
            logger.info(f"LakeFS create branch: {self.branch}")
