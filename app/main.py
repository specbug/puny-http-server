import sys
import argparse
import logging # Use logging configured in server.py

from .server import HTTPServer
from .router import Router
from .constants import HTTPMethod, DEFAULT_PORT, DEFAULT_ADDRESS
from . import handlers # Import handlers module

def main():
    """Parses arguments, sets up routes, and starts the HTTP server."""
    parser = argparse.ArgumentParser(description="Basic HTTP Server")
    parser.add_argument(
        "--directory",
        type=str,
        help="Directory to serve files from",
        default=None
    )
    parser.add_argument(
        "--port",
        type=int,
        help=f"Port to listen on (default: {DEFAULT_PORT})",
        default=DEFAULT_PORT
    )
    parser.add_argument(
        "--host",
        type=str,
        help=f"Host to bind to (default: {DEFAULT_ADDRESS})",
        default=DEFAULT_ADDRESS
    )
    args = parser.parse_args()

    # Create a router and add routes
    router = Router()

    # Add routes using constants and handler functions
    router.add_route(HTTPMethod.GET, r"/$", handlers.handle_root)
    router.add_route(HTTPMethod.GET, r"/echo/.*", handlers.handle_echo) # Regex for /echo/*
    router.add_route(HTTPMethod.GET, r"/user-agent$", handlers.handle_user_agent)
    router.add_route(HTTPMethod.GET, r"/files/.*", handlers.handle_file_get) # Regex for /files/*
    router.add_route(HTTPMethod.POST, r"/files/.*", handlers.handle_file_post) # Regex for /files/*

    # Instantiate and start the server
    server = HTTPServer(
        host=args.host,
        port=args.port,
        directory=args.directory,
        router=router
    )

    logging.info(f"Starting server with config: host={args.host}, port={args.port}, directory={args.directory}")
    server.start() # start() includes the main loop and shutdown handling

if __name__ == "__main__":
    main()
