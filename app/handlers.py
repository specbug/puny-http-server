# Will be populated later 

import os
import gzip
from typing import Optional

from .http_request import HTTPRequest
from .http_response import HTTPResponse
from .constants import HTTPStatus, HTTPHeader, ContentType
from .exceptions import HTTPNotFoundError, HTTPForbiddenError, HTTPInternalServerError

# Type alias for cleaner handler signatures
# HandlerFunction = Callable[[HTTPRequest, Optional[str]], HTTPResponse]

def handle_root(request: HTTPRequest, directory: Optional[str]) -> HTTPResponse:
    """Handles requests to the root path ('/')."""
    # Currently returns a simple 200 OK with no body
    return HTTPResponse(status_code=HTTPStatus.OK)

def handle_echo(request: HTTPRequest, directory: Optional[str]) -> HTTPResponse:
    """Handles requests to '/echo/...' paths."""
    echo_str = request.path[len("/echo/"):]
    response_body = echo_str.encode('utf-8')
    headers = {HTTPHeader.CONTENT_TYPE: ContentType.TEXT_PLAIN}

    # Check for gzip compression
    accept_encoding = request.get_header(HTTPHeader.ACCEPT_ENCODING, "")
    if "gzip" in [enc.strip() for enc in accept_encoding.split(",")]:
        response_body = gzip.compress(response_body)
        headers[HTTPHeader.CONTENT_ENCODING] = "gzip"

    # Content-Length will be set automatically by HTTPResponse
    return HTTPResponse(status_code=HTTPStatus.OK, headers=headers, body=response_body)

def handle_user_agent(request: HTTPRequest, directory: Optional[str]) -> HTTPResponse:
    """Handles requests to '/user-agent'."""
    user_agent = request.get_header(HTTPHeader.USER_AGENT, "Unknown")
    headers = {HTTPHeader.CONTENT_TYPE: ContentType.TEXT_PLAIN}
    # Content-Length will be set automatically by HTTPResponse
    return HTTPResponse(status_code=HTTPStatus.OK, headers=headers, body=user_agent)

def handle_file_get(request: HTTPRequest, directory: Optional[str]) -> HTTPResponse:
    """Handles GET requests to '/files/...'."""
    if not directory:
        raise HTTPInternalServerError("File directory not configured on server.")

    relative_file_path = request.path[len("/files/"):]
    full_file_path = os.path.abspath(os.path.join(directory, relative_file_path))

    # Security check: Ensure the path is still within the configured directory
    if not full_file_path.startswith(os.path.abspath(directory)):
        raise HTTPForbiddenError("Access denied to file path.")

    if not os.path.exists(full_file_path):
        raise HTTPNotFoundError(f"File not found: {relative_file_path}")

    if not os.path.isfile(full_file_path):
        # Do not serve directories
        raise HTTPNotFoundError(f"Path is not a file: {relative_file_path}")

    try:
        with open(full_file_path, "rb") as f:
            file_data = f.read()
        headers = {HTTPHeader.CONTENT_TYPE: ContentType.APP_OCTET_STREAM}
        # Content-Length will be set automatically by HTTPResponse
        return HTTPResponse(status_code=HTTPStatus.OK, headers=headers, body=file_data)
    except IOError as e:
        # Log the error ideally
        print(f"Error reading file '{full_file_path}': {e}") # Replace with logging
        raise HTTPInternalServerError("Error reading file.")

def handle_file_post(request: HTTPRequest, directory: Optional[str]) -> HTTPResponse:
    """Handles POST requests to '/files/...'."""
    if not directory:
        raise HTTPInternalServerError("File directory not configured on server.")

    relative_file_path = request.path[len("/files/"):]
    full_file_path = os.path.abspath(os.path.join(directory, relative_file_path))

    # Security check
    if not full_file_path.startswith(os.path.abspath(directory)):
        raise HTTPForbiddenError("Access denied to file path.")

    if not request.body:
        # Depending on requirements, maybe return 400 Bad Request if body is needed
        body_bytes = b""
    else:
        body_bytes = request.body.encode('utf-8') # Assuming body is text

    try:
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(full_file_path), exist_ok=True)
        with open(full_file_path, "wb") as f:
            f.write(body_bytes)

        # Standard practice for 201 Created is often no body or just a Location header
        # Here, returning empty body.
        return HTTPResponse(status_code=HTTPStatus.CREATED, body=b"")

    except IOError as e:
        # Log the error ideally
        print(f"Error writing file '{full_file_path}': {e}") # Replace with logging
        raise HTTPInternalServerError("Error writing file.")

def handle_not_found(request: HTTPRequest, directory: Optional[str]) -> HTTPResponse:
    """Default handler for unmatched routes (404 Not Found)."""
    return HTTPResponse(status_code=HTTPStatus.NOT_FOUND, body="Resource not found.") 