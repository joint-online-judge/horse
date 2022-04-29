import inspect
from copy import deepcopy
from io import IOBase
from tempfile import SpooledTemporaryFile as SpooledTemporaryFile
from typing import (
    Any,
    AnyStr,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
)

from fastapi import params
from fastapi.dependencies import utils
from fastapi.dependencies.utils import (
    create_response_field,
    is_scalar_field,
    is_scalar_sequence_field,
)
from fastapi_utils.camelcase import snake2camel
from pydantic.error_wrappers import ErrorWrapper
from pydantic.errors import MissingError
from pydantic.fields import FieldInfo, ModelField, Required
from pydantic.schema import get_annotation_from_field_info
from starlette.datastructures import Headers, QueryParams


def get_param_field(
    *,
    param: inspect.Parameter,
    param_name: str,
    default_field_info: Type[params.Param] = params.Param,
    force_type: Optional[params.ParamTypes] = None,
    ignore_default: bool = False,
) -> ModelField:
    default_value = Required
    had_schema = False
    if not param.default == param.empty and ignore_default is False:
        default_value = param.default
    if isinstance(default_value, FieldInfo):
        had_schema = True
        field_info = default_value
        default_value = field_info.default
        if (
            isinstance(field_info, params.Param)
            and getattr(field_info, "in_", None) is None
        ):
            field_info.in_ = default_field_info.in_
        if force_type:
            field_info.in_ = force_type  # type: ignore
    else:
        field_info = default_field_info(default_value)
    required = default_value == Required
    annotation: Any = Any
    if not param.annotation == param.empty:
        annotation = param.annotation
    annotation = get_annotation_from_field_info(annotation, field_info, param_name)
    if not field_info.alias and getattr(field_info, "convert_underscores", None):
        alias = param.name.replace("_", "-")
    else:
        if field_info.alias:
            alias = field_info.alias
        else:
            alias = snake2camel(param.name, start_lower=True)
    field = create_response_field(
        name=param.name,
        type_=annotation,
        default=None if required else default_value,
        alias=alias,
        required=required,
        field_info=field_info,
    )
    field.required = required
    if not had_schema and not is_scalar_field(field=field):
        field.field_info = params.Body(field_info.default)

    return field


def request_params_to_args(
    required_params: Sequence[ModelField],
    received_params: Union[Mapping[str, Any], QueryParams, Headers],
) -> Tuple[Dict[str, Any], List[ErrorWrapper]]:
    values = {}
    errors = []
    for field in required_params:
        if is_scalar_sequence_field(field) and isinstance(
            received_params, (QueryParams, Headers)
        ):
            value = received_params.getlist(field.alias)
            if not value:
                value = received_params.getlist(field.name)
            if not value:
                value = field.default
        else:
            value = received_params.get(field.alias)
            if value is None:
                value = received_params.get(field.name)

        field_info = field.field_info
        assert isinstance(
            field_info, params.Param
        ), "Params must be subclasses of Param"
        if value is None:
            if field.required:
                errors.append(
                    ErrorWrapper(
                        MissingError(), loc=(field_info.in_.value, field.alias)
                    )
                )
            else:
                values[field.name] = deepcopy(field.default)
            continue
        v_, errors_ = field.validate(
            value, values, loc=(field_info.in_.value, field.alias)
        )
        if isinstance(errors_, ErrorWrapper):
            errors.append(errors_)
        elif isinstance(errors_, list):
            errors.extend(errors_)
        else:
            values[field.name] = v_
    return values, errors


utils.get_param_field = get_param_field
utils.request_params_to_args = request_params_to_args


# pragma: no cover
class SpooledTemporaryFileIOBase(IOBase):
    def __init__(self, file: SpooledTemporaryFile):  # type: ignore
        self.file = file

    def close(self, *args, **kwargs):  # type: ignore
        """
        Flush and close the IO object.

        This method has no effect if the file is already closed.
        """
        self.file.close()

    def fileno(self, *args, **kwargs):  # type: ignore
        """
        Returns underlying file descriptor if one exists.

        OSError is raised if the IO object does not use a file descriptor.
        """
        return self.file.fileno()

    def flush(self, *args, **kwargs):  # type: ignore
        """
        Flush write buffers, if applicable.

        This is not implemented for read-only and non-blocking streams.
        """
        self.file.flush()

    def isatty(self, *args, **kwargs):  # type: ignore
        """
        Return whether this is an 'interactive' stream.

        Return False if it can't be determined.
        """
        return self.file.isatty()

    def readable(self, *args, **kwargs):  # type: ignore
        """
        Return whether object was opened for reading.

        If False, read() will raise OSError.
        """
        return self.file.readable()

    def readline(self, *args, **kwargs):  # type: ignore
        """
        Read and return a line from the stream.

        If size is specified, at most size bytes will be read.

        The line terminator is always b'\n' for binary files; for text
        files, the newlines argument to open can be used to select the line
        terminator(s) recognized.
        """
        return self.file.readline(*args)

    def readlines(self, *args, **kwargs):  # type: ignore
        """
        Return a list of lines from the stream.

        hint can be specified to control the number of lines read: no more
        lines will be read if the total size (in bytes/characters) of all
        lines so far exceeds hint.
        """
        return self.file.readlines(*args)

    def seek(self, *args, **kwargs):  # type: ignore
        """
        Change stream position.

        Change the stream position to the given byte offset. The offset is
        interpreted relative to the position indicated by whence.  Values
        for whence are:

        * 0 -- start of stream (the default); offset should be zero or positive
        * 1 -- current stream position; offset may be negative
        * 2 -- end of stream; offset is usually negative

        Return the new absolute position.
        """
        return self.file.seek(*args)

    def seekable(self, *args, **kwargs):  # type: ignore
        """
        Return whether object supports random access.

        If False, seek(), tell() and truncate() will raise OSError.
        This method may need to do a test seek().
        """
        return self.file._file.seekable()  # type: ignore

    def tell(self, *args, **kwargs):  # type: ignore
        """Return current stream position."""
        return self.file.tell()

    def truncate(self, size=None):  # type: ignore
        """
        Truncate file to size bytes.

        File pointer is left unchanged.  Size defaults to the current IO
        position as reported by tell().  Returns the new size.
        """
        if size is None:
            return self.file._file.truncate()  # type: ignore
        if size > self._max_size:  # type: ignore
            self.file.rollover()
        return self.file._file.truncate(size)  # type: ignore

    def writable(self, *args, **kwargs):  # type: ignore
        """
        Return whether object was opened for writing.

        If False, write() will raise OSError.
        """
        return self.file._file.writable()  # type: ignore

    def writelines(self, *args, **kwargs):  # type: ignore
        """
        Write a list of lines to stream.

        Line separators are not added, so it is usual for each of the
        lines provided to have a line separator at the end.
        """
        self.file.writelines(*args)

    def read(self, *args, **kwargs):  # type: ignore
        return self.file.read(*args)

    def write(self, *args, **kwargs):  # type: ignore
        self.file.write(*args)

    def readinto(self, b):  # type: ignore
        return self.file._file.readinto(b)  # type: ignore

    def __enter__(self, *args, **kwargs):  # type: ignore
        self.file.__enter__()
        return self

    def __exit__(self, *args, **kwargs):  # type: ignore
        self.file.__exit__(*args)

    def __iter__(self, *args, **kwargs):  # type: ignore
        """Implement iter(self)."""
        return self.file.__iter__()

    def __next__(self) -> AnyStr:
        return self.file.__next__()
