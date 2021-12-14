from functools import lru_cache
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import IO, TYPE_CHECKING, Any, BinaryIO, Dict, Literal, Optional
from uuid import UUID

import boto3
import rapidjson
from greenletio import async_
from joj.elephant.errors import ElephantError
from joj.elephant.manager import Manager
from joj.elephant.rclone import RClone
from joj.elephant.schemas import ArchiveType, FileInfo
from joj.elephant.storage import ArchiveStorage, LakeFSStorage, Storage
from lakefs_client import Configuration, __version__ as lakefs_client_version, models
from lakefs_client.client import LakeFSClient
from lakefs_client.exceptions import ApiException as LakeFSApiException
from loguru import logger
from patoolib.util import PatoolError

from joj.horse.config import settings
from joj.horse.utils.errors import BizError, ErrorCode
from joj.horse.utils.retry import retry_init

if TYPE_CHECKING:
    from joj.horse.models import Problem, Record, User
    from joj.horse.schemas.lakefs import LakeFSReset


@lru_cache
def get_lakefs_client() -> LakeFSClient:
    configuration = Configuration(
        host=f"{settings.lakefs_host}:{settings.lakefs_port}",
        username=settings.lakefs_username,
        password=settings.lakefs_password,
    )
    return LakeFSClient(configuration)


@lru_cache
def get_rclone() -> RClone:
    rclone_config = f"""
[lakefs]
type = s3
provider = Other
env_auth = false
access_key_id = {settings.lakefs_username}
secret_access_key = {settings.lakefs_password}
endpoint = http://{settings.lakefs_s3_domain}:{settings.lakefs_port}
    """
    return RClone(rclone_config)


def init_lakefs() -> None:
    client = get_lakefs_client()
    response: models.VersionConfig = client.config.get_lake_fs_version()
    server_version = response["version"]
    logger.info(
        f"LakeFS connected: client version {lakefs_client_version}, "
        f"server version {server_version}."
    )


@retry_init("LakeFS")
async def try_init_lakefs() -> None:
    init_lakefs()
    examine_lakefs_buckets()


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


def ensure_user(user_id: UUID) -> None:
    client = get_lakefs_client()
    try:
        client.auth.get_user(user_id=str(user_id))
    except LakeFSApiException:
        user_creation = models.UserCreation(id=str(user_id))
        user = client.auth.create_user(user_creation=user_creation)
        logger.info("LakeFS create user: {}", user)


def ensure_credentials(
    user_id: UUID, access_key_id: Optional[str] = None
) -> Optional[models.CredentialsWithSecret]:
    client = get_lakefs_client()
    if access_key_id is not None:
        try:
            client.auth.get_credentials(
                user_id=str(user_id), access_key_id=access_key_id
            )
            return None
        except LakeFSApiException:
            logger.warning("LakeFS invalid credentials: {}", access_key_id)
    credentials: models.CredentialsWithSecret = client.auth.create_credentials(
        user_id=str(user_id)
    )
    logger.info("LakeFS create credentials: {}", access_key_id)
    return credentials


def get_problem_config_repo_name(problem: "Problem") -> str:
    return f"joj-config-{problem.problem_group_id}"


def get_record_repo_name(record: "Record") -> str:
    return f"joj-submission-{record.problem_id}"


class LakeFSBase:
    def __init__(
        self,
        *,
        bucket: str,
        repo_id: str,
        branch_id: str,
        repo_name_prefix: str = "",
        branch_name_prefix: str = "",
        archive_name: str = "archive",
    ):
        self.bucket: str = bucket
        self.repo_id: str = repo_id
        self.branch_id: str = branch_id
        self.repo_name_prefix: str = repo_name_prefix
        self.branch_name_prefix: str = branch_name_prefix
        self.repo_name: str = f"{self.repo_name_prefix}{self.repo_id}"
        self.branch_name: str = f"{self.branch_name_prefix}{self.branch_id}"
        self.archive_name: str = archive_name
        self.repo: Optional[models.Repository] = None
        self.branch: Optional[models.Ref] = None
        self._storage: Optional[LakeFSStorage] = None

    @staticmethod
    def _get_lakefs_exception_message(e: LakeFSApiException) -> str:
        if e.body is None:
            return ""
        try:
            data = rapidjson.loads(e.body)
            return data["message"]
        except Exception:
            return ""

    def _get_storage(self, ref: Optional[str] = None) -> "Storage":
        if ref is None:
            ref = self.branch_name
        return LakeFSStorage(
            endpoint_url=f"http://{settings.lakefs_s3_domain}:{settings.lakefs_port}",
            repo_name=self.repo_name,
            branch_name=ref,
            username=settings.lakefs_username,
            password=settings.lakefs_password,
            host_in_config="lakefs",
        )

    @property
    def storage(self) -> "Storage":
        if self._storage is None:
            self._storage = self._get_storage()
        return self._storage

    @property
    def path(self) -> str:
        return f"lakefs:{self.repo_name}/{self.branch_name}/"

    def ensure_repo(self) -> None:
        if self.repo is not None:
            return
        client = get_lakefs_client()
        try:
            self.repo = client.repositories.get_repository(repository=self.repo_name)
            logger.info(f"LakeFS get repo: {self.repo}")
        except LakeFSApiException:
            namespace = f"{self.bucket}/{self.repo_id}"
            new_repo = models.RepositoryCreation(
                storage_namespace=namespace,
                name=self.repo_name,
                default_branch=self.branch_name,
            )
            self.repo = client.repositories.create_repository(new_repo)
            logger.info(f"LakeFS create repo: {self.repo}")

    def ensure_branch(self, source_branch_id: Optional[str] = None) -> None:
        self.ensure_repo()
        if self.branch is not None:
            return
        client = get_lakefs_client()
        try:
            self.branch = client.branches.get_branch(
                repository=self.repo_name, branch=self.branch_name
            )
            logger.info(f"LakeFS get branch: {self.branch}")
        except LakeFSApiException:
            if source_branch_id is None:
                assert self.repo is not None
                source_branch_name = self.repo.default_branch
            else:
                source_branch_name = f"{self.branch_name_prefix}{source_branch_id}"
            new_branch = models.BranchCreation(
                name=self.branch_name, source=source_branch_name
            )
            self.branch = client.branches.create_branch(
                repository=self.repo_name, branch_creation=new_branch
            )
            logger.info(f"LakeFS create branch: {self.branch}")

    def ensure_policy(self, permission: Literal["read", "all"]) -> models.Policy:
        if permission != "read" and permission != "all":
            raise BizError(
                ErrorCode.InternalServerError, f"permission not defined: {permission}"
            )
        client = get_lakefs_client()
        policy_id = f"{self.repo_name}-{permission}"
        try:
            policy = client.auth.get_policy(policy_id=policy_id)
        except LakeFSApiException:
            if permission == "read":
                action = ["fs:List*", "fs:Read*"]
            elif permission == "all":
                action = ["fs:*"]
            else:
                assert False
            policy = models.Policy(
                id=policy_id,
                statement=[
                    models.Statement(
                        effect="allow",
                        resource=f"arn:lakefs:fs:::repository/{self.repo_name}/*",
                        action=action,
                    )
                ],
            )
            policy = client.auth.create_policy(policy=policy)
            logger.info(f"LakeFS create policy: {policy_id}")
        return policy

    def ensure_user_policy(
        self, user: "User", permission: Literal["read", "all"]
    ) -> None:
        client = get_lakefs_client()
        policy = self.ensure_policy(permission)
        try:
            client.auth.attach_policy_to_user(user_id=str(user.id), policy_id=policy.id)
        except LakeFSApiException:
            pass

    def get_file_info(self, file_path: Path, ref: Optional[str] = None) -> FileInfo:
        try:
            if ref is None:
                storage = self.storage
            else:
                storage = self._get_storage(ref)
            return storage.getinfo(file_path)
        except ElephantError as e:
            raise BizError(ErrorCode.ProblemConfigDownloadError, str(e))

    def download_file(self, file_path: Path, ref: Optional[str] = None) -> BinaryIO:
        try:
            if ref is None:
                storage = self.storage
            else:
                storage = self._get_storage(ref)
            file = BytesIO()
            storage.download(file_path, file)
            file.seek(0)
            return file
        except ElephantError as e:
            raise BizError(ErrorCode.ProblemConfigDownloadError, str(e))

    def upload_file(self, file_path: Path, file: BinaryIO) -> FileInfo:
        try:
            return self.storage.upload(file_path, file)
        except ElephantError as e:
            raise BizError(ErrorCode.ProblemConfigUpdateError, str(e))

    def delete_file(self, file_path: Path) -> FileInfo:
        try:
            return self.storage.delete(file_path)
        except ElephantError as e:
            raise BizError(ErrorCode.ProblemConfigUpdateError, str(e))

    def delete_directory(self, file_path: Path, recursive: bool) -> FileInfo:
        try:
            if recursive:
                return self.storage.delete_tree(file_path)
            else:
                return self.storage.delete_dir(file_path)
        except ElephantError as e:
            raise BizError(ErrorCode.ProblemConfigUpdateError, str(e))

    def upload_archive(self, filename: str, file: IO[bytes]) -> None:
        self.ensure_branch()

        try:
            temp_file = NamedTemporaryFile(mode="wb", delete=True, suffix=filename)
            temp_file.write(file.read())
            temp_file.flush()
            logger.info("write archive into {}", temp_file.name)
            archive = ArchiveStorage(file_path=temp_file.name)
            archive.extract_all()
            manager = Manager(get_rclone(), archive, self.storage)
            logger.info(archive.path)
            manager.sync_without_validation()
            temp_file.close()

        except ElephantError as e:
            raise BizError(ErrorCode.ProblemConfigUpdateError, str(e))

    def download_archive(
        self, temp_dir: Path, archive_type: ArchiveType, ref: Optional[str] = None
    ) -> Path:
        self.ensure_branch()
        if ref is None:
            storage = self.storage
        else:
            storage = self._get_storage(ref)

        try:
            filename = self.archive_name
            if archive_type == ArchiveType.zip:
                filename += ".zip"
            elif archive_type == ArchiveType.tar:
                filename += ".tar.gz"
            else:
                raise BizError(
                    ErrorCode.ProblemConfigDownloadError,
                    "archive type not supported!",
                )

            temp_file_path = temp_dir / filename

            archive = ArchiveStorage(file_path=str(temp_file_path))
            manager = Manager(get_rclone(), storage, archive)
            manager.sync_without_validation()

            for file in Path(archive.path).iterdir():
                logger.info(file)
            archive.compress_all()
            return temp_file_path

        except (ElephantError, PatoolError) as e:
            raise BizError(ErrorCode.ProblemConfigDownloadError, str(e))
        except Exception as e:
            raise e

    def get_config(self, ref: str) -> Dict[str, Any]:
        try:
            result = self.download_file(Path("config.json"), ref)
            return rapidjson.load(result)
        except ElephantError:
            raise BizError(
                ErrorCode.ProblemConfigValidationError,
                "config.json not found in problem config.",
            )

    def commit(self, message: str) -> models.Commit:
        try:
            client = get_lakefs_client()
            commit_creation = models.CommitCreation(message=message)
            result: models.Commit = client.commits.commit(
                repository=self.repo_name,
                branch=self.branch_name,
                commit_creation=commit_creation,
            )
            return result
        except LakeFSApiException as e:
            raise BizError(
                ErrorCode.ProblemConfigUpdateError,
                self._get_lakefs_exception_message(e),
            )

    async def commit_async(self, message: str) -> models.Commit:
        return await async_(self.commit)(message)

    def reset(self, lakefs_reset: "LakeFSReset") -> None:
        try:
            client = get_lakefs_client()
            reset_creation = models.ResetCreation(
                type=lakefs_reset.get_lakefs_type(),
                path=lakefs_reset.path,
            )
            client.branches.reset_branch(
                repository=self.repo_name,
                branch=self.branch_name,
                reset_creation=reset_creation,
            )
        except LakeFSApiException as e:
            raise BizError(
                ErrorCode.ProblemConfigUpdateError,
                self._get_lakefs_exception_message(e),
            )


class LakeFSProblemConfig(LakeFSBase):
    def __init__(self, problem: "Problem"):
        super().__init__(
            bucket=settings.bucket_config,
            repo_id=str(problem.problem_group_id),
            branch_id=str(problem.id),
            repo_name_prefix="joj-config-",
            branch_name_prefix="problem-",
            archive_name=f"problem-config-{problem.title}",
        )
        self.problem = problem


class LakeFSRecord(LakeFSBase):
    def __init__(self, problem: "Problem", record: "Record"):
        super().__init__(
            bucket=settings.bucket_submission,
            repo_id=str(record.problem_id),
            branch_id=str(record.committer_id),
            repo_name_prefix="joj-submission-",
            branch_name_prefix="user-",
            archive_name="code",
        )
        self.problem = problem
        self.record = record
