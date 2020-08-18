from setuptools import setup

setup(
    name='joj_horse',
    version='0.0.1',
    packages=['joj.horse'],
    include_package_data=True,
    install_requires=[
        'fastapi',
        'uvicorn',
        'starlette',
        'aiohttp',
        'click>=7',
        'celery>=4.4',
        'gitpython>=3.1.7',
        'motor>=2.1.0',
        'Motor-ODM',
        'pydantic[dotenv]',
        'oauth-jaccount',
        'aiocache[redis]'
    ],
)
