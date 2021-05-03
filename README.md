# JOJ Horse

[![Test](https://github.com/joint-online-judge/horse/actions/workflows/test.yml/badge.svg)](https://github.com/joint-online-judge/horse/actions/workflows/test.yml)

The new generation of JOJ Backend. "Horse" is related to speed, an excellent feature of the backend server. It is also a homophonic name in Chinese, aka, "后(horse)端"

## Requirements

+ Python >= 3.7
+ mongodb >= 3.5
+ rabbitmq
+ redis

## Installation

Refer to <https://joint-online-judge.github.io/horse/> to prepare your environment.

### Setup venv (Optional)

```bash
python3 -m venv env
source env/Scripts/activate
```

```bash
pip3 install -e .
vi .env # configure environment
python3 -m joj.horse # or just press F5 in VS Code
```

### For developers

```bash
pip3 install -r requirements-dev.txt
pre-commit install
pytest -svv
```

Check <http://127.0.0.1:34765/api/v1> for api documentation.
