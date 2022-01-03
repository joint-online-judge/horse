# JOJ Horse

[![GitHub](https://img.shields.io/github/license/joint-online-judge/horse)](https://github.com/joint-online-judge/horse/blob/master/LICENSE)
[![CI/CD](https://img.shields.io/github/workflow/status/joint-online-judge/horse/cicd/master)](https://github.com/joint-online-judge/horse/actions/workflows/cicd.yml)
[![GitHub branch checks state](https://img.shields.io/github/checks-status/joint-online-judge/horse/master)](https://github.com/joint-online-judge/horse)
[![Codacy Badge](https://img.shields.io/codacy/grade/2d87ea14ebb34665aa9ace224f7ffef3)](https://www.codacy.com/gh/joint-online-judge/horse/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=joint-online-judge/horse&amp;utm_campaign=Badge_Grade)
[![Codacy Badge](https://img.shields.io/codacy/coverage/2d87ea14ebb34665aa9ace224f7ffef3)](https://www.codacy.com/gh/joint-online-judge/horse/dashboard?utm_source=github.com&utm_medium=referral&utm_content=joint-online-judge/horse&utm_campaign=Badge_Coverage)
[![Swagger Badge](https://img.shields.io/swagger/valid/3.0?specUrl=https%3A%2F%2Fraw.githubusercontent.com%2Fjoint-online-judge%2Fhorse%2Fopenapi%2Fopenapi.json)](https://github.com/joint-online-judge/horse/blob/openapi/openapi.json)

The new generation of JOJ Backend. "Horse" is related to speed, an excellent feature of the backend server. It is also a homophonic name in Chinese, aka, "后(horse)端"

## Requirements

+ Python == 3.8
+ PostgreSQL
+ Redis
+ LakeFS

## Installation

You should use Docker container for development and production. Check <https://github.com/joint-online-judge/joj-deploy-lite>.

### For Developers (and IntelliSense)

```bash
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python - # install poetry
poetry install -E test
poetry run pre-commit install
```

Check <http://127.0.0.1:34765/api/v1> for api documentation.

## License

MIT
