import git

repo = git.Repo(".")
headcommit = repo.head.commit
from datetime import datetime

utc_dt = datetime.fromtimestamp(headcommit.committed_date)
print(utc_dt)
