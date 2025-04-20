from .constants import HTTPStatus, STATUS_TEXT

class HTTPException(Exception):
    """Base class for HTTP related exceptions."""
    def __init__(self, status_code: HTTPStatus, message: str | None = None):
        self.status_code = status_code
        self.message = message or STATUS_TEXT.get(status_code, "Unknown Error")
        super().__init__(f"{self.status_code} {self.message}")

class HTTPBadRequestError(HTTPException):
    """Exception for 400 Bad Request."""
    def __init__(self, message: str | None = None):
        super().__init__(HTTPStatus.BAD_REQUEST, message)

class HTTPNotFoundError(HTTPException):
    """Exception for 404 Not Found."""
    def __init__(self, message: str | None = None):
        super().__init__(HTTPStatus.NOT_FOUND, message)

class HTTPForbiddenError(HTTPException):
    """Exception for 403 Forbidden."""
    def __init__(self, message: str | None = None):
        super().__init__(HTTPStatus.FORBIDDEN, message)

class HTTPMethodNotAllowedError(HTTPException):
    """Exception for 405 Method Not Allowed."""
    def __init__(self, message: str | None = None):
        super().__init__(HTTPStatus.METHOD_NOT_ALLOWED, message)

class HTTPInternalServerError(HTTPException):
    """Exception for 500 Internal Server Error."""
    def __init__(self, message: str | None = None):
        super().__init__(HTTPStatus.INTERNAL_SERVER_ERROR, message) 