# JOJ Horse

[![CI/CD](https://github.com/joint-online-judge/horse/actions/workflows/cicd.yml/badge.svg?branch=master)](https://github.com/joint-online-judge/horse/actions/workflows/cicd.yml)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/2d87ea14ebb34665aa9ace224f7ffef3)](https://www.codacy.com/gh/joint-online-judge/horse/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=joint-online-judge/horse&amp;utm_campaign=Badge_Grade)
[![Coverage](https://img.shields.io/codecov/c/github/joint-online-judge/horse)](https://codecov.io/gh/joint-online-judge/horse)

The new generation of JOJ Backend. "Horse" is related to speed, an excellent feature of the backend server. It is also a homophonic name in Chinese, aka, "后(horse)端"

## Requirements

+ Python >= 3.7
+ mongodb >= 3.5
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
pip3 install -e ".[dev,test]"
pre-commit install
pytest -svv
```

Check <http://127.0.0.1:34765/api/v1> for api documentation.
