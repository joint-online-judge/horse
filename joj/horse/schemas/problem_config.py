from joj.horse.schemas.base import BaseModel


class ProblemConfigCommit(BaseModel):
    message: str = ""


class ProblemConfig(BaseModel):
    pass
    # class Meta:
    #     collection_name = "problem.configs"
    #     strict = False
