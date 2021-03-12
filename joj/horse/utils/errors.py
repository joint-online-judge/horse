from typing import Any

from fastapi import HTTPException, status


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


class APINotImplementedError(BaseError):
    def __init__(self, message: str = "", args: Any = None) -> None:
        super().__init__(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, message=message, args=args
        )


class InvalidAuthenticationError(UnauthorizedError):
    def __init__(self) -> None:
        message = "Invalid authentication."
        super().__init__(message)


class UserNotFoundError(NotFoundError):
    def __init__(self, uid: str) -> None:
        message = "User {} not found."
        super().__init__(message=message, args=[uid])


class DomainNotFoundError(NotFoundError):
    def __init__(self, domain: str) -> None:
        message = "Domain {} not found."
        super().__init__(message=message, args=[domain])


class InvalidDomainURLError(UnprocessableEntityError):
    def __init__(self, url: str) -> None:
        message = "Invalid domain url {}."
        super().__init__(message=message, args=[url])


class ProblemNotFoundError(NotFoundError):
    def __init__(self, problem: str) -> None:
        message = "Problem {} not found."
        super().__init__(message=message, args=[problem])


class ProblemSetNotFoundError(NotFoundError):
    def __init__(self, problem_set: str) -> None:
        message = "Problem set {} not found."
        super().__init__(message=message, args=[problem_set])


class ProblemGroupNotFoundError(NotFoundError):
    def __init__(self, problem_group: str) -> None:
        message = "Problem group {} not found."
        super().__init__(message=message, args=[problem_group])


class RecordNotFoundError(NotFoundError):
    def __init__(self, record: str) -> None:
        message = "Record {} not found."
        super().__init__(message=message, args=[record])


class DeleteProblemBadRequestError(BadRequestError):
    def __init__(self, problem_set: str) -> None:
        message = "Problem {} fdelete bad request."
        super().__init__(message=message, args=[problem_set])
