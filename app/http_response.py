from typing import Dict, Optional, Union
from .constants import HTTPStatus, STATUS_TEXT, CRLF, PROTOCOL_VERSION, HTTPHeader

class HTTPResponse:
    """Represents an HTTP response to be sent."""

    def __init__(self,
                 status_code: HTTPStatus,
                 headers: Optional[Dict[str, str]] = None,
                 body: Optional[Union[str, bytes]] = None,
                 status_text: Optional[str] = None):
        """Initializes an HTTPResponse object."""
        self.status_code = status_code
        self.status_text = status_text or STATUS_TEXT.get(status_code, "Unknown")
        self.headers = headers if headers is not None else {}
        self.body = body
        self._encoded_body: Optional[bytes] = None

        # Automatically set Content-Length if body is present and not already set
        if self.body is not None and HTTPHeader.CONTENT_LENGTH.lower() not in {k.lower() for k in self.headers}:
            self._encode_body() # Encode body to determine length
            if self._encoded_body is not None:
                self.headers[HTTPHeader.CONTENT_LENGTH] = str(len(self._encoded_body))

    def _encode_body(self):
        """Encodes the body to bytes if it isn't already."""
        if self.body is None:
            self._encoded_body = b""
        elif isinstance(self.body, bytes):
            self._encoded_body = self.body
        elif isinstance(self.body, str):
            try:
                self._encoded_body = self.body.encode('utf-8')
            except UnicodeEncodeError:
                # Fallback or raise error? For now, encode with error replacement
                self._encoded_body = self.body.encode('utf-8', 'replace')
        else:
            # Handle other potential types if necessary, or raise error
            self._encoded_body = str(self.body).encode('utf-8', 'replace')

    def to_bytes(self, close_connection: bool = False) -> bytes:
        """Builds the full HTTP response as bytes."""
        # Ensure body is encoded
        if self._encoded_body is None:
            self._encode_body()

        response_line = f"{PROTOCOL_VERSION} {self.status_code.value} {self.status_text}{CRLF}"

        # Add Connection header if closing
        if close_connection:
            # Use canonical header name for consistency
            self.headers[HTTPHeader.CONNECTION] = "close"

        response_headers = ""
        for key, value in self.headers.items():
            response_headers += f"{key}: {value}{CRLF}"

        headers_part = response_headers + CRLF # End of headers

        response = response_line.encode('ascii') + headers_part.encode('ascii')

        if self._encoded_body:
            response += self._encoded_body

        return response

    def __repr__(self) -> str:
        return f"HTTPResponse(status={self.status_code}, headers={self.headers}, body_len={len(self._encoded_body) if self._encoded_body else 0})" 