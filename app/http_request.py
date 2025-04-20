from typing import Dict, Optional
from .constants import HTTPMethod, CRLF, HTTPHeader
from .exceptions import HTTPBadRequestError

class HTTPRequest:
    """Represents a parsed HTTP request."""

    def __init__(self,
                 method: HTTPMethod,
                 path: str,
                 headers: Dict[str, str],
                 body: str | None = None,
                 protocol: str = "HTTP/1.1"):
        """Initializes an HTTPRequest object."""
        self.method = method
        self.path = path
        self.protocol = protocol
        self.headers = headers # Headers are stored case-insensitively (normalized to lower)
        self.body = body

    @classmethod
    def from_bytes(cls, request_bytes: bytes) -> "HTTPRequest":
        """Parses raw request bytes into an HTTPRequest object."""
        try:
            request_text = request_bytes.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPBadRequestError("Invalid encoding in request")

        # Split headers and body
        header_part, body = request_text.split(CRLF + CRLF, 1) if CRLF + CRLF in request_text else (request_text, "")

        request_lines = header_part.split(CRLF)
        if not request_lines:
            raise HTTPBadRequestError("Empty request")

        # Parse start line (Method Path Protocol)
        start_line = request_lines[0]
        try:
            method_str, path, protocol = start_line.split(" ", 2)
        except ValueError:
            raise HTTPBadRequestError(f"Malformed start line: {start_line!r}")

        try:
            method = HTTPMethod(method_str.upper())
        except ValueError:
            # If method is not in our enum, treat as bad request or potentially extend enum
            raise HTTPBadRequestError(f"Unsupported HTTP method: {method_str}")

        # Parse headers
        headers: Dict[str, str] = {}
        for line in request_lines[1:]:
            if line == "": # Should not happen before CRLFCRLF, but handle defensively
                break
            if ":" in line:
                key, value = line.split(":", 1)
                # Normalize header keys to lowercase for consistent access
                headers[key.strip().lower()] = value.strip()
            else:
                raise HTTPBadRequestError(f"Malformed header line: {line!r}")

        return cls(method=method, path=path, headers=headers, body=body, protocol=protocol)

    def get_header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Gets a header value by name (case-insensitive)."""
        return self.headers.get(name.lower(), default)

    @property
    def should_close_connection(self) -> bool:
        """Checks if the 'Connection: close' header is present."""
        return self.get_header(HTTPHeader.CONNECTION, "").lower() == "close"

    def __repr__(self) -> str:
        return f"HTTPRequest(method={self.method}, path='{self.path}', headers={self.headers}, body_len={len(self.body) if self.body else 0})" 