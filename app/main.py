import sys
import gzip
import socket
import threading
import os # Import os for path joining

def parse_request(request_bytes):
    """Parses the raw HTTP request and returns method, path, headers and body."""
    request_text = request_bytes.decode()
    
    # Split headers and body
    if "\r\n\r\n" in request_text:
        headers_text, body = request_text.split("\r\n\r\n", 1)
    else:
        headers_text = request_text
        body = ""
        
    request_lines = headers_text.split("\r\n")
    start_line = request_lines[0]
    method, path, _ = start_line.split(" ")
    
    headers = {}
    for line in request_lines[1:]:
        if line == "":  # Empty line marks end of headers
            break
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip()] = value.strip()
            
    return method, path, headers, body

def build_response(status_code, status_text, headers=None, body=None, close_connection=False):
    """Builds an HTTP response string/bytes."""
    response_line = f"HTTP/1.1 {status_code} {status_text}\r\n"
    response_headers = ""
    if headers:
        for key, value in headers.items():
            response_headers += f"{key}: {value}\r\n"

    # Add Connection header if closing
    if close_connection:
        response_headers += "Connection: close\r\n"

    response_headers += "\r\n"  # End of headers

    response = response_line.encode() + response_headers.encode()
    if body:
        # Ensure body is bytes before concatenation
        response += body if isinstance(body, bytes) else str(body).encode()

    return response

def handle_root(path, headers, sender_socket, directory, body):
    # send_response(sender_socket, 200, "OK")
    return 200, "OK", None, None

def handle_echo(path, headers, sender_socket, directory, body):
    s = path[len("/echo/"):]
    content_encodings = headers.get("Accept-Encoding")
    content_encodings = content_encodings.split(", ") if content_encodings else []
    response_body = s.encode()
    content_type = "text/plain"
    response_headers = {}

    if "gzip" in content_encodings:
        response_body = gzip.compress(response_body) # Compress the original string bytes
        response_headers["Content-Encoding"] = "gzip"

    response_headers["Content-Type"] = content_type
    response_headers["Content-Length"] = str(len(response_body)) # Length of potentially compressed body
    return 200, "OK", response_headers, response_body

def handle_user_agent(path, headers, sender_socket, directory, body):
    user_agent = headers.get("User-Agent", "Unknown")
    response_body = user_agent.encode()
    response_headers = {
        "Content-Type": "text/plain",
        "Content-Length": str(len(response_body))
    }
    return 200, "OK", response_headers, response_body

def handle_file(path, headers, sender_socket, directory, body):
    # Extract filename relative to the specified directory
    relative_file_path = path[len("/files/"):]
    # Construct the full path safely
    full_file_path = os.path.join(directory, relative_file_path)

    # Prevent directory traversal attacks and check if directory is provided
    if not directory or not os.path.abspath(full_file_path).startswith(os.path.abspath(directory)):
        return 403, "Forbidden", None, None # Or 404

    try:
        with open(full_file_path, "rb") as f:
            file_data = f.read()
        response_headers = {
            "Content-Type": "application/octet-stream",
            "Content-Length": str(len(file_data))
        }
        return 200, "OK", response_headers, file_data
    except FileNotFoundError:
        return 404, "Not Found", None, None
    except IsADirectoryError:
        return 404, "Not Found", None, None # Treat directories as not found
    except Exception as e:
        print(f"Error reading file '{full_file_path}': {e}")
        return 500, "Internal Server Error", None, None

def handle_file_create(path, headers, sender_socket, directory, body):
    relative_file_path = path[len("/files/"):]
    full_file_path = os.path.join(directory, relative_file_path)

    # Prevent directory traversal attacks and check if directory is provided
    if not directory or not os.path.abspath(full_file_path).startswith(os.path.abspath(directory)):
        # Assuming 403 is appropriate if path is invalid or outside allowed directory
        return 403, "Forbidden", None, None

    try:
        # Ensure the parent directory exists before writing the file
        os.makedirs(os.path.dirname(full_file_path), exist_ok=True)
        with open(full_file_path, "wb") as f:
            # Body from parse_request is string, needs encoding for write
            f.write(body.encode('utf-8'))
        response_headers = {
            # 201 Created response should have minimal body or location header
            # Sending empty body is common practice
            "Content-Length": "0"
        }
        return 201, "Created", response_headers, b"" # Return empty bytes body
    except Exception as e:
        print(f"Error creating file '{full_file_path}': {e}")
        return 500, "Internal Server Error", None, None

def handle_not_found(path, headers, sender_socket, directory, body):
    return 404, "Not Found", None, None

ROUTES = [
    ("GET", lambda p: p == "/", handle_root),
    ("GET", lambda p: p.startswith("/echo/"), handle_echo),
    ("GET", lambda p: p == "/user-agent", handle_user_agent),
    ("GET", lambda p: p.startswith("/files/"), handle_file),
    ("POST", lambda p: p.startswith("/files/"), handle_file_create),
]

def handle_request(sender_socket, directory):
    """Handles incoming HTTP requests on a persistent connection."""
    # Assign peername before potential closure in finally block
    peername = None
    try:
        peername = sender_socket.getpeername()
        print(f"Connection established with {peername}")
        sender_socket.settimeout(10) # Set a 10-second timeout for inactivity
    except socket.error as e:
        print(f"Error setting up connection with socket: {e}")
        sender_socket.close()
        return # Cannot proceed without a valid socket

    try:
        while True: # Keep handling requests on the same connection
            try:
                req_bytes = sender_socket.recv(2048)
                if not req_bytes:
                    print(f"Client {peername} closed connection.")
                    break # Client closed connection

                method, path, headers, body = parse_request(req_bytes)
                print(f"Received request from {peername}: {method} {path}")

                # Determine if connection should be closed after this request (HTTP/1.1 default is keep-alive)
                close_connection = headers.get("Connection", "").lower() == "close"

                handler = handle_not_found # Default handler
                matched_handler_args = (path, headers, sender_socket, directory, body)

                for route_method, path_checker, route_handler in ROUTES:
                    if method == route_method and path_checker(path):
                        handler = route_handler
                        break

                # Call the selected handler function to get response components
                status_code, status_text, response_headers, response_body = handler(*matched_handler_args)

                # Build the response, adding "Connection: close" if needed
                response_bytes = build_response(status_code, status_text, response_headers, response_body, close_connection)

                # Send the response
                sender_socket.sendall(response_bytes)
                print(f"Sent response to {peername}: {status_code} {status_text}")

                # Close connection if client requested it
                if close_connection:
                    print(f"Closing connection to {peername} as requested by client.")
                    break

            except socket.timeout:
                print(f"Connection to {peername} timed out due to inactivity.")
                break # Exit loop on timeout
            except ConnectionResetError:
                print(f"Connection to {peername} reset by peer.")
                break # Exit loop if client resets
            except BrokenPipeError:
                print(f"Broken pipe error with {peername} (client likely closed connection abruptly).")
                break
            except Exception as e:
                print(f"Error processing request from {peername}: {e}")
                # Attempt to send a 500 error response if possible
                try:
                    # Always close connection on server error
                    if not sender_socket._closed:
                        response_bytes = build_response(500, "Internal Server Error", close_connection=True)
                        sender_socket.sendall(response_bytes)
                        print(f"Sent 500 error response to {peername}.")
                except Exception as send_e:
                    print(f"Error sending 500 response to {peername}: {send_e}")
                break # Exit loop on internal server error

    finally:
        if not sender_socket._closed:
            print(f"Closing socket for {peername if peername else 'unknown client'}.")
            sender_socket.close()

def main():
    # Parse command line arguments
    directory = None
    if len(sys.argv) > 2 and sys.argv[1] == '--directory':
        directory = sys.argv[2]
        print(f"Serving files from directory: {directory}")
    else:
        print("Warning: --directory argument not provided. File serving will not work correctly.")
        # Optionally exit or set a default directory if file serving is mandatory
        # sys.exit(1)

    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    print(f"Server started on port 4221")
    try:
        while True:
            conn = server_socket.accept()
            sender_socket, addr = conn
            # Pass the directory path to the handler thread
            threading.Thread(target=handle_request, args=(sender_socket, directory), daemon=True).start()
    except KeyboardInterrupt:
        print("\nServer shutting down...")
    finally:
        server_socket.close()
        print("Server socket closed.")

if __name__ == "__main__":
    main()
