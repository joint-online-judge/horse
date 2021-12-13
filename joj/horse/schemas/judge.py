from joj.horse.schemas import BaseModel


class JudgeClaim(BaseModel):
    task_id: str


class JudgeCredentials(BaseModel):
    access_key_id: str
    secret_access_key: str
    problem_config_repo_name: str
    problem_config_commit_id: str
    record_repo_name: str
    record_commit_id: str
