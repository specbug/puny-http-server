import socket  # noqa: F401

def parse_request(request_bytes):
    """Parses the raw HTTP request and returns method, path, and headers."""
    request_lines = request_bytes.decode().split("\r\n")
    start_line = request_lines[0]
    method, path, _ = start_line.split(" ")
    
    headers = {}
    for line in request_lines[1:]:
        if line == "":  # Empty line marks end of headers
            break
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip()] = value.strip()
            
    return method, path, headers

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

def handle_echo(req_path, sender_socket):
    if req_path.startswith("/echo/"):
        s = req_path[6:]
        s_len = len(s)
        response_body = s.encode()
        response_headers = {
            "Content-Type": "text/plain",
            "Content-Length": str(s_len)
        }
        send_response(sender_socket, 200, "OK", response_headers, response_body)
    else:
        send_response(sender_socket, 404, "Not Found")

def handle_user_agent(headers, sender_socket):
    user_agent = headers.get("User-Agent", "Unknown")
    response_body = user_agent.encode()
    response_headers = {
        "Content-Type": "text/plain",
        "Content-Length": str(len(response_body))
    }
    send_response(sender_socket, 200, "OK", response_headers, response_body)

def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!")

    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    conn = server_socket.accept()  # wait for client
    sender_socket, addr = conn

    # Get the request from the client
    req_bytes = sender_socket.recv(2048)
    method, path, headers = parse_request(req_bytes)
    print(f"Received request: {method} {path} {headers}")

    if path == "/":
        send_response(sender_socket, 200, "OK")
    elif path.startswith("/echo/"):
        handle_echo(path, sender_socket)
    elif path.startswith("/user-agent"):
        handle_user_agent(headers, sender_socket)
    else:
        send_response(sender_socket, 404, "Not Found")

    # Close the connection
    sender_socket.close()
    server_socket.close()

if __name__ == "__main__":
    main()
