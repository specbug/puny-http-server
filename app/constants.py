from enum import IntEnum, StrEnum

# HTTP Methods
class HTTPMethod(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    PATCH = "PATCH"

# HTTP Status Codes
class HTTPStatus(IntEnum):
    # 1xx Informational
    CONTINUE = 100
    SWITCHING_PROTOCOLS = 101
    PROCESSING = 102

    # 2xx Success
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204

    # 3xx Redirection
    MOVED_PERMANENTLY = 301
    FOUND = 302
    SEE_OTHER = 303
    NOT_MODIFIED = 304

    # 4xx Client Error
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    REQUEST_TIMEOUT = 408
    CONFLICT = 409
    LENGTH_REQUIRED = 411
    PAYLOAD_TOO_LARGE = 413
    URI_TOO_LONG = 414
    UNSUPPORTED_MEDIA_TYPE = 415
    TOO_MANY_REQUESTS = 429

    # 5xx Server Error
    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED = 501
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504
    HTTP_VERSION_NOT_SUPPORTED = 505

# Default status text mapping (can be expanded)
STATUS_TEXT = {
    HTTPStatus.OK: "OK",
    HTTPStatus.CREATED: "Created",
    HTTPStatus.NOT_FOUND: "Not Found",
    HTTPStatus.FORBIDDEN: "Forbidden",
    HTTPStatus.INTERNAL_SERVER_ERROR: "Internal Server Error",
    HTTPStatus.BAD_REQUEST: "Bad Request",
    HTTPStatus.METHOD_NOT_ALLOWED: "Method Not Allowed",
}

# Common Header Names (case-insensitive, but canonical form is good practice)
class HTTPHeader(StrEnum):
    CONTENT_TYPE = "Content-Type"
    CONTENT_LENGTH = "Content-Length"
    CONTENT_ENCODING = "Content-Encoding"
    USER_AGENT = "User-Agent"
    ACCEPT_ENCODING = "Accept-Encoding"
    CONNECTION = "Connection"
    HOST = "Host"
    LOCATION = "Location"

# Common Content Types
class ContentType(StrEnum):
    TEXT_PLAIN = "text/plain"
    APP_OCTET_STREAM = "application/octet-stream"
    APP_JSON = "application/json"
    TEXT_HTML = "text/html"

# Other Constants
CRLF = "\r\n"
PROTOCOL_VERSION = "HTTP/1.1"
DEFAULT_PORT = 4221
DEFAULT_ADDRESS = "localhost"
SOCKET_TIMEOUT = 10 # seconds
RECV_BUFFER_SIZE = 2048 