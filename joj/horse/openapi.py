"""
Generate the openapi schema
"""

import json

from joj.horse import app

openapi_json = json.dumps(app.openapi(), indent=2)
print(openapi_json)
