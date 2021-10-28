from joj.horse.schemas import BaseModel


class Version(BaseModel):
    version: str
    git: str


class JWT(BaseModel):
    jwt: str


class RedirectModel(BaseModel):
    redirect_url: str


class AuthTokens(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
