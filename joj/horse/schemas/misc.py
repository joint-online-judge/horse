from pydantic import BaseModel


class Version(BaseModel):
    version: str
    git: str


class JWT(BaseModel):
    jwt: str


class RedirectModel(BaseModel):
    redirect_url: str
