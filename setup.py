from setuptools import setup

setup(
    name='joj_horse',
    version='0.0.1',
    packages=['joj.horse'],
    include_package_data=True,
    install_requires=[
        'sanic==19.12.0',
        'sanic-plugins-framework>=0.9.0',
        'sanic-restplus>=0.5.3',
        'celery>=4.4',
        'gitpython>=3.1.7',
        'motor>=2.1.0',
    ],
)