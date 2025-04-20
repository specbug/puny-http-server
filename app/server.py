# Will be populated later 

import socket
import threading
import logging
from typing import Optional

from .constants import DEFAULT_ADDRESS, DEFAULT_PORT, RECV_BUFFER_SIZE, SOCKET_TIMEOUT
from .http_request import HTTPRequest
from .http_response import HTTPResponse
from .router import Router
from .exceptions import HTTPException, HTTPInternalServerError

# Configure basic logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s')

class HTTPServer:
    """A basic HTTP/1.1 server supporting persistent connections."""

    def __init__(self, host: str = DEFAULT_ADDRESS, port: int = DEFAULT_PORT,
                 directory: Optional[str] = None, router: Optional[Router] = None):
        """Initializes the HTTP server.

        Args:
            host: The hostname or IP address to bind to.
            port: The port number to bind to.
            directory: The directory to serve files from (passed to handlers).
            router: A Router instance. If None, a default router is created.
        """
        self.host = host
        self.port = port
        self.directory = directory
        self.router = router if router is not None else Router() # Use provided or default router
        self._server_socket: Optional[socket.socket] = None
        self._is_running = False

        if directory:
            logging.info(f"Serving files from directory: {directory}")
        else:
            logging.warning("No --directory specified. File serving handlers might fail.")

    def _handle_client_connection(self, client_socket: socket.socket, address: tuple):
        """Handles a single client connection, potentially multiple requests."""
        client_socket.settimeout(SOCKET_TIMEOUT)
        peername = f"{address[0]}:{address[1]}"
        logging.info(f"Connection established with {peername}")

        try:
            while True: # Keep-Alive loop
                response: Optional[HTTPResponse] = None
                request: Optional[HTTPRequest] = None
                close_connection = False

                try:
                    # Receive data from the client
                    request_bytes = client_socket.recv(RECV_BUFFER_SIZE)
                    if not request_bytes:
                        logging.info(f"Client {peername} closed connection.")
                        break # Client closed connection gracefully

                    # Parse the request
                    request = HTTPRequest.from_bytes(request_bytes)
                    logging.info(f"Received request from {peername}: {request.method.value} {request.path}")

                    # Determine if connection should close after this request
                    close_connection = request.should_close_connection

                    # Find the appropriate handler using the router
                    handler = self.router.find_handler(request)

                    # Execute the handler to get the response object
                    # Pass the configured directory to the handler
                    response = handler(request, self.directory)

                except socket.timeout:
                    logging.warning(f"Connection to {peername} timed out.")
                    close_connection = True # Force close on timeout
                    break
                except ConnectionResetError:
                    logging.warning(f"Connection to {peername} reset by peer.")
                    close_connection = True
                    break
                except BrokenPipeError:
                    logging.warning(f"Broken pipe error with {peername}.")
                    close_connection = True
                    break
                except HTTPException as e:
                    # Handle known HTTP errors from parsing or handlers
                    logging.warning(f"HTTP error for {peername}: {e}")
                    response = HTTPResponse(status_code=e.status_code, body=e.message)
                    # Keep connection open unless client requested close or it's a server error
                    close_connection = close_connection or e.status_code.value >= 500
                except Exception as e:
                    # Handle unexpected errors
                    logging.exception(f"Unexpected error processing request from {peername}: {e}")
                    err_resp = HTTPInternalServerError()
                    response = HTTPResponse(status_code=err_resp.status_code, body=err_resp.message)
                    close_connection = True # Always close on unexpected server errors

                # Send the response if one was generated
                if response:
                    response_bytes = response.to_bytes(close_connection=close_connection)
                    client_socket.sendall(response_bytes)
                    logging.info(f"Sent response to {peername}: {response.status_code.value} {response.status_text}")
                elif not close_connection:
                    # If no response and connection not closing, something is wrong (e.g., timeout without response)
                    # We should probably close to be safe
                    logging.warning(f"No response generated for {peername}, but connection not marked for closure. Closing.")
                    close_connection = True

                # Close connection if flagged
                if close_connection:
                    logging.info(f"Closing connection to {peername}.")
                    break

        finally:
            if not client_socket._closed:
                try:
                    client_socket.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass # Ignore if already closed
                client_socket.close()
                logging.debug(f"Socket for {peername} closed.")

    def start(self):
        """Starts the server, listens for connections, and handles them in threads."""
        try:
            # SO_REUSEPORT allows multiple instances on the same port (useful for testing/dev)
            # SO_REUSEADDR allows reusing the address quickly after server stops
            self._server_socket = socket.create_server((self.host, self.port), reuse_port=True)
            # self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._is_running = True
            logging.info(f"Server started on {self.host}:{self.port}")

            while self._is_running:
                try:
                    client_socket, address = self._server_socket.accept()
                    # Start a new thread to handle the client connection
                    # Use daemon=True so threads don't block program exit
                    thread = threading.Thread(
                        target=self._handle_client_connection,
                        args=(client_socket, address),
                        daemon=True,
                        name=f"Client-{address[0]}:{address[1]}"
                    )
                    thread.start()
                except OSError as e:
                    # Handle cases where the socket might be closed while accept() is blocking
                    if self._is_running:
                        logging.error(f"Error accepting connection: {e}")
                    else:
                        logging.info("Server socket closed, stopping accept loop.")
                        break # Exit loop if server was stopped

        except OSError as e:
            logging.error(f"Failed to start server on {self.host}:{self.port}: {e}")
        except KeyboardInterrupt:
            logging.info("Server shutting down due to KeyboardInterrupt...")
        finally:
            self.stop()

    def stop(self):
        """Stops the server and closes the server socket."""
        self._is_running = False
        if self._server_socket:
            logging.info("Closing server socket...")
            # Close the socket to unblock the accept() call in the main loop
            # Set socket to non-blocking before closing to avoid potential hangs
            # self._server_socket.setblocking(False)
            try:
                 self._server_socket.close()
            except OSError as e:
                 logging.warning(f"Error closing server socket: {e}")
            self._server_socket = None
            logging.info("Server socket closed.")
        logging.info("Server stopped.") 