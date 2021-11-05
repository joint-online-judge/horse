import inspect
from copy import deepcopy
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Type, Union

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
