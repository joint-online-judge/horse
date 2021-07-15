from enum import Enum
from typing import Any

from fastapi import HTTPException, status


class ErrorCode(str, Enum):
    Success = "Success"
    Error = "Error"
    InternalServerError = "InternalServerError"

    ApiNotImplementedError = "ApiNotImplementedError"
    UserNotFoundError = "UserNotFoundError"
    DomainNotFoundError = "DomainNotFoundError"
    UrlNotUniqueError = "UrlNotUniqueError"
    InvalidUrlError = "InvalidUrlError"
    ProblemNotFoundError = "ProblemNotFoundError"
    ProblemSetNotFoundError = "ProblemSetNotFoundError"
    ProblemGroupNotFoundError = "ProblemGroupNotFoundError"
    RecordNotFoundError = "RecordNotFoundError"
    DeleteProblemBadRequestError = "DeleteProblemBadRequestError"
    UserAlreadyInDomainBadRequestError = "UserAlreadyInDomainBadRequestError"
    DomainInvitationBadRequestError = "DomainInvitationBadRequestError"
    ScoreboardHiddenBadRequestError = "ScoreboardHiddenBadRequestError"
    ProblemSetBeforeAvailableError = "ProblemSetBeforeAvailableError"
    ProblemSetAfterDueError = "ProblemSetAfterDueError"
    UserNotJudgerError = "UserNotJudgerError"
    DomainNotOwnerError = "DomainNotOwnerError"
    DomainNotRootError = "DomainNotRootError"
    DomainRoleNotFoundError = "DomainRoleNotFoundError"
    DomainRoleNotUniqueError = "DomainRoleNotUniqueError"
    DomainRoleReadOnlyError = "DomainRoleReadOnlyError"
    DomainRoleUsedError = "DomainRoleUsedError"
    DomainUserNotFoundError = "DomainUserNotFoundError"


class BizError(Exception):
    def __init__(self, error_code: ErrorCode, error_msg: str = ""):
        self.error_code = error_code
        self.error_msg = error_msg


class BaseError(HTTPException):
    def __init__(self, status_code: int, message: str = "", args: Any = None) -> None:
        if args is None:
            args = []
        super().__init__(status_code=status_code, detail=message.format(*args))


class BadRequestError(BaseError):
    def __init__(self, message: str = "", args: Any = None) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST, message=message, args=args
        )


class UnauthorizedError(BaseError):
    def __init__(self, message: str = "", args: Any = None) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED, message=message, args=args
        )


class ForbiddenError(BaseError):
    def __init__(self, message: str = "", args: Any = None) -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN, message=message, args=args
        )


class NotFoundError(BaseError):
    def __init__(self, message: str = "", args: Any = None) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND, message=message, args=args
        )


class UnprocessableEntityError(BaseError):
    def __init__(self, message: str = "", args: Any = None) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, message=message, args=args
        )


class InternalServerError(BaseError):
    def __init__(self, message: str = "", args: Any = None) -> None:
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=message,
            args=args,
        )
