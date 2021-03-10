# JOJ Horse

The new generation of JOJ Backend. "Horse" is related to speed, an excellent feature of the backend server. It is also a homophonic name in Chinese, aka, "后(horse)端"

## Requirements

+ Python >= 3.7
+ mongodb >= 3.5
+ rabbitmq
+ redis

## Installation

Refer to <https://joint-online-judge.github.io/horse/> to prepare your environment.

(setup venv)

```bash
pip3 install -e .
pre-commit install
vi .env # configure environment
python3 -m joj.horse
# or just press F5 in VS Code
```

Check <http://127.0.0.1:34765/api/v1> for api documentation.
