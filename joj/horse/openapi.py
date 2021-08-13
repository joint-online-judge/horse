"""
Generate the openapi schema
"""

import rapidjson

from joj.horse.app import app

openapi_json = rapidjson.dumps(app.openapi(), indent=2)
print(openapi_json)
