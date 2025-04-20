import sys
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

def build_response(status_code, status_text, headers=None, body=None):
    """Builds an HTTP response string/bytes."""
    response_line = f"HTTP/1.1 {status_code} {status_text}\r\n"
    response_headers = ""
    if headers:
        for key, value in headers.items():
            response_headers += f"{key}: {value}\r\n"
    response_headers += "\r\n"  # End of headers
    
    response = response_line.encode() + response_headers.encode()
    if body:
        response += body
        
    return response

def send_response(sender_socket, status_code, status_text, headers=None, body=None):
    """Builds and sends an HTTP response."""
    response = build_response(status_code, status_text, headers, body)
    sender_socket.sendall(response)

def handle_root(path, headers, sender_socket, directory, body):
    send_response(sender_socket, 200, "OK")

def handle_echo(path, headers, sender_socket, directory, body):
    s = path[len("/echo/"):]
    content_encodings = headers.get("Accept-Encoding")
    content_encodings = content_encodings.split(",") if content_encodings else []
    s_len = len(s)
    response_body = s.encode()
    response_headers = {
        "Content-Type": "text/plain",
        "Content-Length": str(s_len)
    }
    if "gzip" in content_encodings:
        response_headers["Content-Encoding"] = "gzip"
    send_response(sender_socket, 200, "OK", response_headers, response_body)

def handle_user_agent(path, headers, sender_socket, directory, body):
    user_agent = headers.get("User-Agent", "Unknown")
    response_body = user_agent.encode()
    response_headers = {
        "Content-Type": "text/plain",
        "Content-Length": str(len(response_body))
    }
    send_response(sender_socket, 200, "OK", response_headers, response_body)

def handle_file(path, headers, sender_socket, directory, body):
    # Extract filename relative to the specified directory
    relative_file_path = path[len("/files/"):]
    # Construct the full path safely
    full_file_path = os.path.join(directory, relative_file_path)

    # Prevent directory traversal attacks (basic check)
    if not os.path.abspath(full_file_path).startswith(os.path.abspath(directory)):
        send_response(sender_socket, 403, "Forbidden") # Or 404 depending on desired behavior
        return

    try:
        with open(full_file_path, "rb") as f:
            file_data = f.read()
        response_headers = {
            "Content-Type": "application/octet-stream",
            "Content-Length": str(len(file_data))
        }
        send_response(sender_socket, 200, "OK", response_headers, file_data)
    except FileNotFoundError:
        send_response(sender_socket, 404, "Not Found")
    except IsADirectoryError:
        send_response(sender_socket, 404, "Not Found") # Treat directories as not found
    except Exception as e:
        print(f"Error reading file '{full_file_path}': {e}")
        send_response(sender_socket, 500, "Internal Server Error")

def handle_file_create(path, headers, sender_socket, directory, body):
    relative_file_path = path[len("/files/"):]
    full_file_path = os.path.join(directory, relative_file_path)
    try:
        with open(full_file_path, "wb") as f:
            f.write(body.encode())
        response_headers = {
            "Content-Type": "text/plain",
            "Content-Length": str(len(body))
        }
        send_response(sender_socket, 201, "Created", response_headers, body.encode())
    except Exception as e:
        print(f"Error creating file '{full_file_path}': {e}")
        send_response(sender_socket, 500, "Internal Server Error")

def handle_not_found(path, headers, sender_socket, directory, body):
    send_response(sender_socket, 404, "Not Found")

ROUTES = [
    ("GET", lambda p: p == "/", handle_root),
    ("GET", lambda p: p.startswith("/echo/"), handle_echo),
    ("GET", lambda p: p == "/user-agent", handle_user_agent),
    ("GET", lambda p: p.startswith("/files/"), handle_file),
    ("POST", lambda p: p.startswith("/files/"), handle_file_create),
]

def handle_request(sender_socket, directory):
    """Handles the incoming HTTP request using defined routes and the specified directory."""
    try:
        req_bytes = sender_socket.recv(2048)
        if not req_bytes:
            return 
        method, path, headers, body = parse_request(req_bytes)
        print(f"Received request: {method} {path}")

        handler = handle_not_found
        for route_method, path_checker, route_handler in ROUTES:
            if method == route_method and path_checker(path):
                handler = route_handler
                break
        
        # Pass the directory to the selected handler
        handler(path, headers, sender_socket, directory, body)

    except Exception as e:
        print(f"Error handling request: {e}")
        try:
            send_response(sender_socket, 500, "Internal Server Error")
        except Exception as send_e:
            print(f"Error sending 500 response: {send_e}")
    finally:
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
