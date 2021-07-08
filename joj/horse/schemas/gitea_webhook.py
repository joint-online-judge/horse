from datetime import datetime
from typing import List, Optional

from pydantic.main import BaseModel


class User(BaseModel):
    id: int
    login: str
    full_name: str
    email: str
    avatar_url: str
    language: str
    is_admin: bool
    last_login: datetime
    created: datetime
    restricted: bool
    username: str


class Permission(BaseModel):
    admin: bool
    push: bool
    pull: bool


class InternalTracker(BaseModel):
    enable_time_tracker: bool
    allow_only_contributors_to_track_time: bool
    enable_issue_dependencies: bool


class ExternalTracker(BaseModel):
    external_tracker_url: str
    external_tracker_format: str
    external_tracker_style: str


class ExternalWiki(BaseModel):
    external_wiki_url: str


class Repository(BaseModel):
    id: int
    owner: User
    name: str
    full_name: str
    description: str
    empty: bool
    private: bool
    fork: bool
    template: bool
    parent: Optional["Repository"]
    mirror: bool
    size: int
    html_url: str
    ssh_url: str
    clone_url: str
    original_url: str
    website: str
    stars_count: int
    forks_count: int
    watchers_count: int
    open_issues_count: int
    open_pr_counter: int
    release_counter: int
    default_branch: str
    archived: bool
    created_at: datetime
    updated_at: datetime
    permissions: Optional[Permission]
    has_issues: bool
    internal_tracker: Optional[InternalTracker]
    external_tracker: Optional[ExternalTracker]
    has_wiki: bool
    external_wiki: Optional[ExternalWiki]
    has_pull_requests: bool
    has_projects: bool
    ignore_whitespace_conflicts: bool
    allow_merge_commits: bool
    allow_rebase: bool
    allow_rebase_explicit: bool
    allow_squash_merge: bool
    avatar_url: str
    internal: bool
    mirror_interval: str


Repository.update_forward_refs()


class PayloadUser(BaseModel):
    name: str
    email: str
    username: str


class Verification(BaseModel):
    verified: bool
    reason: str
    signature: str
    signer: Optional[PayloadUser]
    payload: str


class Commit(BaseModel):
    id: str
    message: str
    url: str
    author: Optional[PayloadUser]
    committer: Optional[PayloadUser]
    verification: Optional[Verification]
    timestamp: datetime
    added: Optional[List[str]]
    removed: Optional[List[str]]
    modified: Optional[List[str]]


class GiteaWebhook(BaseModel):
    secret: str
    ref: str
    before: str
    after: str
    compare_url: str
    commits: Optional[List[Commit]]
    head_commit: Optional[Commit]
    repository: Optional[Repository]
    pusher: Optional[User]
    sender: Optional[User]
