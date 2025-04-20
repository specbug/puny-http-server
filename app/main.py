import sys
import socket
import threading
import os
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('http_server')

class ResponseBuilder:
    """Helper class to build HTTP responses"""
    
    @staticmethod
    def build(status_code, status_text, headers=None, body=None):
        """Builds an HTTP response as bytes"""
        response_line = f"HTTP/1.1 {status_code} {status_text}\r\n"
        response_headers = ""
        if headers:
            for key, value in headers.items():
                response_headers += f"{key}: {value}\r\n"
        response_headers += "\r\n"  # End of headers
        
        response = response_line.encode() + response_headers.encode()
        if body:
            response += body if isinstance(body, bytes) else body.encode()
            
        return response
    
    @staticmethod
    def send(socket, status_code, status_text, headers=None, body=None):
        """Builds and sends an HTTP response"""
        response = ResponseBuilder.build(status_code, status_text, headers, body)
        socket.sendall(response)

    @staticmethod
    def text(socket, status_code, status_text, text):
        """Creates and sends a text response"""
        body = text if isinstance(text, bytes) else text.encode()
        headers = {
            "Content-Type": "text/plain",
            "Content-Length": str(len(body))
        }
        ResponseBuilder.send(socket, status_code, status_text, headers, body)
    
    @staticmethod
    def ok(socket, body=None, content_type=None):
        """Sends a 200 OK response"""
        if body:
            body_bytes = body if isinstance(body, bytes) else body.encode()
            headers = {
                "Content-Type": content_type or "text/plain",
                "Content-Length": str(len(body_bytes))
            }
            ResponseBuilder.send(socket, 200, "OK", headers, body_bytes)
        else:
            ResponseBuilder.send(socket, 200, "OK")
    
    @staticmethod
    def created(socket, body=None):
        """Sends a 201 Created response"""
        if body:
            body_bytes = body if isinstance(body, bytes) else body.encode()
            headers = {
                "Content-Type": "text/plain",
                "Content-Length": str(len(body_bytes))
            }
            ResponseBuilder.send(socket, 201, "Created", headers, body_bytes)
        else:
            ResponseBuilder.send(socket, 201, "Created")
    
    @staticmethod
    def not_found(socket):
        """Sends a 404 Not Found response"""
        ResponseBuilder.send(socket, 404, "Not Found")
    
    @staticmethod
    def error(socket, message=None):
        """Sends a 500 Internal Server Error response"""
        ResponseBuilder.send(socket, 500, "Internal Server Error")


def parse_request(request_bytes):
    """Parses the raw HTTP request and returns method, path, headers and body."""
    try:
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
    except Exception as e:
        logger.error(f"Error parsing request: {e}")
        return None, None, {}, ""

def handle_root(path, headers, sender_socket, directory, body):
    ResponseBuilder.ok(sender_socket)

def handle_echo(path, headers, sender_socket, directory, body):
    s = path[len("/echo/"):]
    ResponseBuilder.text(sender_socket, 200, "OK", s)

def handle_user_agent(path, headers, sender_socket, directory, body):
    user_agent = headers.get("User-Agent", "Unknown")
    ResponseBuilder.text(sender_socket, 200, "OK", user_agent)

def handle_file(path, headers, sender_socket, directory, body):
    # Extract filename relative to the specified directory
    relative_file_path = path[len("/files/"):]
    # Construct the full path safely
    full_file_path = os.path.join(directory, relative_file_path)

    # Prevent directory traversal attacks (basic check)
    if not os.path.abspath(full_file_path).startswith(os.path.abspath(directory)):
        ResponseBuilder.send(sender_socket, 403, "Forbidden")
        return

    try:
        with open(full_file_path, "rb") as f:
            file_data = f.read()
        
        # Try to guess a better content type based on file extension
        content_type = "application/octet-stream"
        _, ext = os.path.splitext(full_file_path)
        if ext.lower() in ('.html', '.htm'):
            content_type = "text/html"
        elif ext.lower() == '.txt':
            content_type = "text/plain"
        elif ext.lower() in ('.jpg', '.jpeg'):
            content_type = "image/jpeg"
        elif ext.lower() == '.png':
            content_type = "image/png"
        
        headers = {
            "Content-Type": content_type,
            "Content-Length": str(len(file_data))
        }
        ResponseBuilder.send(sender_socket, 200, "OK", headers, file_data)
    except FileNotFoundError:
        ResponseBuilder.not_found(sender_socket)
    except IsADirectoryError:
        ResponseBuilder.not_found(sender_socket)
    except Exception as e:
        logger.error(f"Error reading file '{full_file_path}': {e}")
        ResponseBuilder.error(sender_socket)

def handle_file_create(path, headers, sender_socket, directory, body):
    relative_file_path = path[len("/files/"):]
    full_file_path = os.path.join(directory, relative_file_path)
    
    # Prevent directory traversal attacks
    if not os.path.abspath(full_file_path).startswith(os.path.abspath(directory)):
        ResponseBuilder.send(sender_socket, 403, "Forbidden")
        return
        
    # Ensure the directory exists
    file_dir = os.path.dirname(full_file_path)
    if not os.path.exists(file_dir):
        try:
            os.makedirs(file_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"Error creating directory '{file_dir}': {e}")
            ResponseBuilder.error(sender_socket)
            return
    
    try:
        with open(full_file_path, "wb") as f:
            if body:
                f.write(body.encode() if isinstance(body, str) else body)
        
        # Return success response with the created file path
        ResponseBuilder.created(sender_socket, f"File created: {relative_file_path}")
    except Exception as e:
        logger.error(f"Error creating file '{full_file_path}': {e}")
        ResponseBuilder.error(sender_socket)

def handle_not_found(path, headers, sender_socket, directory, body):
    ResponseBuilder.not_found(sender_socket)

# Route configuration
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
        if not method or not path:
            ResponseBuilder.error(sender_socket)
            return
            
        logger.info(f"Received request: {method} {path}")

        # Find the appropriate handler for the request
        handler = handle_not_found
        for route_method, path_checker, route_handler in ROUTES:
            if method == route_method and path_checker(path):
                handler = route_handler
                break
        
        # Pass the directory to the selected handler
        handler(path, headers, sender_socket, directory, body)

    except Exception as e:
        logger.error(f"Error handling request: {e}")
        try:
            ResponseBuilder.error(sender_socket)
        except Exception as send_e:
            logger.error(f"Error sending 500 response: {send_e}")
    finally:
        try:
            sender_socket.close()
        except:
            pass

def main():
    # Parse command line arguments
    directory = None
    if len(sys.argv) > 2 and sys.argv[1] == '--directory':
        directory = sys.argv[2]
        logger.info(f"Serving files from directory: {directory}")
    else:
        logger.warning("--directory argument not provided. File serving will not work correctly.")

    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    logger.info(f"Server started on port 4221")
    try:
        while True:
            conn = server_socket.accept()
            sender_socket, addr = conn
            # Pass the directory path to the handler thread
            threading.Thread(target=handle_request, args=(sender_socket, directory), daemon=True).start()
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    finally:
        server_socket.close()
        logger.info("Server socket closed.")

if __name__ == "__main__":
    main()
