# -*- coding: utf-8 -*-
"""Sanic request argument parsing module.

Origin: https://github.com/EndurantDevs/webargs-sanic
Modified By: tc-imba (update webargs api to 6.x)

Example: ::
    from sanic import Sanic
    from webargs import fields
    from webargs_sanic.sanicparser import use_args
    app = Sanic(__name__)
    hello_args = {
        'name': fields.Str(required=True)
    }
    @app.route('/')
    @use_args(hello_args)
    async def index(args):
        return 'Hello ' + args['name']
"""
import sanic
import sanic.request
import sanic.exceptions

from webargs import core
from webargs.compat import MARSHMALLOW_VERSION_INFO
from webargs.asyncparser import AsyncParser
from webargs.multidictproxy import MultiDictProxy


@sanic.exceptions.add_status_code(400)
@sanic.exceptions.add_status_code(422)
class HandleValidationError(sanic.exceptions.SanicException):
    pass


def abort(http_status_code, exc=None, **kwargs):
    """Raise a HTTPException for the given http_status_code. Attach any keyword
    arguments to the exception for later processing.
    From Flask-Restful. See NOTICE file for license information.
    """
    try:
        sanic.exceptions.abort(http_status_code, exc)
    except sanic.exceptions.SanicException as err:
        err.data = kwargs

        if exc and not hasattr(exc, 'messages'):
            exc.messages = kwargs.get('messages')
        err.exc = exc
        raise err


def is_json_request(req):
    content_type = req.content_type
    return core.is_json(content_type)


class SanicParser(AsyncParser):
    """Sanic request argument parser."""

    __location_map__ = dict(
        view_args="load_view_args",
        path="load_view_args",
        **core.Parser.__location_map__
    )

    def load_view_args(self, req, schema):
        """Pull a value from the request's ``view_args``."""
        return req.match_info or core.missing

    def get_request_from_view_args(self, view, args, kwargs):
        """Get request object from a handler function or method. Used internally by
        ``use_args`` and ``use_kwargs``.
        """
        if len(args) > 1 and isinstance(args[1], sanic.request.Request):
            req = args[1]
        else:
            req = args[0]
        assert isinstance(
            req, sanic.request.Request
        ), "Request argument not found for handler"
        return req

    def _raw_load_json(self, req):
        """Return a json payload from the request for the core parser's load_json

        Checks the input mimetype and may return 'missing' if the mimetype is
        non-json, even if the request body is parseable as json."""
        if not is_json_request(req):
            return core.missing

        try:
            return req.json
        except:
            return core.parse_json(req.body)

    def _handle_invalid_json_error(self, error, req, *args, **kwargs):
        status_code = 400
        abort(status_code, exc=error, messages={"json": ["Invalid JSON body."]}, status_code=status_code)

    def load_querystring(self, req, schema):
        """Return query params from the request as a MultiDictProxy."""
        return MultiDictProxy(req.args, schema)

    def load_form(self, req, schema):
        """Return form values from the request as a MultiDictProxy."""
        return MultiDictProxy(req.form, schema)

    def load_headers(self, req, schema):
        """Return headers from the request as a MultiDictProxy."""
        return MultiDictProxy(req.headers, schema)

    def load_cookies(self, req, schema):
        """Return cookies from the request."""
        return req.cookies

    def load_files(self, req, schema):
        """Return files from the request as a MultiDictProxy."""
        return MultiDictProxy(req.files, schema)

    def handle_error(self, error, req, schema, error_status_code=None, error_headers=None):
        """Handles errors during parsing. Aborts the current HTTP request and
        responds with a 422 error.
        """
        status_code = error_status_code or getattr(error, "status_code", self.DEFAULT_VALIDATION_STATUS)
        # on marshmallow 2, a many schema receiving a non-list value will
        # produce this specific error back -- reformat it to match the
        # marshmallow 3 message so that Flask can properly encode it
        messages = error.messages
        if (
                MARSHMALLOW_VERSION_INFO[0] < 3
                and schema.many
                and messages == {0: {}, "_schema": ["Invalid input type."]}
        ):
            messages.pop(0)
        abort(status_code, exc=error, messages=messages, schema=schema, status_code=status_code, header=error_headers)


parser = SanicParser()
use_args = parser.use_args
use_kwargs = parser.use_kwargs
