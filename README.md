# JOJ Horse

[![CI/CD](https://github.com/joint-online-judge/horse/actions/workflows/cicd.yml/badge.svg?branch=master)](https://github.com/joint-online-judge/horse/actions/workflows/cicd.yml)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/2d87ea14ebb34665aa9ace224f7ffef3)](https://www.codacy.com/gh/joint-online-judge/horse/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=joint-online-judge/horse&amp;utm_campaign=Badge_Grade)
[![Codacy Badge](https://app.codacy.com/project/badge/Coverage/2d87ea14ebb34665aa9ace224f7ffef3)](https://www.codacy.com/gh/joint-online-judge/horse/dashboard?utm_source=github.com&utm_medium=referral&utm_content=joint-online-judge/horse&utm_campaign=Badge_Coverage)

The new generation of JOJ Backend. "Horse" is related to speed, an excellent feature of the backend server. It is also a homophonic name in Chinese, aka, "后(horse)端"

## Requirements

+ Python >= 3.7
+ PostgreSQL
+ Redis
+ LakeFS

## Installation

Refer to <https://joint-online-judge.github.io/horse/> to prepare your environment.

```bash
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -
poetry install --no-dev
vi .env # configure environment
```
### For developers

```bash
poetry install -E test
poetry run pre-commit install
poetry run pytest -svv
```

## Usage

```bash
poetry run python -m joj.horse
```

Check <http://127.0.0.1:34765/api/v1> for api documentation.

## License

MIT
