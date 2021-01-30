from fastapi import HTTPException, status


class BaseError(HTTPException):
    def __init__(self, status_code, message: str = '', args=None) -> None:
        if args is None:
            args = []
        super().__init__(status_code=status_code, detail=message.format(*args))


class BadRequestError(BaseError):
    def __init__(self, message: str = '', args=None) -> None:
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, message=message, args=args)


class UnauthorizedError(BaseError):
    def __init__(self, message: str = '', args=None) -> None:
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, message=message, args=args)


class InvalidAuthenticationError(UnauthorizedError):
    def __init__(self) -> None:
        message = 'Invalid authentication.'
        super().__init__(message)


class ForbiddenError(BaseError):
    def __init__(self, message: str = '', args=None) -> None:
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, message=message, args=args)


class NotFoundError(BaseError):
    def __init__(self, message: str = '', args=None) -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, message=message, args=args)


class UserNotFoundError(NotFoundError):
    def __init__(self, uid: str) -> None:
        message = 'User {} not found.'
        super().__init__(message=message, args=[uid])
