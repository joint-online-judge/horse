# JOJ Horse

The new generation of JOJ Backend. "Horse" is related to speed, an excellent feature of the backend server. It is also a homophonic name in Chinese, aka, "后(horse)端"

## Requirements

+ Python >= 3.7
+ mongodb >= 3.5
+ rabbitmq
+ redis

## Misc

`pylint` is used as default linter. For your ease, you may need to add the following to `~/.pylintrc`(especially for VSCode users).

```;
[MASTER]
init-hook='import sys; sys.path.append("YOUR_PATH_TO_HORSE")
extension-pkg-whitelist=pydantic
disable=
    C0114, # missing-module-docstring
```

## Installation

Refer to <https://joint-online-judge.github.io/horse/> to prepare your environment.

(setup venv)

```bash
pip3 install -e .
vi .env # configure environment
python3 -m joj.horse
# or just press F5 in VS Code
```

Check <http://127.0.0.1:34765/api/v1> for api documentation.
