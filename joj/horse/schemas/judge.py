from joj.horse.schemas import BaseModel


class JudgerClaim(BaseModel):
    task_id: str


class JudgerCredentials(BaseModel):
    access_key_id: str
    secret_access_key: str
    problem_config_repo_name: str
    problem_config_commit_id: str
    record_repo_name: str
    record_commit_id: str
