# Will be populated later 

import re
from typing import Callable, List, Tuple, Optional, Pattern

from .http_request import HTTPRequest
from .http_response import HTTPResponse
from .constants import HTTPMethod
from .handlers import handle_not_found # Default fallback handler
from .exceptions import HTTPMethodNotAllowedError

# Type alias for the handler function signature
HandlerFunction = Callable[[HTTPRequest, Optional[str]], HTTPResponse]

# Type alias for a route definition
Route = Tuple[HTTPMethod, Pattern[str], HandlerFunction]

class Router:
    """Manages route definitions and dispatches requests to handlers."""

    def __init__(self):
        """Initializes the Router with an empty list of routes."""
        self._routes: List[Route] = []
        self.default_handler: HandlerFunction = handle_not_found

    def add_route(self, method: HTTPMethod, path_pattern: str, handler: HandlerFunction):
        """
        Adds a route to the router.

        Args:
            method: The HTTP method (e.g., HTTPMethod.GET).
            path_pattern: A regex string to match the request path.
            handler: The function to handle requests matching the method and path.
        """
        try:
            compiled_pattern = re.compile(f"^{path_pattern}$") # Match whole path
        except re.error as e:
            raise ValueError(f"Invalid regex pattern '{path_pattern}': {e}") from e
        self._routes.append((method, compiled_pattern, handler))

    def find_handler(self, request: HTTPRequest) -> HandlerFunction:
        """
        Finds the appropriate handler for the given request.

        Args:
            request: The incoming HTTPRequest object.

        Returns:
            The handler function to process the request.

        Raises:
            HTTPMethodNotAllowedError: If a route matches the path but not the method.
            HTTPNotFoundError: Implicitly, if no route matches (returns default handler).
        """
        allowed_methods = set()
        path_matched = False

        for route_method, path_regex, handler in self._routes:
            match = path_regex.match(request.path)
            if match:
                path_matched = True
                allowed_methods.add(route_method.value)
                if request.method == route_method:
                    # Path and method match
                    return handler # Return the first matching handler

        if path_matched:
            # Path matched, but method did not for any route
            # Optionally, you could include an Allow header in the response
            raise HTTPMethodNotAllowedError(
                f"Method {request.method.value} not allowed for {request.path}. Allowed: {', '.join(sorted(allowed_methods))}"
            )

        # No route matched the path
        return self.default_handler 